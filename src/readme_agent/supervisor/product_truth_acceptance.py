"""Bind exact product-fact acceptance identities to durable lifecycle state."""

from __future__ import annotations

from datetime import UTC, datetime

from readme_agent.errors import StateBackendError
from readme_agent.facts.acceptance_contract import ProductTruthOutcome
from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import (
    FactAcceptanceBindingV1,
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.readme_poc_lifecycle import migrate_readme_poc_lifecycle
from readme_agent.state.schema import RunStateV2


def _binding_identity(binding: FactAcceptanceBindingV1) -> tuple:
    return (
        binding.source_revision,
        binding.facts_hash,
        binding.contract_hash,
        binding.component_hashes,
        binding.outcome,
    )


def ensure_product_truth_acceptance_binding(
    state_backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    facts_hash: str,
    contract_hash: str,
    component_hashes: dict[str, str],
    outcome: ProductTruthOutcome,
    observed_by: str = "supervisor_product_truth",
    reason: str = "exact ProductFactsV2 graph accepted under the current contract",
) -> ReadmePocLifecycleStateV2:
    """Append the full acceptance identity once after an ordinary fact transition."""

    expected_identity = source_revision, facts_hash, contract_hash, component_hashes, outcome
    now = datetime.now(UTC).isoformat()

    def patch(state: RunStateV2) -> RunStateV2:
        stored = state.readme_poc_lifecycle
        lifecycle = (
            migrate_readme_poc_lifecycle(stored)
            if isinstance(stored, ReadmePocLifecycleStateV1)
            else stored
        )
        if (
            lifecycle is None
            or lifecycle.content_assurance != "repository_verified"
            or lifecycle.source_revision != source_revision
            or lifecycle.facts_hash != facts_hash
            or lifecycle.fact_acceptance_contract_hash != contract_hash
            or lifecycle.fact_acceptance_component_hashes != component_hashes
        ):
            raise StateBackendError(
                f"cannot bind fact acceptance for non-current product truth {org_repo!r}"
            )
        latest = (
            lifecycle.fact_acceptance_history[-1] if lifecycle.fact_acceptance_history else None
        )
        if latest is not None and _binding_identity(latest) == expected_identity:
            return state
        binding = FactAcceptanceBindingV1(
            source_revision=source_revision,
            facts_hash=facts_hash,
            contract_hash=contract_hash,
            component_hashes=component_hashes,
            outcome=outcome,
            observed_by=observed_by,
            reason=reason,
            occurred_at=now,
        )
        updated = lifecycle.model_copy(
            update={
                "updated_at": now,
                "fact_acceptance_history": [*lifecycle.fact_acceptance_history, binding],
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": updated})

    saved = save_state_patch(state_backend, org_repo, patch)
    assert isinstance(saved.readme_poc_lifecycle, ReadmePocLifecycleStateV2)
    return saved.readme_poc_lifecycle
