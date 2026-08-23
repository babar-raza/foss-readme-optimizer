"""Sealing finding projection for replay attestation."""

from __future__ import annotations

from readme_agent.verification.sealed_transaction_replay_attestor_state import _AttestationState
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_proof import _earliest_affected_stage
from readme_agent.verification.sealed_transaction_replay_results import (
    ReplayArtifactDeltaV1,
    ReplayArtifactInventoryV1,
    ReplayDriftFindingV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import (
    STAGE_ORDER,
    ReplayStageV1,
)


def _project_sealing_findings(
    state: _AttestationState,
    expected_contract: ReplayAttestationContractV1,
    first_inventory: ReplayArtifactInventoryV1,
    replay_inventory: ReplayArtifactInventoryV1,
    artifact_delta: ReplayArtifactDeltaV1,
) -> tuple[ReplayStageV1 | None, tuple[ReplayStageV1, ...]]:
    for label, unsafe in (
        ("first", first_inventory.unsafe_paths),
        ("replay", replay_inventory.unsafe_paths),
    ):
        for path in unsafe:
            state.findings.append(
                ReplayDriftFindingV1(
                    code="escaping_symlink", stage="SEALING", detail=f"{label}: {path}"
                )
            )
    for label, missing in (
        ("first", first_inventory.missing_required),
        ("replay", replay_inventory.missing_required),
    ):
        for artifact_id in missing:
            state.findings.append(
                ReplayDriftFindingV1(
                    code=f"missing_required_artifact:{artifact_id}",
                    stage="SEALING",
                    detail=f"{label}: {artifact_id}",
                )
            )
    for label, undeclared in (
        ("first", first_inventory.undeclared_semantic_paths),
        ("replay", replay_inventory.undeclared_semantic_paths),
    ):
        for path in undeclared:
            state.findings.append(
                ReplayDriftFindingV1(
                    code=f"unexpected_semantic_artifact:{path}",
                    stage="SEALING",
                    detail=f"{label}: {path}",
                )
            )
    for label, dup in (
        ("first", first_inventory.duplicate_declared_paths),
        ("replay", replay_inventory.duplicate_declared_paths),
    ):
        for path in dup:
            state.findings.append(
                ReplayDriftFindingV1(
                    code="duplicate_declaration", stage="SEALING", detail=f"{label}: {path}"
                )
            )
    for path in artifact_delta.promised_byte_identity_failures:
        artifact = next(a for a in expected_contract.artifacts if a.artifact_id == path)
        state.findings.append(
            ReplayDriftFindingV1(
                code="artifact_hash_mismatch",
                stage=artifact.stage,
                detail=f"byte identity failed: {path}",
            )
        )
    for label, mismatches in (
        ("first", first_inventory.hash_declaration_mismatches),
        ("replay", replay_inventory.hash_declaration_mismatches),
    ):
        for path in mismatches:
            state.findings.append(
                ReplayDriftFindingV1(
                    code="artifact_hash_mismatch", stage="SEALING", detail=f"{label}: {path}"
                )
            )
    for label, invalid in (
        ("first", first_inventory.schema_invalid),
        ("replay", replay_inventory.schema_invalid),
    ):
        for artifact_id in invalid:
            state.findings.append(
                ReplayDriftFindingV1(
                    code="inventory_incomplete", stage="SEALING", detail=f"{label}: {artifact_id}"
                )
            )

    earliest = _earliest_affected_stage(tuple(state.findings))
    affected_stages = tuple(sorted({f.stage for f in state.findings}, key=STAGE_ORDER.__getitem__))
    state.record("no_drift_detected", not state.findings, f"{len(state.findings)} drift finding(s)")
    return earliest, affected_stages
