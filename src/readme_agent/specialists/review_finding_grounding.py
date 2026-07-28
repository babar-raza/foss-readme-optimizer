"""Validate reviewer findings against exact candidate spans and accepted fact evidence."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FindingKind = Literal["quality", "factual"]
FindingPolarityResult = Literal["not_applicable", "supports", "contradicts", "missing"]
EvidencePolarity = Literal[
    "positive_implementation",
    "explicit_constraint",
    "ambiguous_occurrence",
]


class GroundedReviewFindingV1(BaseModel):
    """One review premise with inspectable candidate and fact anchors."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    kind: FindingKind
    criterion: str = Field(min_length=1)
    section: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    quoted_candidate_span: str = Field(min_length=1)
    fact_id: str | None = None
    evidence_excerpt: str | None = None
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
                    self.expected_polarity,
                    self.observed_polarity,
                )
            ):
                raise ValueError("quality finding cannot carry factual evidence fields")
            if self.polarity_result != "not_applicable":
                raise ValueError("quality finding polarity must be not_applicable")
        elif self.polarity_result == "missing":
            if self.fact_id is not None or self.evidence_excerpt is not None:
                raise ValueError("missing-evidence finding cannot cite a fact or evidence excerpt")
        elif self.fact_id is None or not self.evidence_excerpt:
            raise ValueError("supported/contradicted factual finding requires fact and evidence")
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
        if finding.kind != "factual" or finding.polarity_result == "missing":
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
                "evidence": sorted(_fact_evidence_strings(fact)),
            }
            for fact in (product_facts or {}).get("facts", [])
            if isinstance(fact, dict)
            and fact.get("fact_id")
            in set((product_facts or {}).get("selected_fact_ids", {}).values())
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
