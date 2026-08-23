"""Fingerprint every implementation that can alter sealed portfolio acceptance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from readme_agent.presentation.candidate_benchmark_acceptance_contracts import (
    canonical_benchmark_acceptance_payload_hash,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    load_benchmark_quality_profile,
)
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import (
    EvidenceBundleV1,
    comparison_evidence_paths_are_bound,
)
from readme_agent.verification.sealed_transaction_replay import (
    CompleteTransactionNoOpProofV1,
    ReplayAttestationContractV1,
    canonical_json_sha256,
    canonical_proof_hash,
)

_ROOT = Path(__file__).resolve().parents[4]
_ACCEPTANCE_FILES = (
    "src/readme_agent/presentation/candidate_benchmark_acceptance.py",
    "src/readme_agent/presentation/candidate_benchmark_acceptance_contracts.py",
    "src/readme_agent/presentation/candidate_benchmark_acceptance_policy.py",
    "src/readme_agent/presentation/candidate_benchmark_acceptance_evaluation.py",
    "src/readme_agent/presentation/candidate_benchmark_comparison.py",
    "data/aspose_benchmark_quality_profile.json",
    "src/readme_agent/supervisor/portfolio_proof_engine/acceptance_contract.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/benchmark_gate.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/dashboard.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/replay_gate.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/evidence_bundle.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/full_pipeline_modes.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/receipt_store.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/rubric.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/rubric_criteria.py",
    "src/readme_agent/supervisor/portfolio_proof_engine/rubric_evidence.py",
    "src/readme_agent/validation/public_quality_contracts.py",
    "src/readme_agent/validation/public_quality_registry.py",
    "src/readme_agent/validation/public_quality_structure_checks.py",
    "src/readme_agent/verification/local_poc_replay_contract.py",
    "src/readme_agent/verification/sealed_transaction_replay.py",
    "src/readme_agent/verification/sealed_transaction_replay_artifacts.py",
    "src/readme_agent/verification/sealed_transaction_replay_attestor.py",
    "src/readme_agent/verification/sealed_transaction_replay_attestor_bundle.py",
    "src/readme_agent/verification/sealed_transaction_replay_attestor_effects.py",
    "src/readme_agent/verification/sealed_transaction_replay_attestor_findings.py",
    "src/readme_agent/verification/sealed_transaction_replay_attestor_state.py",
    "src/readme_agent/verification/sealed_transaction_replay_contracts.py",
    "src/readme_agent/verification/sealed_transaction_replay_effects.py",
    "src/readme_agent/verification/sealed_transaction_replay_identity.py",
    "src/readme_agent/verification/sealed_transaction_replay_inventory.py",
    "src/readme_agent/verification/sealed_transaction_replay_json.py",
    "src/readme_agent/verification/sealed_transaction_replay_paths.py",
    "src/readme_agent/verification/sealed_transaction_replay_proof.py",
    "src/readme_agent/verification/sealed_transaction_replay_provider.py",
    "src/readme_agent/verification/sealed_transaction_replay_results.py",
    "src/readme_agent/verification/sealed_transaction_replay_vocabulary.py",
)


def portfolio_acceptance_contract_hash() -> str:
    digest = hashlib.sha256()
    for relative in _ACCEPTANCE_FILES:
        path = _ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def replay_attestation_contract_hash(contract: ReplayAttestationContractV1) -> str:
    """Hash a replay contract with the attestor's declaration-order-independent projection."""

    payload = contract.model_dump(mode="json")
    payload["artifacts"] = sorted(payload["artifacts"], key=lambda item: item["artifact_id"])
    payload["identity_bindings"] = sorted(
        payload["identity_bindings"], key=lambda item: item["component"]
    )
    payload["product_effects"] = sorted(payload["product_effects"], key=lambda item: item["effect"])
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def benchmark_acceptance_proven(bundle: EvidenceBundleV1) -> bool | None:
    """Require current, manifest-bound benchmark acceptance for this exact candidate."""

    acceptance, comparison, manifest = (
        bundle.benchmark_acceptance,
        bundle.benchmark_comparison,
        bundle.manifest,
    )
    if acceptance is None or comparison is None or manifest is None or bundle.bundle_dir is None:
        return None
    applicable = set(acceptance.applicable_dimension_ids)
    dimensions = {item.dimension_id: item for item in acceptance.dimensions}
    comparison_dimensions = {
        item.dimension_id: item for item in comparison.dimensions if item.applicable
    }
    comparison_payload = comparison.model_dump(mode="json")
    comparison_payload["dimensions"] = sorted(
        comparison_payload["dimensions"], key=lambda item: item["dimension_id"]
    )
    current_profile_hash = load_benchmark_quality_profile()[1]
    return all(
        (
            acceptance.acceptance_status == "BENCHMARK_ACCEPTANCE_PROVEN",
            acceptance.repository == bundle.org_repo,
            acceptance.source_revision == bundle.source_revision,
            acceptance.candidate_sha256 == bundle.candidate_hash,
            acceptance.facts_hash == manifest.get("facts_hash"),
            not acceptance.unresolved_dimension_ids,
            not acceptance.hard_disqualifiers,
            not acceptance.failure_reasons,
            bool(applicable),
            all(item in dimensions and dimensions[item].verdict == "PASS" for item in applicable),
            applicable == set(comparison_dimensions),
            comparison_evidence_paths_are_bound(Path(bundle.bundle_dir), comparison),
            comparison.repository == bundle.org_repo,
            comparison.source_revision == bundle.source_revision,
            comparison.candidate_sha256 == bundle.candidate_hash,
            comparison.benchmark_profile_sha256 == acceptance.benchmark_profile_sha256,
            comparison.benchmark_profile_sha256 == current_profile_hash,
            acceptance.comparison_identity_sha256
            == canonical_benchmark_acceptance_payload_hash(comparison_payload),
            manifest.get("benchmark_acceptance_proven") is True,
            manifest.get("benchmark_acceptance_hash") == acceptance.canonical_hash(),
            manifest.get("portfolio_acceptance_contract_hash")
            == portfolio_acceptance_contract_hash(),
        )
    )


def replay_attestation_proven(bundle: EvidenceBundleV1) -> bool | None:
    """Require a self-consistent replay proof with zero calls and zero product effects."""

    attestation, contract, manifest = (
        bundle.replay_attestation,
        bundle.replay_contract,
        bundle.manifest,
    )
    if attestation is None or contract is None or manifest is None:
        return None
    proof = attestation.proof
    candidate_hash, facts_hash, revision = (
        bundle.candidate_hash,
        manifest.get("facts_hash"),
        bundle.source_revision,
    )
    if not all(isinstance(item, str) and item for item in (candidate_hash, facts_hash, revision)):
        return False
    assert isinstance(candidate_hash, str)
    assert isinstance(facts_hash, str)
    assert isinstance(revision, str)
    expected_components = {
        "repository_identity": canonical_json_sha256(bundle.org_repo),
        "source_revision": canonical_json_sha256(revision),
        "facts_hash": canonical_json_sha256(facts_hash),
        "candidate_hash": canonical_json_sha256(candidate_hash),
    }
    identities_match = all(
        identity.org_repo == bundle.org_repo
        and identity.source_revision == revision
        and not identity.missing_required_components
        and not identity.malformed_components
        and all(
            identity.component_digests.get(name) == digest
            for name, digest in expected_components.items()
        )
        for identity in (proof.first_identity, proof.replay_identity)
    )
    provider, effects = proof.provider_delta, proof.effect_delta
    required_effects = {
        "readme_write",
        "target_tree_change",
        "commit",
        "branch",
        "push",
        "pull_request",
        "publication",
        "duplicate_lifecycle_effect",
    }
    required_contract_effects = {
        item.effect for item in contract.product_effects if item.level == "REQUIRED"
    }
    return all(
        (
            proof.passed,
            bool(proof.checks) and all(proof.checks.values()),
            not proof.failures,
            not proof.findings,
            canonical_proof_hash(proof) == proof.proof_hash,
            proof.org_repo == bundle.org_repo == contract.org_repo,
            proof.expected_source_revision == revision == contract.expected_source_revision,
            proof.contract_id == contract.contract_id,
            proof.contract_digest == replay_attestation_contract_hash(contract),
            identities_match,
            provider.accounting_certain,
            provider.declared_accounting_consistent,
            provider.ledger_superset_ok,
            provider.ledger_temporal_ok,
            provider.ledger_scope_ok,
            provider.first_provider_call_count is not None,
            provider.replay_provider_call_count == provider.first_provider_call_count,
            not provider.replay_new_provider_call_ids,
            provider.replay_authoring_calls == 0,
            provider.replay_factual_review_calls == 0,
            provider.replay_visitor_review_calls == 0,
            provider.replay_repair_calls == 0,
            provider.replay_other_calls == 0,
            not provider.replay_unclassified_jobs,
            not provider.replay_disallowed_dispositions,
            not provider.model_drift_axes,
            not provider.sampling_drift_axes,
            not provider.missing_reused_call_ids,
            not effects.violated,
            not effects.unproven,
            required_effects <= required_contract_effects,
            required_effects <= set(effects.checked_effects),
            required_effects <= set(effects.proven_absent),
            effects.target_readme_digest_first is not None,
            effects.target_readme_digest_first == effects.target_readme_digest_replay,
            effects.target_tree_digest_first is not None,
            effects.target_tree_digest_first == effects.target_tree_digest_replay,
            effects.target_revision_first == revision == effects.target_revision_replay,
            manifest.get("complete_transaction_replay_attestation_passed") is True,
            manifest.get("complete_transaction_replay_attestation_hash") == proof.proof_hash,
        )
    )


def replay_bound_rubric_evaluation(evaluation: dict, proof: CompleteTransactionNoOpProofV1) -> dict:
    """Return rubric evidence updated with the terminal replay result."""

    outcome_data = evaluation.get("outcome")
    if not isinstance(outcome_data, dict):
        raise ValueError("rubric evaluation has no typed outcome")
    try:
        outcome = RubricAcceptanceOutcome.model_validate(outcome_data)
    except ValidationError as exc:
        raise ValueError("rubric evaluation outcome is malformed") from exc
    replay_penalty = 1 if outcome.replay_attestation_proven is False else 0
    base_disqualifiers = max(0, outcome.hard_disqualifier_count - replay_penalty)
    updated = outcome.model_copy(
        update={
            "accepted": (
                outcome.score == 30
                and base_disqualifiers == 0
                and outcome.benchmark_acceptance_proven is True
                and proof.passed
            ),
            "hard_disqualifier_count": base_disqualifiers + (0 if proof.passed else 1),
            "replay_attestation_proven": proof.passed,
            "replay_attestation_hash": proof.proof_hash,
            "acceptance_contract_hash": portfolio_acceptance_contract_hash(),
        }
    )
    return {**evaluation, "outcome": updated.model_dump(mode="json")}


def rubric_acceptance_binding_current(bundle: EvidenceBundleV1) -> bool | None:
    """Ensure persisted rubric evidence contains the terminal benchmark and replay bindings."""

    evaluation = bundle.rubric_evaluation
    if (
        evaluation is None
        or bundle.benchmark_acceptance is None
        or bundle.replay_attestation is None
    ):
        return None
    outcome_data = evaluation.get("outcome")
    if not isinstance(outcome_data, dict):
        return False
    try:
        outcome = RubricAcceptanceOutcome.model_validate(outcome_data)
    except ValidationError:
        return False
    return all(
        (
            outcome.accepted,
            outcome.score == 30,
            outcome.hard_disqualifier_count == 0,
            outcome.benchmark_acceptance_proven is True,
            outcome.benchmark_acceptance_hash == bundle.benchmark_acceptance.canonical_hash(),
            outcome.replay_attestation_proven is True,
            outcome.replay_attestation_hash == bundle.replay_attestation.proof.proof_hash,
            outcome.acceptance_contract_hash == portfolio_acceptance_contract_hash(),
        )
    )


__all__ = [
    "benchmark_acceptance_proven",
    "portfolio_acceptance_contract_hash",
    "replay_attestation_contract_hash",
    "replay_attestation_proven",
    "replay_bound_rubric_evaluation",
    "rubric_acceptance_binding_current",
]
