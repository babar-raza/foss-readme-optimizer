"""Pre-effect README factuality and protected-content gate."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.facts.protected_content import (
    fingerprint_protected_content,
    validate_protected_content,
)
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.runtime_context import load_runtime_link_inputs
from readme_agent.readme.claim_verification import find_claim_conflicts
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.markers import find_presentation_span


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
    *,
    source_text: str | None = None,
    product_facts_v2: dict | ProductFactsV2 | None = None,
    agentic_composition_plan: dict | None = None,
) -> CandidateFactualityDecisionV1:
    """Dispatch independent fact producers, then reject unsupported loss/claims."""

    if product_facts_v2 is not None:
        # The canonical local path already collected and durably bound ProductFactsV2 to
        # one immutable repository snapshot. Re-dispatching fact and package collectors
        # here can observe a later registry/repository state, leaks live credentials into
        # offline tests, and violates RepositorySnapshotV1's same-view invariant. The
        # document-plan branch below independently reconstructs every introduced claim
        # from this exact verified graph, so the legacy V1 conflict scan is neither needed
        # nor permitted on this path.
        current_v2 = ProductFactsV2.model_validate(product_facts_v2)
        claim_conflicts: list[dict] = []
    else:
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
        facts_v1 = ProductFactsV1.from_capability_results(
            facts_result,
            acquisition_results=acquisition_dispatch.result["results"],
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
    if product_facts_v2 is not None or find_presentation_span(final_text) is not None:
        immutable_source = source_text if source_text is not None else original_text
        identity = current_v2.selected_fact("product.identity")
        source_revision = identity.source.source_revision
        if source_revision is None:
            return CandidateFactualityDecisionV1(
                valid=False,
                product_facts_v2_hash=current_v2.canonical_hash(),
                error="product identity has no immutable source revision",
            )
        link_catalogs, link_allocation_policy = load_runtime_link_inputs(org_repo)
        expected, document_plan = build_readme_document_candidate(
            org_repo,
            immutable_source,
            current_v2,
            base_revision=source_revision,
            agentic_composition_plan=agentic_composition_plan,
            link_catalogs=link_catalogs,
            link_allocation_policy=link_allocation_policy,
        )
        document_validation = validate_readme_document_candidate(
            immutable_source,
            final_text,
            document_plan,
            current_v2,
            link_catalogs=link_catalogs,
        )
        losses = [
            {"category": "document_plan", "reason": error} for error in document_validation.errors
        ]
        protected_valid = document_validation.valid and expected == final_text
    else:
        protected = validate_protected_content(
            fingerprint_protected_content(original_text),
            fingerprint_protected_content(final_text),
        )
        losses = [loss.model_dump(mode="json") for loss in protected.losses]
        protected_valid = protected.valid
    return CandidateFactualityDecisionV1(
        valid=not claim_conflicts and protected_valid,
        product_facts_v2_hash=current_v2.canonical_hash(),
        claim_conflicts=claim_conflicts,
        protected_content_losses=losses,
    )
