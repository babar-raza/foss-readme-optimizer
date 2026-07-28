"""Validate reviewer findings against exact candidate spans and accepted fact evidence."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.readme.fact_grounding import fact_strings

FindingKind = Literal["quality", "factual"]
FindingPolarityResult = Literal["not_applicable", "supports", "contradicts", "missing"]
FindingDisposition = Literal["supports_acceptance", "requires_repair", "blocks"]
EvidencePolarity = Literal[
    "positive_implementation",
    "explicit_constraint",
    "ambiguous_occurrence",
]
BLIND_QUALITY_CRITERIA = (
    "clarity",
    "product_specificity",
    "hierarchy",
    "navigation",
    "installation_presentation",
    "example_presentation",
    "preservation",
    "visible_duplication",
    "internal_terminology",
    "promotional_balance",
    "markdown_integrity",
    "template_genericity",
)


class GroundedReviewFindingV1(BaseModel):
    """One review premise with inspectable candidate and fact anchors."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    kind: FindingKind
    criterion: str = Field(min_length=1)
    section: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    quoted_candidate_span: str = Field(min_length=1)
    disposition: FindingDisposition
    fact_id: str | None = None
    evidence_excerpt: str | None = None
    evidence_location: str | None = None
    expected_polarity: EvidencePolarity | None = None
    observed_polarity: EvidencePolarity | None = None
    polarity_result: FindingPolarityResult
    required_repair: str = ""

    @model_validator(mode="after")
    def _shape_matches_kind(self) -> GroundedReviewFindingV1:
        if self.kind == "quality":
            if any(
                value is not None
                for value in (
                    self.fact_id,
                    self.evidence_excerpt,
                    self.evidence_location,
                    self.expected_polarity,
                    self.observed_polarity,
                )
            ):
                raise ValueError("quality finding cannot carry factual evidence fields")
            if self.polarity_result != "not_applicable":
                raise ValueError("quality finding polarity must be not_applicable")
            if self.disposition == "blocks":
                raise ValueError("quality finding cannot block on factual evidence")
        elif self.polarity_result == "missing":
            if (
                self.fact_id is not None
                or self.evidence_excerpt is not None
                or self.evidence_location is not None
            ):
                raise ValueError("missing-evidence finding cannot cite a fact or evidence excerpt")
            if self.disposition != "blocks":
                raise ValueError("missing-evidence finding must block")
        elif self.fact_id is None or not self.evidence_excerpt or not self.evidence_location:
            raise ValueError(
                "supported/contradicted factual finding requires fact, evidence, and location"
            )
        elif self.polarity_result == "supports" and self.disposition == "blocks":
            raise ValueError("supported factual finding cannot block")
        elif self.polarity_result == "contradicts" and self.disposition != "blocks":
            raise ValueError("contradicted factual finding must block")
        if self.disposition == "requires_repair" and not self.required_repair.strip():
            raise ValueError("repair finding requires a bounded repair instruction")
        if self.disposition != "requires_repair" and self.required_repair.strip():
            raise ValueError("only repair findings may carry repair instructions")
        return self


class FindingGroundingResultV1(BaseModel):
    """Deterministic validation result for one role response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    errors: list[str]
    checked_finding_ids: list[str]


def _fact_evidence_strings(fact: dict) -> set[str]:
    values = {
        str(fact.get("value", "")),
        str((fact.get("source") or {}).get("location", "")),
    }
    for assessment in fact.get("evidence_assessments") or []:
        values.update(
            {
                str(assessment.get("anchor", "")),
                str(assessment.get("exact_excerpt", "")),
                str(assessment.get("context_excerpt", "")),
            }
        )
    return {value for value in values if value}


def _accepted_literal_fact_ids(finding: GroundedReviewFindingV1, product_facts: dict) -> list[str]:
    text = f"{finding.claim}\n{finding.quoted_candidate_span}".casefold()
    by_fact_id = {
        str(fact.get("fact_id")): fact
        for fact in product_facts.get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    matches: list[str] = []
    for fact_id in set(product_facts.get("selected_fact_ids", {}).values()):
        fact = by_fact_id.get(fact_id)
        if fact is None:
            continue
        if fact.get("verification_state") not in {"verified", "policy_approved"}:
            continue
        if any(conflict.get("status") == "unresolved" for conflict in fact.get("conflicts", [])):
            continue
        if any(
            len(phrase.strip()) >= 4 and phrase.strip().casefold() in text
            for phrase in fact_strings(fact.get("value"))
        ):
            matches.append(fact_id)
    return sorted(matches)


def validate_review_findings(
    *,
    candidate_text: str,
    product_facts: dict | None,
    findings: list[GroundedReviewFindingV1],
) -> FindingGroundingResultV1:
    """Reject invented spans, unknown facts, evidence mismatch, and wrong polarity."""

    errors: list[str] = []
    by_fact_id = {
        str(fact.get("fact_id")): fact
        for fact in (product_facts or {}).get("facts", [])
        if isinstance(fact, dict) and fact.get("fact_id")
    }
    selected = set((product_facts or {}).get("selected_fact_ids", {}).values())
    seen: set[str] = set()
    for finding in findings:
        if finding.finding_id in seen:
            errors.append(f"{finding.finding_id}:duplicate finding ID")
        seen.add(finding.finding_id)
        if finding.quoted_candidate_span not in candidate_text:
            errors.append(f"{finding.finding_id}:quoted candidate span is absent")
        if finding.kind != "factual":
            if finding.kind == "quality" and finding.criterion not in BLIND_QUALITY_CRITERIA:
                errors.append(
                    f"{finding.finding_id}:criterion is outside blind visible-quality authority"
                )
            continue
        if finding.polarity_result == "missing":
            contradicted_by = _accepted_literal_fact_ids(finding, product_facts or {})
            if contradicted_by:
                errors.append(
                    f"{finding.finding_id}:missing-evidence premise contradicts accepted facts "
                    f"{contradicted_by}"
                )
            continue
        assert finding.fact_id is not None
        fact = by_fact_id.get(finding.fact_id)
        if fact is None:
            errors.append(f"{finding.finding_id}:unknown fact ID {finding.fact_id}")
            continue
        if finding.fact_id not in selected:
            errors.append(f"{finding.finding_id}:fact ID is not selected")
        if fact.get("verification_state") not in {"verified", "policy_approved"}:
            errors.append(f"{finding.finding_id}:fact is not accepted")
        if any(conflict.get("status") == "unresolved" for conflict in fact.get("conflicts", [])):
            errors.append(f"{finding.finding_id}:fact has unresolved conflict")
        source_location = str((fact.get("source") or {}).get("location", ""))
        if finding.evidence_location != source_location:
            errors.append(f"{finding.finding_id}:evidence location disagrees with cited fact")
        evidence_excerpt = finding.evidence_excerpt
        assert evidence_excerpt is not None
        evidence = _fact_evidence_strings(fact)
        if not any(evidence_excerpt in value or value in evidence_excerpt for value in evidence):
            errors.append(f"{finding.finding_id}:evidence excerpt is not bound to cited fact")
        assessments = fact.get("evidence_assessments") or []
        matching = [
            item
            for item in assessments
            if evidence_excerpt
            in {
                str(item.get("anchor", "")),
                str(item.get("exact_excerpt", "")),
                str(item.get("context_excerpt", "")),
            }
        ]
        if matching:
            assessment = matching[0]
            if finding.expected_polarity != assessment.get("expected_polarity"):
                errors.append(f"{finding.finding_id}:expected polarity disagrees with evidence")
            if finding.observed_polarity != assessment.get("observed_polarity"):
                errors.append(f"{finding.finding_id}:observed polarity disagrees with evidence")
            derived = "supports" if assessment.get("accepted") else "contradicts"
            if finding.polarity_result != derived:
                errors.append(f"{finding.finding_id}:polarity result has wrong direction")
        elif (
            finding.expected_polarity != "positive_implementation"
            or finding.observed_polarity != "positive_implementation"
            or finding.polarity_result != "supports"
        ):
            errors.append(
                f"{finding.finding_id}:accepted evidence without an assessment must support"
            )
    return FindingGroundingResultV1(
        valid=not errors,
        errors=errors,
        checked_finding_ids=sorted(seen),
    )


def grounding_retry_context(
    *,
    errors: list[str],
    candidate_text: str,
    product_facts: dict | None,
) -> str:
    """Return bounded reconciliation evidence without another producer verdict."""

    payload = {
        "validation_errors": errors,
        "candidate_sha256_input_length": len(candidate_text.encode("utf-8")),
        "selected_fact_ids": (product_facts or {}).get("selected_fact_ids", {}),
        "accepted_fact_evidence": [
            {
                "fact_id": fact.get("fact_id"),
                "verification_state": fact.get("verification_state"),
                "evidence_location": (fact.get("source") or {}).get("location"),
                "evidence": sorted(_fact_evidence_strings(fact)),
                "evidence_assessments": fact.get("evidence_assessments") or [],
            }
            for fact in (product_facts or {}).get("facts", [])
            if isinstance(fact, dict)
            and fact.get("fact_id")
            in set((product_facts or {}).get("selected_fact_ids", {}).values())
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
