"""Final proof construction and hashing for sealed transaction replay attestation."""

from __future__ import annotations

from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import (
    _canonical_contract_digest,
    canonical_json_sha256,
)
from readme_agent.verification.sealed_transaction_replay_results import (
    CompleteTransactionNoOpProofV1,
    ProductEffectDeltaV1,
    ProviderLedgerDeltaV1,
    ReplayArtifactDeltaV1,
    ReplayArtifactInventoryV1,
    ReplayDriftFindingV1,
    SealedTransactionIdentityV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    STAGE_ORDER,
    ReplayStageV1,
)


def _earliest_affected_stage(findings: tuple[ReplayDriftFindingV1, ...]) -> ReplayStageV1 | None:
    if not findings:
        return None
    return min((finding.stage for finding in findings), key=STAGE_ORDER.__getitem__)


def _empty_proof(
    contract: ReplayAttestationContractV1, *, checks: dict[str, bool], failures: list[str]
) -> CompleteTransactionNoOpProofV1:
    empty_identity_first = SealedTransactionIdentityV1(
        bundle_label="first", identity_digest=canonical_json_sha256({})
    )
    empty_identity_replay = SealedTransactionIdentityV1(
        bundle_label="replay", identity_digest=canonical_json_sha256({})
    )
    empty_inventory_first = ReplayArtifactInventoryV1(
        bundle_label="first",
        declared_count=len(contract.artifacts),
        present_count=0,
        file_count=0,
        total_bytes=0,
        walk_error="bundle_root_invalid",
        inventory_digest=canonical_json_sha256({"walk_error": "bundle_root_invalid"}),
    )
    empty_inventory_replay = empty_inventory_first.model_copy(update={"bundle_label": "replay"})
    empty_delta = ReplayArtifactDeltaV1(delta_digest=canonical_json_sha256({}))
    empty_provider = ProviderLedgerDeltaV1(
        ledger_load_error="bundle_root_invalid",
        accounting_certain=False,
        delta_digest=canonical_json_sha256({"error": "bundle_root_invalid"}),
    )
    empty_effect = ProductEffectDeltaV1(delta_digest=canonical_json_sha256({}))
    finding = ReplayDriftFindingV1(code="bundle_root_invalid", stage="SEALING", detail="")
    proof = CompleteTransactionNoOpProofV1(
        contract_id=contract.contract_id,
        org_repo=contract.org_repo,
        expected_source_revision=contract.expected_source_revision,
        contract_digest=_canonical_contract_digest(contract),
        passed=False,
        checks=checks,
        failures=tuple(failures),
        findings=(finding,),
        earliest_affected_stage="SEALING",
        affected_stages=("SEALING",),
        first_identity=empty_identity_first,
        replay_identity=empty_identity_replay,
        first_inventory=empty_inventory_first,
        replay_inventory=empty_inventory_replay,
        artifact_delta=empty_delta,
        provider_delta=empty_provider,
        effect_delta=empty_effect,
        proof_hash="0" * 64,
    )
    return _stamp_proof_hash(proof)


def _stamp_proof_hash(proof: CompleteTransactionNoOpProofV1) -> CompleteTransactionNoOpProofV1:
    payload = proof.model_dump(mode="json")
    payload.pop("proof_hash", None)
    return proof.model_copy(update={"proof_hash": canonical_json_sha256(payload)})


def canonical_proof_hash(proof: CompleteTransactionNoOpProofV1) -> str:
    payload = proof.model_dump(mode="json")
    payload.pop("proof_hash", None)
    return canonical_json_sha256(payload)
