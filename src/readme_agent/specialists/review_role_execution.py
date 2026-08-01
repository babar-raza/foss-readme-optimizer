"""Execute one reviewer role with bounded finding-grounding correction."""

from __future__ import annotations

import re
from typing import Protocol

from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import build_role_grounding_retry_message
from readme_agent.readme.fact_grounding import fact_strings
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_candidate_anchors import (
    CandidateReviewAnchorV1,
    bind_candidate_review_anchors,
    build_candidate_review_anchors,
    unknown_candidate_review_anchor_ids,
)
from readme_agent.specialists.review_finding_grounding import (
    FindingGroundingResultV1,
    deterministically_disproven_finding_ids,
    grounding_retry_context,
    validate_review_findings,
)

_MAX_GROUNDING_ATTEMPTS = 2
_MAX_BLIND_GROUNDING_ATTEMPTS = 3


class AnalysisClientLike(Protocol):
    """Minimal analysis-client seam used by independent reviewer roles."""

    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


class GroundedRoleFailure(LLMError):
    """Reviewer failure that preserves every bounded grounding attempt."""

    def __init__(self, message: str, *, retry_history: tuple[dict, ...]) -> None:
        super().__init__(message)
        self.retry_history = retry_history


def _normalized_finding_id(value: object) -> str:
    raw = str(value).strip().casefold()
    normalized = re.sub(r"[^a-z0-9_.-]+", "-", raw).strip("._-")
    if normalized and not normalized[0].isalpha():
        normalized = f"finding-{normalized}"
    return normalized or "finding"


def normalize_redundant_role_fields(role: str, value: object) -> object:
    """Derive redundant summaries from verdict and findings without changing either."""

    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    findings = normalized.get("findings")
    if isinstance(findings, list):
        normalized_items: list[object] = []
        finding_id_occurrences: dict[str, int] = {}
        for item in findings:
            if not isinstance(item, dict):
                normalized_items.append(item)
                continue
            normalized_item = dict(item)
            if isinstance(normalized_item.get("finding_id"), str):
                base_finding_id = _normalized_finding_id(normalized_item["finding_id"])
                occurrence = finding_id_occurrences.get(base_finding_id, 0) + 1
                finding_id_occurrences[base_finding_id] = occurrence
                normalized_item["finding_id"] = (
                    base_finding_id if occurrence == 1 else f"{base_finding_id}.{occurrence}"
                )
            if normalized_item.get("disposition") != "requires_repair":
                normalized_item["required_repair"] = ""
            normalized_items.append(normalized_item)
        normalized["findings"] = normalized_items
    verdict = normalized.get("verdict")
    if verdict in {"ACCEPT", "SYSTEM_FAILURE"}:
        normalized["failed_criteria"] = []
        normalized["sections_affected"] = []
        normalized["required_repair"] = ""
        return normalized
    summarizable_verdicts = {
        "blind_quality": {"REJECT_REPAIRABLE"},
        "factual_plan": {
            "REJECT_REPAIRABLE",
            "BLOCKED_FACT_CONFLICT",
            "BLOCKED_MISSING_EVIDENCE",
        },
    }
    if verdict not in summarizable_verdicts.get(role, set()):
        return normalized
    findings = normalized.get("findings")
    if not isinstance(findings, list) or not findings:
        return normalized
    valid_findings = [item for item in findings if isinstance(item, dict)]
    if len(valid_findings) != len(findings):
        return normalized
    normalized_findings = []
    for item in valid_findings:
        normalized_item = dict(item)
        if (
            normalized_item.get("disposition") == "requires_repair"
            and not str(normalized_item.get("required_repair", "")).strip()
        ):
            section = str(normalized_item.get("section", "README section")).strip()
            claim = str(normalized_item.get("claim", "visible presentation defect")).strip()
            normalized_item["required_repair"] = (
                f"Repair the quoted {section} presentation defect: {claim}"
            )
        normalized_findings.append(normalized_item)
    normalized["findings"] = normalized_findings
    normalized["failed_criteria"] = list(
        dict.fromkeys(
            str(item["criterion"])
            for item in normalized_findings
            if str(item.get("criterion", "")).strip()
        )
    )
    normalized["sections_affected"] = list(
        dict.fromkeys(
            str(item["section"])
            for item in normalized_findings
            if str(item.get("section", "")).strip()
        )
    )
    normalized["required_repair"] = (
        " ".join(
            dict.fromkeys(
                str(item["required_repair"]).strip()
                for item in normalized_findings
                if item.get("disposition") == "requires_repair"
                and str(item.get("required_repair", "")).strip()
            )
        )
        if verdict == "REJECT_REPAIRABLE"
        else ""
    )
    return normalized


def _parse_role_result(
    role: str,
    result: AnalysisResult,
    *,
    candidate_anchors: tuple[CandidateReviewAnchorV1, ...] = (),
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    try:
        unknown = unknown_candidate_review_anchor_ids(result.parsed, candidate_anchors)
        if unknown:
            label = "blind README quality" if role == "blind_quality" else "factual README plan"
            raise LLMError(f"{label} review selected unknown anchors: {unknown}")
        anchored = bind_candidate_review_anchors(result.parsed, candidate_anchors)
        if role == "blind_quality":
            return BlindQualityReviewResultV1.model_validate(
                normalize_redundant_role_fields(
                    role,
                    anchored,
                )
            )
        return FactualPlanReviewResultV1.model_validate(
            normalize_redundant_role_fields(role, anchored)
        )
    except ValidationError as exc:
        label = "blind README quality" if role == "blind_quality" else "factual README plan"
        raise LLMError(f"{label} review violated its output contract: {exc}") from exc


def _drop_ungrounded_blind_sibling_findings(
    parsed: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    errors: list[str],
) -> tuple[BlindQualityReviewResultV1 | FactualPlanReviewResultV1, tuple[str, ...]]:
    """Retain grounded blind findings when only sibling quality findings are invalid."""

    if not isinstance(parsed, BlindQualityReviewResultV1) or parsed.verdict == "SYSTEM_FAILURE":
        return parsed, ()
    invalid_ids = {error.split(":", maxsplit=1)[0] for error in errors if ":" in error}
    invalid_ids.update(deterministically_disproven_finding_ids(errors))
    finding_ids = {finding.finding_id for finding in parsed.findings}
    removable_ids = invalid_ids & finding_ids
    if not removable_ids:
        return parsed, ()
    retained = [finding for finding in parsed.findings if finding.finding_id not in removable_ids]
    if not retained:
        return parsed, ()
    disposition = "repair" if parsed.verdict == "REJECT_REPAIRABLE" else "acceptance"
    normalized = normalize_redundant_role_fields(
        "blind_quality",
        {
            **parsed.model_dump(mode="json"),
            "reasoning": (
                "Deterministic grounding removed ungrounded quality findings and retained "
                f"{len(retained)} independently proposed {disposition} finding(s)."
            ),
            "findings": [finding.model_dump(mode="json") for finding in retained],
        },
    )
    return BlindQualityReviewResultV1.model_validate(normalized), tuple(sorted(removable_ids))


def _reconcile_candidate_spans(
    parsed: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    candidate_text: str,
) -> tuple[BlindQualityReviewResultV1 | FactualPlanReviewResultV1, tuple[str, ...]]:
    """Bind a whitespace-lossy reviewer quote to one unique exact candidate span."""

    updates = []
    reconciled_ids: list[str] = []
    for finding in parsed.findings:
        quote = finding.quoted_candidate_span
        if quote in candidate_text:
            updates.append(finding)
            continue
        tokens = re.findall(r"\S+", quote)
        if not tokens:
            updates.append(finding)
            continue
        pattern = r"\s+".join(re.escape(token) for token in tokens)
        matches = list(re.finditer(pattern, candidate_text))
        exact_span: str | None
        if len(matches) == 1:
            exact_span = matches[0].group(0)
        else:
            exact_span = _unique_whitespace_insensitive_span(quote, candidate_text)
        if exact_span is None:
            updates.append(finding)
            continue
        updates.append(finding.model_copy(update={"quoted_candidate_span": exact_span}))
        reconciled_ids.append(finding.finding_id)
    if not reconciled_ids:
        return parsed, ()
    payload = {**parsed.model_dump(mode="json"), "findings": updates}
    if isinstance(parsed, BlindQualityReviewResultV1):
        return BlindQualityReviewResultV1.model_validate(payload), tuple(reconciled_ids)
    return FactualPlanReviewResultV1.model_validate(payload), tuple(reconciled_ids)


def _reconcile_supported_factual_evidence(
    parsed: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    product_facts: dict | None,
) -> tuple[BlindQualityReviewResultV1 | FactualPlanReviewResultV1, tuple[str, ...]]:
    """Bind redundant evidence fields for accepted, conflict-free fact citations."""

    if not isinstance(parsed, FactualPlanReviewResultV1) or product_facts is None:
        return parsed, ()
    selected = set(product_facts.get("selected_fact_ids", {}).values())
    by_fact_id = {
        str(fact.get("fact_id")): fact
        for fact in product_facts.get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    updates = []
    reconciled_ids: list[str] = []
    for finding in parsed.findings:
        fact = by_fact_id.get(str(finding.fact_id))
        if (
            finding.disposition != "supports_acceptance"
            or fact is None
            or finding.fact_id not in selected
            or fact.get("verification_state") not in {"verified", "policy_approved"}
            or any(
                conflict.get("status") == "unresolved"
                for conflict in fact.get("conflicts", [])
                if isinstance(conflict, dict)
            )
        ):
            updates.append(finding)
            continue
        assessments = fact.get("evidence_assessments") or []
        accepted_assessments = [
            assessment
            for assessment in assessments
            if isinstance(assessment, dict) and assessment.get("accepted")
        ]
        if accepted_assessments:
            assessment = accepted_assessments[0]
            evidence_excerpt = next(
                (
                    str(assessment.get(field, "")).strip()
                    for field in ("exact_excerpt", "anchor", "context_excerpt")
                    if str(assessment.get(field, "")).strip()
                ),
                "",
            )
            expected = assessment.get("expected_polarity")
            observed = assessment.get("observed_polarity")
        else:
            evidence_excerpt = next(iter(fact_strings(fact.get("value"))), "")
            expected = "positive_implementation"
            observed = "positive_implementation"
        if not evidence_excerpt:
            updates.append(finding)
            continue
        evidence_location = str((fact.get("source") or {}).get("location", ""))
        if (
            finding.evidence_excerpt == evidence_excerpt
            and finding.evidence_location == evidence_location
            and finding.expected_polarity == expected
            and finding.observed_polarity == observed
            and finding.polarity_result == "supports"
        ):
            updates.append(finding)
            continue
        updates.append(
            finding.model_copy(
                update={
                    "evidence_excerpt": evidence_excerpt,
                    "evidence_location": evidence_location,
                    "expected_polarity": expected,
                    "observed_polarity": observed,
                    "polarity_result": "supports",
                }
            )
        )
        reconciled_ids.append(finding.finding_id)
    if not reconciled_ids:
        return parsed, ()
    return (
        FactualPlanReviewResultV1.model_validate(
            {**parsed.model_dump(mode="json"), "findings": updates}
        ),
        tuple(reconciled_ids),
    )


def _unique_whitespace_insensitive_span(quote: str, candidate_text: str) -> str | None:
    """Recover exact bytes only when whitespace removal yields one content-identical span."""

    normalized_quote = "".join(character for character in quote if not character.isspace())
    if not normalized_quote:
        return None
    normalized_candidate: list[str] = []
    source_offsets: list[int] = []
    for offset, character in enumerate(candidate_text):
        if character.isspace():
            continue
        normalized_candidate.append(character)
        source_offsets.append(offset)
    haystack = "".join(normalized_candidate)
    starts: list[int] = []
    cursor = 0
    while True:
        match = haystack.find(normalized_quote, cursor)
        if match < 0:
            break
        starts.append(match)
        cursor = match + 1
        if len(starts) > 1:
            return None
    if len(starts) != 1:
        return None
    normalized_start = starts[0]
    normalized_end = normalized_start + len(normalized_quote) - 1
    source_start = source_offsets[normalized_start]
    source_end = source_offsets[normalized_end] + 1
    return candidate_text[source_start:source_end]


def run_grounded_role(
    *,
    role: str,
    prompt_id: str,
    client: AnalysisClientLike,
    messages: list[dict],
    candidate_text: str,
    product_facts: dict | None,
    visitor_contract: dict | None = None,
) -> tuple[
    BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
    list[dict],
    FindingGroundingResultV1,
]:
    """Run a reviewer and allow one bounded correction of invalid finding evidence."""

    history: list[dict] = []
    current_messages = list(messages)
    candidate_anchors = build_candidate_review_anchors(candidate_text)
    max_attempts = (
        _MAX_BLIND_GROUNDING_ATTEMPTS if role == "blind_quality" else _MAX_GROUNDING_ATTEMPTS
    )
    for attempt in range(1, max_attempts + 1):
        analysis = client.analyze(current_messages)
        grounding: FindingGroundingResultV1 | None = None
        dismissed_finding_ids: tuple[str, ...] = ()
        reconciled_candidate_span_ids: tuple[str, ...] = ()
        reconciled_factual_polarity_ids: tuple[str, ...] = ()
        original_errors: list[str] = []
        try:
            parsed = _parse_role_result(
                role,
                analysis,
                candidate_anchors=candidate_anchors,
            )
            parsed, reconciled_candidate_span_ids = _reconcile_candidate_spans(
                parsed,
                candidate_text,
            )
            parsed, reconciled_factual_polarity_ids = _reconcile_supported_factual_evidence(
                parsed,
                product_facts,
            )
            grounding = validate_review_findings(
                candidate_text=candidate_text,
                product_facts=product_facts,
                findings=parsed.findings,
                visitor_contract=visitor_contract,
            )
            errors = grounding.errors
            original_errors = list(errors)
            if errors:
                parsed, dismissed_finding_ids = _drop_ungrounded_blind_sibling_findings(
                    parsed,
                    errors,
                )
                if dismissed_finding_ids:
                    grounding = validate_review_findings(
                        candidate_text=candidate_text,
                        product_facts=product_facts,
                        findings=parsed.findings,
                        visitor_contract=visitor_contract,
                    )
                    errors = grounding.errors
        except LLMError as exc:
            parsed = None
            errors = [str(exc)]
        invalid_finding_ids = {error.split(":", maxsplit=1)[0] for error in errors if ":" in error}
        history.append(
            {
                "role": role,
                "attempt": attempt,
                "valid": not errors,
                "errors": errors,
                "validation_result": grounding.model_dump(mode="json") if grounding else None,
                "deterministically_dismissed_finding_ids": list(dismissed_finding_ids),
                "reconciled_candidate_span_ids": list(reconciled_candidate_span_ids),
                "reconciled_factual_polarity_ids": list(reconciled_factual_polarity_ids),
                "pre_normalization_errors": original_errors,
                "invalid_findings": [
                    {
                        "finding_id": finding.finding_id,
                        "criterion": finding.criterion,
                        "section": finding.section,
                        "claim": finding.claim,
                        "quoted_candidate_span": finding.quoted_candidate_span,
                        "required_repair": finding.required_repair,
                    }
                    for finding in parsed.findings
                    if finding.finding_id in invalid_finding_ids
                ]
                if parsed is not None
                else [],
            }
        )
        if parsed is not None and grounding is not None and not errors:
            return parsed, history, grounding
        if attempt == max_attempts:
            raise GroundedRoleFailure(
                f"{role} reviewer repeatedly returned ungrounded findings: {errors}",
                retry_history=tuple(history),
            )
        current_messages = [
            *messages,
            build_role_grounding_retry_message(
                prompt_id,
                grounding_retry_context(
                    errors=errors,
                    candidate_text=candidate_text,
                    product_facts=product_facts,
                    findings=tuple(parsed.findings) if parsed is not None else (),
                    visitor_contract=visitor_contract,
                ),
            ),
        ]
    raise AssertionError("grounding retry loop must return or raise")
