"""Recover a sealed product-fact bundle whose durable commit was interrupted."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.facts.acceptance_contract import (
    ProductTruthOutcome,
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.state.backend import StateBackend
from readme_agent.state.cas import save_state_patch
from readme_agent.state.lifecycle_schema import (
    FactAcceptanceBindingV1,
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
    ReadmePocTransitionV2,
)
from readme_agent.state.readme_poc_lifecycle import migrate_readme_poc_lifecycle
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.product_truth_provenance import (
    load_coherent_product_truth_proposal,
    load_product_truth_json_object,
)

_FACT_BOUNDARY_STATUSES = frozenset(
    {
        "PROFILED",
        "FACTS_COLLECTING",
        "FACTS_READY",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
    }
)
_FACT_OUTCOMES = frozenset({"FACTS_READY", "BLOCKED_FACT_CONFLICT", "BLOCKED_MISSING_EVIDENCE"})


def _binding_identity(binding: FactAcceptanceBindingV1) -> tuple:
    return (
        binding.source_revision,
        binding.facts_hash,
        binding.contract_hash,
        binding.component_hashes,
        binding.outcome,
    )


def _commit_recovered_product_truth(
    state_backend: StateBackend,
    org_repo: str,
    *,
    source_revision: str,
    facts_hash: str,
    outcome: ProductTruthOutcome,
    evidence_refs: list[str],
    prompt_hash: str | None,
    contract_hash: str,
    component_hashes: dict[str, str],
) -> ReadmePocLifecycleStateV2:
    """Decide recovery eligibility and mutate within one fresh CAS closure."""

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
        ):
            raise StateBackendError(
                f"cannot recover product truth for {org_repo!r} without its current profile"
            )
        latest = (
            lifecycle.fact_acceptance_history[-1] if lifecycle.fact_acceptance_history else None
        )
        core_matches = (
            lifecycle.facts_hash == facts_hash
            and lifecycle.prompt_hash == prompt_hash
            and lifecycle.fact_acceptance_contract_hash == contract_hash
            and lifecycle.fact_acceptance_component_hashes == component_hashes
        )
        binding_matches = latest is not None and _binding_identity(latest) == expected_identity
        if lifecycle.status not in _FACT_BOUNDARY_STATUSES or any(
            (
                lifecycle.assessment_hash,
                lifecycle.presentation_plan_hash,
                lifecycle.candidate_hash,
            )
        ):
            if core_matches and binding_matches:
                return state
            raise RuntimeError(
                "interrupted product-truth recovery observed newer incompatible lifecycle state"
            )
        if lifecycle.status == outcome and core_matches:
            if binding_matches:
                return state
            binding = FactAcceptanceBindingV1(
                source_revision=source_revision,
                facts_hash=facts_hash,
                contract_hash=contract_hash,
                component_hashes=component_hashes,
                outcome=outcome,
                observed_by="supervisor_product_truth_recovery",
                reason="sealed ProductFactsV2 acceptance binding recovered after interruption",
                occurred_at=now,
            )
            updated = lifecycle.model_copy(
                update={
                    "updated_at": now,
                    "fact_acceptance_history": [*lifecycle.fact_acceptance_history, binding],
                }
            )
            return state.model_copy(update={"readme_poc_lifecycle": updated})

        transitions = list(lifecycle.history)
        from_status = lifecycle.status
        if from_status != "FACTS_COLLECTING":
            transitions.append(
                ReadmePocTransitionV2(
                    from_status=from_status,
                    to_status="FACTS_COLLECTING",
                    reason=(
                        "sealed fact inputs recovered; invalidating only dependent README stages"
                    ),
                    observed_by="supervisor_product_truth_recovery",
                    occurred_at=now,
                    source_revision=source_revision,
                )
            )
            from_status = "FACTS_COLLECTING"
        transitions.append(
            ReadmePocTransitionV2(
                from_status=from_status,
                to_status=outcome,
                reason="checksum-sealed ProductFactsV2 commit recovered after interruption",
                evidence_refs=evidence_refs,
                observed_by="supervisor_product_truth_recovery",
                occurred_at=now,
                source_revision=source_revision,
            )
        )
        acceptance_history = lifecycle.fact_acceptance_history
        if not binding_matches:
            acceptance_history = [
                *acceptance_history,
                FactAcceptanceBindingV1(
                    source_revision=source_revision,
                    facts_hash=facts_hash,
                    contract_hash=contract_hash,
                    component_hashes=component_hashes,
                    outcome=outcome,
                    observed_by="supervisor_product_truth_recovery",
                    reason="checksum-sealed ProductFactsV2 accepted during interrupted recovery",
                    occurred_at=now,
                ),
            ]
        updated = lifecycle.model_copy(
            update={
                "status": outcome,
                "updated_at": now,
                "history": transitions,
                "facts_hash": facts_hash,
                "assessment_hash": None,
                "presentation_plan_hash": None,
                "candidate_hash": None,
                "prompt_hash": prompt_hash,
                "fact_acceptance_contract_hash": contract_hash,
                "fact_acceptance_component_hashes": component_hashes,
                "fact_acceptance_history": acceptance_history,
                "reviewer_standard_hash": None,
                "protected_content_fingerprint": None,
                "repair_budget_origin_hash": None,
                "repair_attempts_for_revision": 0,
                "details": {},
            }
        )
        return state.model_copy(update={"readme_poc_lifecycle": updated})

    saved = save_state_patch(state_backend, org_repo, patch)
    assert isinstance(saved.readme_poc_lifecycle, ReadmePocLifecycleStateV2)
    return saved.readme_poc_lifecycle


def recover_interrupted_product_truth_commit(
    org_repo: str,
    source_revision: str,
    bundle_dir: Path,
    state_backend: StateBackend,
    lifecycle: ReadmePocLifecycleStateV2,
    *,
    ecosystem: str | None = None,
    family: str | None = None,
) -> ReadmePocLifecycleStateV2 | None:
    """Commit a current checksum-sealed fact bundle left ahead of durable state."""

    if (
        lifecycle.content_assurance != "repository_verified"
        or lifecycle.source_revision != source_revision
        or lifecycle.status not in _FACT_BOUNDARY_STATUSES
        or any(
            (
                lifecycle.assessment_hash,
                lifecycle.presentation_plan_hash,
                lifecycle.candidate_hash,
            )
        )
    ):
        return None

    manifest_path = bundle_dir / "manifest.json"
    facts_path = bundle_dir / "facts" / "product-facts.json"
    if not manifest_path.is_file() or not facts_path.is_file():
        return None
    manifest = load_product_truth_json_object(manifest_path, "manifest")

    current_contract = current_fact_acceptance_contract(ecosystem, family)
    if (
        manifest.get("org_repo") != org_repo
        or manifest.get("source_revision") != source_revision
        or manifest.get("local_verification_contract_hash")
        != local_verification_contract_hash(ecosystem)
        or manifest.get("fact_acceptance_contract_hash") != current_contract.canonical_hash()
        or manifest.get("fact_acceptance_component_hashes") != current_contract.component_hashes
    ):
        return None

    if not verify_sha256sums(bundle_dir):
        raise RuntimeError(
            "interrupted product-truth recovery refused a bundle with an invalid checksum inventory"
        )
    proposed_product_truth = load_coherent_product_truth_proposal(bundle_dir, manifest)
    if proposed_product_truth is not None and manifest.get("resolution_source") == "agent_draft":
        return None

    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    facts_hash = facts.canonical_hash()
    identity_revision = facts.selected_fact("product.identity").source.source_revision
    outcome = classify_product_truth(facts, current_contract)
    if (
        facts.org_repo != org_repo
        or (identity_revision is not None and identity_revision != source_revision)
        or manifest.get("facts_hash") != facts_hash
        or manifest.get("lifecycle_status") not in _FACT_OUTCOMES
        or manifest.get("lifecycle_status") != outcome
    ):
        raise RuntimeError(
            "interrupted product-truth recovery found inconsistent bundle identity or outcome"
        )

    return _commit_recovered_product_truth(
        state_backend,
        org_repo,
        source_revision=source_revision,
        facts_hash=facts_hash,
        outcome=outcome,
        evidence_refs=[
            str(facts_path),
            str(bundle_dir / "facts" / "provenance.json"),
            str(bundle_dir / "facts" / "conflicts.json"),
        ],
        prompt_hash=manifest.get("prompt_hash"),
        contract_hash=current_contract.canonical_hash(),
        component_hashes=current_contract.component_hashes,
    )
