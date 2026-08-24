"""Persist an independent complete-transaction replay attestation."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.supervisor.local_poc_replay_snapshots import (
    first_snapshot_path,
    materialize_transaction_snapshot,
)
from readme_agent.supervisor.local_poc_snapshot_evidence import write_local_poc_manifest
from readme_agent.supervisor.portfolio_proof_engine.rubric_evidence import (
    replay_bound_rubric_evaluation,
)
from readme_agent.verification.local_poc_replay_contract import (
    derive_local_poc_replay_contract,
)
from readme_agent.verification.sealed_transaction_replay import (
    CompleteTransactionNoOpProofV1,
    attest_complete_transaction_noop,
)


class ReplayGateError(RuntimeError):
    """The current candidate has no trustworthy first/replay transaction pair."""


def attest_and_persist_replay_gate(bundle_dir: Path) -> CompleteTransactionNoOpProofV1:
    """Seal the replay view, attest it independently, and bind the proof to the manifest."""

    first_root = first_snapshot_path(bundle_dir)
    if not first_root.is_dir():
        first_root = _recover_completed_first_snapshot(bundle_dir)
    replay_root = materialize_transaction_snapshot(bundle_dir, label="replay")
    contract = derive_local_poc_replay_contract(
        first_root=first_root,
        replay_root=replay_root,
    )
    proof = attest_complete_transaction_noop(
        first_bundle_root=first_root,
        replay_bundle_root=replay_root,
        expected_contract=contract,
    )
    review_dir = bundle_dir / "review"
    rubric_path = review_dir / "rubric-evaluation.json"
    try:
        rubric_evaluation = json.loads(rubric_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayGateError("replay requires a valid persisted rubric evaluation") from exc
    if not isinstance(rubric_evaluation, dict):
        raise ReplayGateError("persisted rubric evaluation is not a JSON object")
    try:
        replay_bound_rubric = replay_bound_rubric_evaluation(rubric_evaluation, proof)
    except ValueError as exc:
        raise ReplayGateError(str(exc)) from exc
    manifest_path = bundle_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayGateError("replay requires a valid local-POC manifest") from exc
    if not isinstance(manifest, dict):
        raise ReplayGateError("local-POC manifest is not a JSON object")
    completed = [str(item) for item in manifest.get("completed_stages", [])]
    if proof.passed and "COMPLETE_TRANSACTION_REPLAY_ATTESTED" not in completed:
        completed.append("COMPLETE_TRANSACTION_REPLAY_ATTESTED")
    manifest.update(
        {
            "complete_transaction_replay_attestation_hash": proof.proof_hash,
            "complete_transaction_replay_attestation_passed": proof.passed,
            "completed_stages": completed,
        }
    )
    write_redacted_json(
        review_dir / "complete-transaction-replay-contract.json",
        contract.model_dump(mode="json"),
    )
    write_redacted_json(
        review_dir / "complete-transaction-replay-attestation.json",
        {
            "attestation_type": "CompleteTransactionReplayAttestationV1",
            "first_bundle_root": str(first_root),
            "replay_bundle_root": str(replay_root),
            "proof": proof.model_dump(mode="json"),
        },
    )
    write_redacted_json(rubric_path, replay_bound_rubric)
    write_local_poc_manifest(bundle_dir, manifest)
    refresh_sha256sums(bundle_dir)
    return proof


def _recover_completed_first_snapshot(bundle_dir: Path) -> Path:
    """Recover a missing first view only from an already proven zero-call transaction."""

    manifest = _object(bundle_dir / "manifest.json", "manifest")
    no_op = _object(bundle_dir / "review" / "no-op-proof.json", "no-op proof")
    candidate_hash = manifest.get("candidate_hash")
    if not all(
        (
            manifest.get("lifecycle_status") == "NO_OP_PROVEN",
            no_op.get("verdict") == "NO_OP_PROVEN",
            isinstance(candidate_hash, str),
            no_op.get("candidate_hash") == candidate_hash,
            no_op.get("new_provider_call_count") == 0,
            no_op.get("patch_created") is False,
            no_op.get("duplicate_bundle_created") is False,
            isinstance(no_op.get("acceptance_binding"), dict),
        )
    ):
        raise ReplayGateError("the approved first transaction was not snapshotted before replay")
    write_redacted_json(
        bundle_dir / "review" / "first-transaction-snapshot-recovery.json",
        {
            "schema_version": 1,
            "recovery_basis": "checksum_complete_zero_call_no_op",
            "org_repo": manifest.get("org_repo"),
            "source_revision": manifest.get("source_revision"),
            "facts_hash": manifest.get("facts_hash"),
            "candidate_hash": candidate_hash,
            "candidate_stage_dependency_key": manifest.get("candidate_stage_dependency_key"),
        },
    )
    refresh_sha256sums(bundle_dir)
    return materialize_transaction_snapshot(bundle_dir, label="first")


def _object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayGateError(f"replay requires a valid {label}") from exc
    if not isinstance(value, dict):
        raise ReplayGateError(f"replay requires a valid {label}")
    return value


__all__ = ["ReplayGateError", "attest_and_persist_replay_gate"]
