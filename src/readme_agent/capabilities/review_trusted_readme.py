"""Independently review one trusted README candidate without factual promotion."""

from __future__ import annotations

from readme_agent.capabilities.contracts import materialize_contract_models
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.registry.loader import require_listed
from readme_agent.repository_snapshot import current_repository_snapshot
from readme_agent.specialists.trusted_transform_review import run_trusted_transform_review
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedReviewExecutionV1,
    TrustedTransformReviewV1,
)

CAPABILITY_ID = "review_trusted_readme"

MANIFEST = materialize_contract_models(
    CapabilityManifest(
        capability_id=CAPABILITY_ID,
        version="1",
        name="Review trusted README",
        purpose=(
            "Require deterministic validation plus separate blind-quality and inheritance-fidelity "
            "review without treating README-derived content as repository-verified truth."
        ),
        category="independent_verification",
        owner="readme_agent.specialists.trusted_transform_review",
        execution_type="agentic_analysis",
        required_inputs={"org_repo": "string"},
        produced_outputs={
            "review": "object",
            "cache_reused": "boolean",
            "provider_calls_before": "integer",
            "provider_calls_after": "integer",
            "fixture_calls_before": "integer",
            "fixture_calls_after": "integer",
            "cache_reuses_before": "integer",
            "cache_reuses_after": "integer",
            "accounting_status": "string",
            "ledger_path": "string",
            "ledger_sha256": "string",
            "provider_call_ids": "array",
            "calls_by_job": "object",
            "prompt_tokens": "integer|null",
            "completion_tokens": "integer|null",
            "total_tokens": "integer|null",
        },
        preconditions=[
            "org_repo is listed in data/products.json",
            "one immutable RepositorySnapshotV1 is bound to the current run",
            "trusted fact graph and composition output belong to that snapshot",
        ],
        required_permissions=["read_only_network"],
        side_effect_class="read_only_network",
        allowed_domains=[INDEPENDENT_VERIFICATION],
        model_route="blind_readme_quality_review+trusted_readme_fidelity_review",
        tools_used=[
            "llm.reviewer_client.LiveBlindQualityReviewClient",
            "llm.reviewer_client.LiveTrustedFidelityReviewClient",
            "specialists.trusted_transform_review.run_trusted_transform_review",
        ],
        failure_modes=[
            "LLMError when either role violates its schema or grounding contract",
            "ValueError when source, candidate, validation, or cache identity is stale",
        ],
        rollback_behavior="reopen only trusted review or the grounded responsible section",
        tests=["tests/unit/test_trusted_transform_review.py"],
        requirement_ids=["TRP-003", "TRP-006", "TRP-007"],
        input_model=OrgRepoOnlyInputV1,
        output_model=TrustedReviewExecutionV1,
        evidence_outputs=[
            "review",
            "cache_reused",
            "provider_calls_before",
            "provider_calls_after",
            "ledger_path",
            "ledger_sha256",
        ],
    )
)


def execute(
    org_repo: str,
    *,
    fact_graph: dict,
    composition_output: dict,
    blind_client=None,
    fidelity_client=None,
    cached_review: dict | None = None,
    enable_fidelity_batch_cache: bool = False,
) -> dict:
    """Review exact snapshot-bound inputs; clients and cache stay outside the tool schema."""

    require_listed(org_repo)
    snapshot = current_repository_snapshot(org_repo)
    if snapshot is None or snapshot.readme_path is None:
        raise RuntimeError("review_trusted_readme requires a bound README snapshot")
    graph = TrustedReadmeFactGraphV1.model_validate(fact_graph)
    composition = TrustedReadmeCompositionOutputV1.model_validate(composition_output)
    if graph.org_repo != org_repo or graph.source_revision != snapshot.source_revision:
        raise RuntimeError("trusted review fact graph is not bound to the current snapshot")
    source_text = (snapshot.root_path / snapshot.readme_path).read_text(encoding="utf-8")
    execution = run_trusted_transform_review(
        graph,
        source_text,
        composition,
        blind_client=blind_client,
        fidelity_client=fidelity_client,
        cached_review=(
            TrustedTransformReviewV1.model_validate(cached_review)
            if cached_review is not None
            else None
        ),
        enable_fidelity_batch_cache=enable_fidelity_batch_cache,
    )
    return execution.model_dump(mode="json")
