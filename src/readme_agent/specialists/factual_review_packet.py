"""Build a compact, hash-bound factual README review packet."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.fact_grounding import fact_strings
from readme_agent.specialists.readme_review_roles import json_hash


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactualReviewFactV1(_StrictModel):
    fact_id: str
    field: str
    value: Any
    verification_state: str
    evidence_location: str
    evidence_assessments: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)


class FactualReviewOperationV1(_StrictModel):
    operation_id: str
    operation: str
    fact_ids: list[str] = Field(default_factory=list)
    protected_content_treatment: str
    rationale: str


class FactualReviewClaimV1(_StrictModel):
    claim_id: str
    operation_id: str
    fact_id: str
    field: str
    claim_text: str
    verification_state: str
    evidence_location: str
    evidence_excerpt: str
    unresolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    rationale: str


class FactualReviewSourceSectionV1(_StrictModel):
    section_id: str
    heading: str
    disposition: str
    fact_ids: list[str] = Field(default_factory=list)
    protected_fragment_ids: list[str] = Field(default_factory=list)
    rationale: str


class FactualReviewPacketV1(_StrictModel):
    schema_version: int = 1
    org_repo: str
    candidate_sha256: str
    product_facts_sha256: str
    presentation_plan_sha256: str
    selected_fact_ids: dict[str, str]
    selected_facts: list[FactualReviewFactV1]
    surface_plan: dict[str, Any]
    source_sections: list[FactualReviewSourceSectionV1]
    operations: list[FactualReviewOperationV1]
    candidate_claims: list[FactualReviewClaimV1]

    def canonical_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def fact_context(self) -> dict[str, Any]:
        return {
            "selected_fact_ids": self.selected_fact_ids,
            "selected_facts": [fact.model_dump(mode="json") for fact in self.selected_facts],
        }

    def plan_context(self) -> dict[str, Any]:
        return {
            "surface_plan": self.surface_plan,
            "source_sections": [
                section.model_dump(mode="json") for section in self.source_sections
            ],
            "operations": [operation.model_dump(mode="json") for operation in self.operations],
            "candidate_claims": [claim.model_dump(mode="json") for claim in self.candidate_claims],
        }


def _candidate_claim_text(candidate_text: str, binding: dict[str, Any]) -> str | None:
    if binding.get("coordinate_space") != "candidate_utf8":
        return None
    candidate_bytes = candidate_text.encode("utf-8")
    start = int(binding.get("byte_start", -1))
    end = int(binding.get("byte_end", -1))
    if start < 0 or end < start or end > len(candidate_bytes):
        raise ValueError(f"candidate claim has invalid UTF-8 span: {binding.get('claim_id')!r}")
    claim_text = candidate_bytes[start:end].decode("utf-8")
    if sha256_hex(claim_text) != binding.get("claim_text_sha256"):
        raise ValueError(f"candidate claim hash mismatch: {binding.get('claim_id')!r}")
    return claim_text


def _claim_evidence_excerpt(claim_text: str, fact: dict[str, Any]) -> str:
    """Choose exact supplied fact text, preferring a literal claim match."""

    values = fact_strings(fact.get("value"))
    if not values:
        raise ValueError(f"candidate claim cites an empty fact: {fact.get('fact_id')!r}")
    folded_claim = claim_text.casefold()
    literal_matches = [value for value in values if value.casefold() in folded_claim]
    if literal_matches:
        return max(literal_matches, key=len)
    return values[0]


def build_factual_review_packet(
    org_repo: str,
    candidate_text: str,
    product_facts: dict[str, Any],
    presentation_plan: dict[str, Any],
) -> FactualReviewPacketV1:
    """Project full producer artifacts into the exact evidence a factual reviewer needs."""

    selected_fact_ids = {
        str(field): str(fact_id)
        for field, fact_id in (product_facts.get("selected_fact_ids") or {}).items()
    }
    selected_ids = set(selected_fact_ids.values())
    selected_facts_by_id: dict[str, dict[str, Any]] = {}
    selected_facts = []
    for fact in product_facts.get("facts") or []:
        if not isinstance(fact, dict) or fact.get("fact_id") not in selected_ids:
            continue
        selected_facts_by_id[str(fact["fact_id"])] = fact
        selected_facts.append(
            FactualReviewFactV1(
                fact_id=str(fact["fact_id"]),
                field=str(fact["field"]),
                value=fact.get("value"),
                verification_state=str(fact.get("verification_state", "")),
                evidence_location=str((fact.get("source") or {}).get("location", "")),
                evidence_assessments=list(fact.get("evidence_assessments") or []),
                unresolved_conflicts=[
                    conflict
                    for conflict in fact.get("conflicts") or []
                    if isinstance(conflict, dict) and conflict.get("status") == "unresolved"
                ],
            )
        )
    if {fact.fact_id for fact in selected_facts} != selected_ids:
        raise ValueError("factual review packet is missing one or more selected facts")

    document_plan = presentation_plan.get("readme_document_plan") or presentation_plan
    operations = [
        FactualReviewOperationV1(
            operation_id=str(operation.get("operation_id", "")),
            operation=str(operation.get("operation", "")),
            fact_ids=[str(item) for item in operation.get("fact_ids") or []],
            protected_content_treatment=str(
                operation.get("protected_content_treatment", "unspecified")
            ),
            rationale=str(operation.get("rationale", "")),
        )
        for operation in document_plan.get("operations") or []
        if isinstance(operation, dict)
    ]

    assessment = presentation_plan.get("readme_assessment") or {}
    source_sections = [
        FactualReviewSourceSectionV1(
            section_id=str(section.get("section_id", "")),
            heading=str(section.get("heading", "")),
            disposition=str(section.get("disposition", "")),
            fact_ids=[str(item) for item in section.get("fact_ids") or []],
            protected_fragment_ids=[
                str(item) for item in section.get("protected_fragment_ids") or []
            ],
            rationale=str(section.get("rationale", "")),
        )
        for section in assessment.get("sections") or []
        if isinstance(section, dict)
    ]

    claim_map = presentation_plan.get("claim_map") or {}
    candidate_claims = []
    for binding in claim_map.get("claims") or []:
        if not isinstance(binding, dict):
            continue
        claim_text = _candidate_claim_text(candidate_text, binding)
        if claim_text is None:
            continue
        fact_id = str(binding.get("fact_id", ""))
        fact = selected_facts_by_id.get(fact_id)
        if fact is None:
            raise ValueError(f"candidate claim cites a non-selected fact: {fact_id!r}")
        candidate_claims.append(
            FactualReviewClaimV1(
                claim_id=str(binding.get("claim_id", "")),
                operation_id=str(binding.get("operation_id", "")),
                fact_id=fact_id,
                field=str(binding.get("field", "")),
                claim_text=claim_text,
                verification_state=str(fact.get("verification_state", "")),
                evidence_location=str((fact.get("source") or {}).get("location", "")),
                evidence_excerpt=_claim_evidence_excerpt(claim_text, fact),
                unresolved_conflicts=[
                    conflict
                    for conflict in fact.get("conflicts") or []
                    if isinstance(conflict, dict) and conflict.get("status") == "unresolved"
                ],
                rationale=str(binding.get("rationale", "")),
            )
        )

    return FactualReviewPacketV1(
        org_repo=org_repo,
        candidate_sha256=sha256_hex(candidate_text),
        product_facts_sha256=json_hash(product_facts),
        presentation_plan_sha256=json_hash(presentation_plan),
        selected_fact_ids=selected_fact_ids,
        selected_facts=sorted(selected_facts, key=lambda fact: (fact.field, fact.fact_id)),
        surface_plan=dict(presentation_plan.get("presentation_plan") or {}),
        source_sections=source_sections,
        operations=operations,
        candidate_claims=candidate_claims,
    )
