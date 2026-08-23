"""Artifact delta construction for sealed transaction replay attestation."""

from __future__ import annotations

from typing import Any

from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import (
    _diff_allowed_pointers,
    _project_semantic,
    canonical_json_sha256,
)
from readme_agent.verification.sealed_transaction_replay_paths import _is_non_semantic, _WalkResult
from readme_agent.verification.sealed_transaction_replay_results import (
    ReplayArtifactDeltaV1,
    ReplayArtifactInventoryV1,
)


def _build_artifact_delta(
    contract: ReplayAttestationContractV1,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
    first_inventory: ReplayArtifactInventoryV1,
    replay_inventory: ReplayArtifactInventoryV1,
    first_walk: _WalkResult,
    replay_walk: _WalkResult,
) -> ReplayArtifactDeltaV1:
    both_artifacts = [
        artifact
        for artifact in contract.artifacts
        if artifact.scope == "both" and artifact.compare_for_delta
    ]
    compared: list[str] = []
    byte_identical: list[str] = []
    semantically_identical: list[str] = []
    changed: list[str] = []
    missing_in_first: list[str] = []
    missing_in_replay: list[str] = []
    allowed_diffs: list[str] = []
    promised_failures: list[str] = []

    def _comparison_digest(inventory: ReplayArtifactInventoryV1, artifact_id: str) -> str | None:
        # raw_digests is the byte-identity signal; for canonical_json_sha256 artifacts (which are
        # deliberately reorder/formatting-invariant) it is never populated, so the canonical
        # mode_digest -- itself already order-independent -- is the correct identity surrogate.
        return inventory.raw_digests.get(artifact_id) or inventory.mode_digests.get(artifact_id)

    for artifact in both_artifacts:
        artifact_id = artifact.artifact_id
        in_first = artifact_id in first_inventory.mode_digests
        in_replay = artifact_id in replay_inventory.mode_digests
        if not in_first and not in_replay:
            continue
        if not in_first:
            missing_in_first.append(artifact_id)
            continue
        if not in_replay:
            missing_in_replay.append(artifact_id)
            continue
        compared.append(artifact_id)
        raw_equal = _comparison_digest(first_inventory, artifact_id) == _comparison_digest(
            replay_inventory, artifact_id
        )
        if artifact_id in contract.output_equivalence_artifact_ids:
            if not raw_equal:
                promised_failures.append(artifact_id)
                changed.append(artifact_id)
            else:
                byte_identical.append(artifact_id)
            continue
        if raw_equal:
            byte_identical.append(artifact_id)
            continue
        if artifact.kind in ("json_object", "json_array"):
            first_doc = first_parsed.get(artifact_id)
            replay_doc = replay_parsed.get(artifact_id)
            first_projection = _project_semantic(first_doc)
            replay_projection = _project_semantic(replay_doc)
            if canonical_json_sha256(first_projection) == canonical_json_sha256(replay_projection):
                semantically_identical.append(artifact_id)
                allowed_diffs.extend(
                    f"{artifact_id}#{pointer}"
                    for pointer in _diff_allowed_pointers(first_doc, replay_doc)
                )
            else:
                changed.append(artifact_id)
        else:
            changed.append(artifact_id)

    # Any declared artifact's presence/absence is already governed precisely by its own
    # level (REQUIRED/OPTIONAL/NOT_APPLICABLE) via missing_required/missing_optional -- the raw
    # file-set diff below exists only to catch UNDECLARED files appearing asymmetrically, so every
    # declared path (any scope, any level) is exempt from it regardless of which side it's on.
    declared_paths = {a.relative_path for a in contract.artifacts}
    non_semantic_kwargs = {
        "non_semantic_paths": frozenset(contract.non_semantic_paths),
        "non_semantic_basenames": frozenset(contract.non_semantic_basenames),
        "non_semantic_suffixes": frozenset(contract.non_semantic_suffixes),
        "non_semantic_directories": frozenset(contract.non_semantic_directories),
    }
    first_only_paths = sorted(
        path
        for path in set(first_walk.regular_files) - set(replay_walk.regular_files) - declared_paths
        if not _is_non_semantic(path, **non_semantic_kwargs)
    )
    replay_only_paths = sorted(
        path
        for path in set(replay_walk.regular_files) - set(first_walk.regular_files) - declared_paths
        if not _is_non_semantic(path, **non_semantic_kwargs)
    )

    return ReplayArtifactDeltaV1(
        compared_artifact_ids=tuple(sorted(compared)),
        byte_identical_artifact_ids=tuple(sorted(byte_identical)),
        semantically_identical_artifact_ids=tuple(sorted(semantically_identical)),
        changed_artifact_ids=tuple(sorted(changed)),
        missing_in_first=tuple(sorted(missing_in_first)),
        missing_in_replay=tuple(sorted(missing_in_replay)),
        first_only_paths=tuple(first_only_paths),
        replay_only_paths=tuple(replay_only_paths),
        allowed_differences_observed=tuple(sorted(set(allowed_diffs))),
        promised_byte_identity_failures=tuple(sorted(promised_failures)),
        delta_digest=canonical_json_sha256(
            {
                "changed": sorted(changed),
                "missing_first": sorted(missing_in_first),
                "missing_replay": sorted(missing_in_replay),
                "promised_failures": sorted(promised_failures),
            }
        ),
    )
