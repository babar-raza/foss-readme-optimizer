"""Bundle, identity, and artifact phases for sealed replay attestation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from readme_agent.verification.sealed_transaction_replay_artifacts import _build_artifact_delta
from readme_agent.verification.sealed_transaction_replay_attestor_state import _AttestationState
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_identity import _extract_identity
from readme_agent.verification.sealed_transaction_replay_inventory import _build_inventory
from readme_agent.verification.sealed_transaction_replay_paths import _walk_bundle
from readme_agent.verification.sealed_transaction_replay_results import (
    ReplayArtifactDeltaV1,
    ReplayArtifactInventoryV1,
    ReplayDriftFindingV1,
    SealedTransactionIdentityV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import _COMPONENT_STAGE


@dataclass(frozen=True)
class _BundleEvidence:
    first_inventory: ReplayArtifactInventoryV1
    replay_inventory: ReplayArtifactInventoryV1
    first_parsed: dict[str, Any]
    replay_parsed: dict[str, Any]
    first_identity: SealedTransactionIdentityV1
    replay_identity: SealedTransactionIdentityV1
    artifact_delta: ReplayArtifactDeltaV1


def _attest_bundle_evidence(
    state: _AttestationState,
    first_bundle_root: Path,
    replay_bundle_root: Path,
    expected_contract: ReplayAttestationContractV1,
) -> _BundleEvidence:
    first_inventory, first_parsed, _first_paths = _build_inventory(
        first_bundle_root, expected_contract, label="first", scopes=("both", "first_only")
    )
    replay_inventory, replay_parsed, _replay_paths = _build_inventory(
        replay_bundle_root, expected_contract, label="replay", scopes=("both", "replay_only")
    )
    state.record(
        "first_inventory_walkable",
        first_inventory.walk_error is None,
        str(first_inventory.walk_error),
    )
    state.record(
        "replay_inventory_walkable",
        replay_inventory.walk_error is None,
        str(replay_inventory.walk_error),
    )
    state.record(
        "inventory_bounds_respected",
        first_inventory.walk_error != "inventory_bounds_exceeded"
        and replay_inventory.walk_error != "inventory_bounds_exceeded",
    )
    state.record(
        "no_escaping_symlinks",
        not first_inventory.unsafe_paths and not replay_inventory.unsafe_paths,
        f"unsafe paths: first={first_inventory.unsafe_paths} "
        f"replay={replay_inventory.unsafe_paths}",
    )
    state.record(
        "no_duplicate_declared_paths",
        not first_inventory.duplicate_declared_paths
        and not replay_inventory.duplicate_declared_paths,
        "duplicate self-declared inventory path",
    )
    state.record(
        "required_artifacts_present",
        not first_inventory.missing_required and not replay_inventory.missing_required,
        f"missing required: first={first_inventory.missing_required} "
        f"replay={replay_inventory.missing_required}",
    )
    state.record(
        "artifact_hashes_recomputed",
        not first_inventory.hash_declaration_mismatches
        and not replay_inventory.hash_declaration_mismatches,
        "recomputed hash disagrees with bundle self-declaration",
    )
    state.record(
        "bundle_self_declarations_match",
        not first_inventory.orphan_inventory_paths and not replay_inventory.orphan_inventory_paths,
        "sha256sums.txt lists a file that no longer exists",
    )
    state.record(
        "inventory_covers_every_file",
        not first_inventory.uncovered_paths and not replay_inventory.uncovered_paths,
        "a file on disk is not covered by sha256sums.txt",
    )
    state.record(
        "no_undeclared_semantic_artifacts",
        not first_inventory.undeclared_semantic_paths
        and not replay_inventory.undeclared_semantic_paths,
        f"undeclared: first={first_inventory.undeclared_semantic_paths} "
        f"replay={replay_inventory.undeclared_semantic_paths}",
    )
    state.record(
        "artifact_schemas_valid",
        not first_inventory.schema_invalid and not replay_inventory.schema_invalid,
        f"schema invalid: first={first_inventory.schema_invalid} "
        f"replay={replay_inventory.schema_invalid}",
    )

    first_identity = _extract_identity(expected_contract, first_parsed, label="first")
    replay_identity = _extract_identity(expected_contract, replay_parsed, label="replay")
    state.record(
        "repository_identity_matches_contract",
        first_identity.org_repo == expected_contract.org_repo
        and replay_identity.org_repo == expected_contract.org_repo,
        "bundle org_repo does not match contract",
    )
    state.record(
        "source_revision_matches_contract",
        first_identity.source_revision == expected_contract.expected_source_revision
        and replay_identity.source_revision == expected_contract.expected_source_revision,
        "bundle source_revision does not match contract",
    )
    first_bad_identity = (
        first_identity.missing_required_components + first_identity.malformed_components
    )
    replay_bad_identity = (
        replay_identity.missing_required_components + replay_identity.malformed_components
    )
    state.record(
        "required_identity_components_resolved",
        not first_bad_identity and not replay_bad_identity,
        f"missing/malformed identity: first={first_bad_identity} replay={replay_bad_identity}",
    )

    for component in sorted(
        set(first_identity.component_digests) & set(replay_identity.component_digests)
    ):
        if (
            first_identity.component_digests[component]
            != replay_identity.component_digests[component]
        ):
            state.findings.append(
                ReplayDriftFindingV1(
                    code=f"identity_drift:{component}",
                    stage=_COMPONENT_STAGE[component],  # type: ignore[index]
                    detail=f"identity component drifted: {component}",
                )
            )
    state.record(
        "identity_components_match_across_bundles",
        not state.findings,
        "identity component drift detected",
    )

    first_walk = _walk_bundle(
        first_bundle_root,
        max_files=expected_contract.max_inventory_files,
        max_bytes=expected_contract.max_inventory_bytes,
    )
    replay_walk = _walk_bundle(
        replay_bundle_root,
        max_files=expected_contract.max_inventory_files,
        max_bytes=expected_contract.max_inventory_bytes,
    )
    artifact_delta = _build_artifact_delta(
        expected_contract,
        first_parsed,
        replay_parsed,
        first_inventory,
        replay_inventory,
        first_walk,
        replay_walk,
    )
    state.record(
        "promised_outputs_byte_identical",
        not artifact_delta.promised_byte_identity_failures,
        "promised byte-identical artifacts differ: "
        f"{artifact_delta.promised_byte_identity_failures}",
    )
    state.record(
        "non_promised_artifacts_semantically_identical",
        not artifact_delta.changed_artifact_ids,
        f"artifacts changed beyond allowed differences: {artifact_delta.changed_artifact_ids}",
    )
    for artifact_id in artifact_delta.changed_artifact_ids:
        artifact = next(a for a in expected_contract.artifacts if a.artifact_id == artifact_id)
        state.findings.append(
            ReplayDriftFindingV1(
                code="semantic_artifact_changed",
                stage=artifact.stage,
                detail=f"artifact changed: {artifact_id}",
            )
        )
    only_allowed = not artifact_delta.first_only_paths and not artifact_delta.replay_only_paths
    state.record(
        "only_allowed_differences_observed",
        only_allowed,
        f"unmatched file sets: first_only={artifact_delta.first_only_paths} "
        f"replay_only={artifact_delta.replay_only_paths}",
    )
    if not only_allowed:
        state.findings.append(
            ReplayDriftFindingV1(
                code="undeclared_difference", stage="SEALING", detail="bundle file sets differ"
            )
        )
    return _BundleEvidence(
        first_inventory=first_inventory,
        replay_inventory=replay_inventory,
        first_parsed=first_parsed,
        replay_parsed=replay_parsed,
        first_identity=first_identity,
        replay_identity=replay_identity,
        artifact_delta=artifact_delta,
    )
