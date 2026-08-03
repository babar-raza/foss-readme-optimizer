"""Map every generated README operation to its selected accepted fact records."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.fact_grounding import find_literal_fact_match
from readme_agent.readme.markers import find_presentation_span


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadmeClaimBindingV1(_StrictModel):
    claim_id: str
    operation_id: str
    fact_id: str
    field: str
    verification_state: Literal["verified", "policy_approved"]
    fact_value_sha256: str
    introduced_text_sha256: str
    coordinate_space: Literal["candidate_utf8", "presentation_inner_source_utf8"]
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    claim_text_sha256: str
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _valid_span(self) -> ReadmeClaimBindingV1:
        if self.byte_end < self.byte_start:
            raise ValueError("claim byte_end must be >= byte_start")
        return self


class ReadmeClaimMapV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str
    facts_hash: str
    candidate_sha256: str
    claims: list[ReadmeClaimBindingV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_claim_ids(self) -> ReadmeClaimMapV1:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("README claim map contains duplicate claim IDs")
        return self

    def canonical_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_readme_claim_map(
    plan: ReadmeDocumentPlanV1,
    facts: ProductFactsV2,
    *,
    source_text: str,
    candidate_text: str,
) -> ReadmeClaimMapV1:
    """Map each selected fact to exact introduced or removed README bytes."""

    claims = []
    existing = find_presentation_span(source_text)
    source_inner = existing.content if existing is not None else source_text
    source_bytes = source_inner.encode("utf-8")
    for operation in plan.operations:
        if not operation.fact_ids:
            continue
        if operation.replacement_text:
            replacement_character_start = candidate_text.find(operation.replacement_text)
            operation_claim_text = operation.replacement_text
            operation_byte_start = (
                len(candidate_text[:replacement_character_start].encode("utf-8"))
                if replacement_character_start >= 0
                else None
            )
            coordinate_space: Literal["candidate_utf8", "presentation_inner_source_utf8"] = (
                "candidate_utf8"
            )
        else:
            operation_claim_text = source_bytes[
                operation.source_byte_start : operation.source_byte_end
            ].decode("utf-8")
            operation_byte_start = operation.source_byte_start
            coordinate_space = "presentation_inner_source_utf8"
        operation_claim_count = 0
        for fact_id in operation.fact_ids:
            selected = facts.fact_by_id(fact_id)
            if facts.selected_fact_ids.get(selected.field) != fact_id:
                raise ValueError(f"document operation cites non-selected fact {fact_id!r}")
            if (
                selected.verification_state not in {"verified", "policy_approved"}
                or selected.has_unresolved_conflict
            ):
                raise ValueError(
                    f"document operation cites ineligible fact "
                    f"{fact_id!r}:{selected.verification_state}"
                )
            fact_value = json.dumps(
                selected.value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
            literal_match = find_literal_fact_match(operation_claim_text, selected.value)
            if literal_match is None:
                continue
            claim_text = operation_claim_text[literal_match.line_start : literal_match.line_end]
            if operation_byte_start is None:
                candidate_character_start = candidate_text.find(claim_text)
                if candidate_character_start < 0:
                    raise ValueError(
                        "document operation fact text is absent from candidate: "
                        f"{operation.operation_id!r}:{selected.field!r}"
                    )
                byte_start = len(candidate_text[:candidate_character_start].encode("utf-8"))
            else:
                relative_character_start = literal_match.line_start
                relative_byte_start = len(
                    operation_claim_text[:relative_character_start].encode("utf-8")
                )
                byte_start = operation_byte_start + relative_byte_start
            byte_end = byte_start + len(claim_text.encode("utf-8"))
            claims.append(
                ReadmeClaimBindingV1(
                    claim_id=f"{operation.operation_id}:{selected.field}",
                    operation_id=operation.operation_id,
                    fact_id=fact_id,
                    field=selected.field,
                    verification_state=selected.verification_state,
                    fact_value_sha256=hashlib.sha256(fact_value.encode("utf-8")).hexdigest(),
                    introduced_text_sha256=operation.replacement_sha256,
                    coordinate_space=coordinate_space,
                    byte_start=byte_start,
                    byte_end=byte_end,
                    claim_text_sha256=sha256_hex(claim_text),
                    rationale=operation.rationale,
                )
            )
            operation_claim_count += 1
        if operation.replacement_text and operation.fact_ids and operation_claim_count == 0:
            raise ValueError(
                f"document operation cites no literal rendered fact: {operation.operation_id!r}"
            )
    candidate_bytes = candidate_text.encode("utf-8")
    for provenance in plan.candidate_content_provenance:
        if not provenance.fact_ids:
            continue
        bound_bytes = candidate_bytes[
            provenance.candidate_byte_start : provenance.candidate_byte_end
        ]
        bound_text = bound_bytes.decode("utf-8")
        for fact_id in provenance.fact_ids:
            selected = facts.fact_by_id(fact_id)
            if facts.selected_fact_ids.get(selected.field) != fact_id:
                raise ValueError(f"candidate provenance cites non-selected fact {fact_id!r}")
            if (
                selected.verification_state not in {"verified", "policy_approved"}
                or selected.has_unresolved_conflict
            ):
                raise ValueError(
                    f"candidate provenance cites ineligible fact "
                    f"{fact_id!r}:{selected.verification_state}"
                )
            literal_match = find_literal_fact_match(bound_text, selected.value)
            if literal_match is None:
                continue
            fact_value = json.dumps(
                selected.value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            )
            claim_text = bound_text[literal_match.line_start : literal_match.line_end]
            relative_byte_start = len(bound_text[: literal_match.line_start].encode("utf-8"))
            byte_start = provenance.candidate_byte_start + relative_byte_start
            claims.append(
                ReadmeClaimBindingV1(
                    claim_id=f"{provenance.provenance_id}:{selected.field}",
                    operation_id=provenance.provenance_id,
                    fact_id=fact_id,
                    field=selected.field,
                    verification_state=selected.verification_state,
                    fact_value_sha256=hashlib.sha256(fact_value.encode("utf-8")).hexdigest(),
                    introduced_text_sha256=sha256_hex(bound_bytes),
                    coordinate_space="candidate_utf8",
                    byte_start=byte_start,
                    byte_end=byte_start + len(claim_text.encode("utf-8")),
                    claim_text_sha256=sha256_hex(claim_text),
                    rationale=provenance.rationale,
                )
            )
    return ReadmeClaimMapV1(
        org_repo=plan.org_repo,
        facts_hash=plan.facts_hash,
        candidate_sha256=plan.candidate_sha256,
        claims=claims,
    )
