"""Pre-effect README factuality and protected-content gate."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.protected_content import (
    fingerprint_protected_content,
    validate_protected_content,
)
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_verification import find_claim_conflicts


class CandidateFactualityDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    product_facts_v2_hash: str | None = None
    claim_conflicts: list[dict] = Field(default_factory=list)
    protected_content_losses: list[dict] = Field(default_factory=list)
    error: str | None = None


def evaluate_candidate_factuality(
    org_repo: str,
    original_text: str,
    final_text: str,
    permissions: set[PermissionClass],
) -> CandidateFactualityDecisionV1:
    """Dispatch independent fact producers, then reject unsupported loss/claims."""

    facts_dispatch = dispatch_tool_call(
        {
            "function": {
                "name": "get_product_facts",
                "arguments": json.dumps({"org_repo": org_repo}),
            }
        },
        permissions,
    )
    if facts_dispatch.outcome != "executed" or facts_dispatch.result is None:
        return CandidateFactualityDecisionV1(
            valid=False,
            error=f"get_product_facts:{facts_dispatch.outcome}:{facts_dispatch.error}",
        )

    acquisition_dispatch = dispatch_tool_call(
        {
            "function": {
                "name": "verify_package_acquisition",
                "arguments": json.dumps({"org_repo": org_repo}),
            }
        },
        permissions,
    )
    if acquisition_dispatch.outcome != "executed" or acquisition_dispatch.result is None:
        return CandidateFactualityDecisionV1(
            valid=False,
            error=(
                "verify_package_acquisition:"
                f"{acquisition_dispatch.outcome}:{acquisition_dispatch.error}"
            ),
        )

    facts_result = facts_dispatch.result
    current_v2 = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
    provenance_fact = current_v2.selected_fact("product.identity")
    facts_v1 = ProductFactsV1.from_capability_results(
        facts_result,
        acquisition_results=acquisition_dispatch.result["results"],
    )
    product_facts = migrate_product_facts_v1(
        facts_v1,
        source_revision=provenance_fact.source.source_revision,
        observed_at=provenance_fact.source.retrieved_at,
    )

    claim_conflicts = [
        {
            "package_root_path": finding.package_root_path,
            "ecosystem": finding.ecosystem,
            "claimed_coordinate": finding.claimed_coordinate,
            "verification_outcome": finding.verification_outcome,
            "verification_detail": finding.verification_detail,
            "readme_excerpt": finding.readme_excerpt,
        }
        for finding in find_claim_conflicts(final_text, facts_v1)
    ]
    protected = validate_protected_content(
        fingerprint_protected_content(original_text),
        fingerprint_protected_content(final_text),
    )
    losses = [loss.model_dump(mode="json") for loss in protected.losses]
    return CandidateFactualityDecisionV1(
        valid=not claim_conflicts and protected.valid,
        product_facts_v2_hash=product_facts.canonical_hash(),
        claim_conflicts=claim_conflicts,
        protected_content_losses=losses,
    )
