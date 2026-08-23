"""Top-level orchestration for sealed transaction replay attestation.

The phase modules retain the original check and finding order while keeping this entry point a
small wiring seam.
"""

from __future__ import annotations

from pathlib import Path

from readme_agent.verification.sealed_transaction_replay_attestor_bundle import (
    _attest_bundle_evidence,
)
from readme_agent.verification.sealed_transaction_replay_attestor_effects import (
    _attest_provider_and_effects,
)
from readme_agent.verification.sealed_transaction_replay_attestor_findings import (
    _project_sealing_findings,
)
from readme_agent.verification.sealed_transaction_replay_attestor_state import _AttestationState
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import _canonical_contract_digest
from readme_agent.verification.sealed_transaction_replay_proof import (
    _empty_proof,
    _stamp_proof_hash,
)
from readme_agent.verification.sealed_transaction_replay_results import (
    CompleteTransactionNoOpProofV1,
)


def attest_complete_transaction_noop(
    *,
    first_bundle_root: Path,
    replay_bundle_root: Path,
    expected_contract: ReplayAttestationContractV1,
) -> CompleteTransactionNoOpProofV1:
    """Independently verify, from sealed evidence alone, that a replay was a true no-op."""

    state = _AttestationState()
    first_root_ok = first_bundle_root.is_dir() and not first_bundle_root.is_symlink()
    replay_root_ok = replay_bundle_root.is_dir() and not replay_bundle_root.is_symlink()
    state.record(
        "first_bundle_root_valid", first_root_ok, f"invalid first bundle root: {first_bundle_root}"
    )
    state.record(
        "replay_bundle_root_valid",
        replay_root_ok,
        f"invalid replay bundle root: {replay_bundle_root}",
    )
    distinct = (
        first_root_ok
        and replay_root_ok
        and first_bundle_root.resolve() != replay_bundle_root.resolve()
    )
    if first_root_ok and replay_root_ok:
        state.record(
            "distinct_bundle_roots", distinct, "first and replay bundle roots must be distinct"
        )
    if not (first_root_ok and replay_root_ok and distinct):
        return _empty_proof(
            expected_contract,
            checks=state.checks,
            failures=state.failures,
        )

    bundle = _attest_bundle_evidence(
        state,
        first_bundle_root,
        replay_bundle_root,
        expected_contract,
    )
    provider_delta, effect_delta = _attest_provider_and_effects(
        state,
        expected_contract,
        first_bundle_root,
        replay_bundle_root,
        bundle.first_parsed,
        bundle.replay_parsed,
        bundle.first_inventory,
        bundle.replay_inventory,
    )
    earliest, affected_stages = _project_sealing_findings(
        state,
        expected_contract,
        bundle.first_inventory,
        bundle.replay_inventory,
        bundle.artifact_delta,
    )
    passed = (
        not state.failures
        and all(state.checks.values())
        and provider_delta.accounting_certain
        and not effect_delta.unproven
        and not effect_delta.violated
    )
    proof = CompleteTransactionNoOpProofV1(
        contract_id=expected_contract.contract_id,
        org_repo=expected_contract.org_repo,
        expected_source_revision=expected_contract.expected_source_revision,
        contract_digest=_canonical_contract_digest(expected_contract),
        passed=passed,
        checks=state.checks,
        failures=tuple(state.failures),
        findings=tuple(state.findings),
        earliest_affected_stage=earliest,
        affected_stages=affected_stages,
        first_identity=bundle.first_identity,
        replay_identity=bundle.replay_identity,
        first_inventory=bundle.first_inventory,
        replay_inventory=bundle.replay_inventory,
        artifact_delta=bundle.artifact_delta,
        provider_delta=provider_delta,
        effect_delta=effect_delta,
        proof_hash="0" * 64,
    )
    return _stamp_proof_hash(proof)
