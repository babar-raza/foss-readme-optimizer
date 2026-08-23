"""Reconcile factual-review evidence and candidate spans without another provider call."""

from __future__ import annotations

import re

from readme_agent.readme.fact_grounding import fact_strings
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)

FACTUAL_RECONCILIATION_CONTRACT_VERSION = "factual-reconciliation-v2-no-auto-accept"


def _unique_whitespace_insensitive_span(quote: str, candidate_text: str) -> str | None:
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


def reconcile_candidate_spans(
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
        exact_span = (
            matches[0].group(0)
            if len(matches) == 1
            else _unique_whitespace_insensitive_span(quote, candidate_text)
        )
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


def reconcile_supported_factual_evidence(
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
            finding.disposition not in {"supports_acceptance", "requires_repair"}
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


__all__ = [
    "FACTUAL_RECONCILIATION_CONTRACT_VERSION",
    "reconcile_candidate_spans",
    "reconcile_supported_factual_evidence",
]
