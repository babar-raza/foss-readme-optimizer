"""Map every generated README operation to its selected accepted fact records."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1


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
    rationale: str = Field(min_length=1)


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
) -> ReadmeClaimMapV1:
    """Build a deterministic, selected-fact-only map for introduced or corrected prose."""

    claims = []
    for operation in plan.operations:
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
            claims.append(
                ReadmeClaimBindingV1(
                    claim_id=f"{operation.operation_id}:{selected.field}",
                    operation_id=operation.operation_id,
                    fact_id=fact_id,
                    field=selected.field,
                    verification_state=selected.verification_state,
                    fact_value_sha256=hashlib.sha256(fact_value.encode("utf-8")).hexdigest(),
                    introduced_text_sha256=operation.replacement_sha256,
                    rationale=operation.rationale,
                )
            )
    return ReadmeClaimMapV1(
        org_repo=plan.org_repo,
        facts_hash=plan.facts_hash,
        candidate_sha256=plan.candidate_sha256,
        claims=claims,
    )
