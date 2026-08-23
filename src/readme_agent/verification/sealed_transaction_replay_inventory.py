"""Declared artifact inventory construction for replay attestation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from readme_agent.evidence.writer import sha256_file
from readme_agent.llm.call_ledger import load_llm_call_records
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import (
    _mode_digest,
    canonical_json_sha256,
)
from readme_agent.verification.sealed_transaction_replay_paths import (
    _is_non_semantic,
    _parse_sha256sums,
    _resolve_declared_path,
    _under_lifecycle_directory,
    _walk_bundle,
)
from readme_agent.verification.sealed_transaction_replay_results import (
    ReplayArtifactInventoryV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import BundleScopeV1


def _build_inventory(
    root: Path,
    contract: ReplayAttestationContractV1,
    *,
    label: Literal["first", "replay"],
    scopes: tuple[BundleScopeV1, ...],
) -> tuple[ReplayArtifactInventoryV1, dict[str, Any], dict[str, str]]:
    walk = _walk_bundle(
        root, max_files=contract.max_inventory_files, max_bytes=contract.max_inventory_bytes
    )
    on_disk = set(walk.regular_files)

    declared = [artifact for artifact in contract.artifacts if artifact.scope in scopes]
    missing_required: list[str] = []
    missing_optional: list[str] = []
    unsafe_paths = list(walk.unsafe_paths)
    mode_digests: dict[str, str] = {}
    raw_digests: dict[str, str] = {}
    sizes: dict[str, int] = {}
    schema_invalid: list[str] = []
    parsed_by_id: dict[str, Any] = {}
    path_by_id: dict[str, str] = {}

    if walk.walk_error is not None:
        inventory = ReplayArtifactInventoryV1(
            bundle_label=label,
            declared_count=len(declared),
            present_count=0,
            file_count=walk.file_count,
            total_bytes=walk.total_bytes,
            missing_required=tuple(a.artifact_id for a in declared if a.level == "REQUIRED"),
            walk_error=walk.walk_error,
            inventory_digest=canonical_json_sha256({"walk_error": walk.walk_error}),
        )
        return inventory, {}, {}

    for artifact in declared:
        resolved = _resolve_declared_path(root, artifact.relative_path)
        if resolved is None:
            if artifact.relative_path in on_disk:
                unsafe_paths.append(artifact.relative_path)
            if artifact.level == "REQUIRED":
                missing_required.append(artifact.artifact_id)
            elif artifact.level == "OPTIONAL":
                missing_optional.append(artifact.artifact_id)
            continue
        try:
            data = resolved.read_bytes()
        except OSError:
            if artifact.level == "REQUIRED":
                missing_required.append(artifact.artifact_id)
            continue
        effective_cap = min(artifact.max_bytes, contract.max_artifact_bytes)
        if len(data) > effective_cap:
            unsafe_paths.append(artifact.relative_path)
            if artifact.level == "REQUIRED":
                missing_required.append(artifact.artifact_id)
            continue

        parsed: Any = None
        valid = True
        if artifact.kind == "json_object":
            try:
                parsed = json.loads(data.decode("utf-8"))
                valid = isinstance(parsed, dict)
            except (json.JSONDecodeError, UnicodeDecodeError):
                valid = False
        elif artifact.kind == "json_array":
            try:
                parsed = json.loads(data.decode("utf-8"))
                valid = isinstance(parsed, list)
            except (json.JSONDecodeError, UnicodeDecodeError):
                valid = False
        elif artifact.kind == "jsonl_llm_ledger":
            if not resolved.is_file():
                valid = False
            else:
                try:
                    parsed = load_llm_call_records(resolved)
                except (RuntimeError, ValueError, OSError, UnicodeError):
                    valid = False

        if not valid:
            schema_invalid.append(artifact.artifact_id)
            continue

        # Raw byte digests are only meaningful (and stored) for hash modes where byte identity is
        # the actual semantic identity. A canonical_json_sha256 artifact's raw bytes are, by
        # design, allowed to reformat/reorder without changing its identity -- storing a raw
        # digest for it would make the proof (and proof_hash) sensitive to formatting noise that
        # requirement 8 ("stable output ordering/hash") explicitly says must not matter.
        if artifact.hash_mode != "canonical_json_sha256":
            raw_digests[artifact.artifact_id] = sha256_hex(data)
        mode_digests[artifact.artifact_id] = _mode_digest(
            resolved, data, artifact.hash_mode, parsed
        )
        sizes[artifact.artifact_id] = len(data)
        parsed_by_id[artifact.artifact_id] = parsed
        path_by_id[artifact.artifact_id] = artifact.relative_path

    inventory_entries, duplicate_declared_paths = _parse_sha256sums(root / "sha256sums.txt")
    uncovered_paths: list[str] = []
    orphan_inventory_paths: list[str] = []
    hash_declaration_mismatches: list[str] = []
    if inventory_entries or (root / "sha256sums.txt").is_file():
        covered = set(inventory_entries)
        uncovered_paths = sorted((on_disk - {"sha256sums.txt"}) - covered)
        orphan_inventory_paths = sorted(covered - on_disk)
        for relpath, expected_digest in inventory_entries.items():
            candidate = root / relpath
            resolved_candidate = (
                _resolve_declared_path(root, relpath) if "/" in relpath or relpath else None
            )
            target = (
                resolved_candidate
                if resolved_candidate is not None
                else (candidate if candidate.is_file() else None)
            )
            if target is None:
                continue
            try:
                actual_digest, _ = sha256_file(target)
            except OSError:
                continue
            if actual_digest != expected_digest:
                hash_declaration_mismatches.append(relpath)

    lifecycle_effect_children: dict[str, tuple[str, ...]] = {}
    undeclared_semantic_paths: list[str] = []
    declared_paths = {artifact.relative_path for artifact in declared}
    for relpath in walk.regular_files:
        lifecycle_dir = _under_lifecycle_directory(relpath, contract.lifecycle_effect_directories)
        if lifecycle_dir is not None:
            children = lifecycle_effect_children.setdefault(lifecycle_dir, ())
            remainder = relpath[len(lifecycle_dir) + 1 :]
            child = remainder.split("/", 1)[0]
            if child not in children:
                lifecycle_effect_children[lifecycle_dir] = tuple(sorted({*children, child}))
            continue
        if relpath in declared_paths:
            continue
        if _is_non_semantic(
            relpath,
            non_semantic_paths=frozenset(contract.non_semantic_paths),
            non_semantic_basenames=frozenset(contract.non_semantic_basenames),
            non_semantic_suffixes=frozenset(contract.non_semantic_suffixes),
            non_semantic_directories=frozenset(contract.non_semantic_directories),
        ):
            continue
        undeclared_semantic_paths.append(relpath)

    inventory = ReplayArtifactInventoryV1(
        bundle_label=label,
        declared_count=len(declared),
        present_count=len(mode_digests),
        file_count=walk.file_count,
        total_bytes=walk.total_bytes,
        mode_digests=mode_digests,
        raw_digests=raw_digests,
        sizes=sizes,
        missing_required=tuple(sorted(set(missing_required))),
        missing_optional=tuple(sorted(set(missing_optional))),
        unsafe_paths=tuple(sorted(set(unsafe_paths))),
        duplicate_declared_paths=tuple(duplicate_declared_paths),
        hash_declaration_mismatches=tuple(sorted(set(hash_declaration_mismatches))),
        undeclared_semantic_paths=tuple(sorted(set(undeclared_semantic_paths))),
        uncovered_paths=tuple(uncovered_paths),
        orphan_inventory_paths=tuple(orphan_inventory_paths),
        schema_invalid=tuple(sorted(set(schema_invalid))),
        lifecycle_effect_children=lifecycle_effect_children,
        walk_error=None,
        inventory_digest=canonical_json_sha256(
            {
                "mode": sorted(mode_digests.items()),
                "raw": sorted(raw_digests.items()),
                "undeclared": sorted(set(undeclared_semantic_paths)),
                "lifecycle": sorted(lifecycle_effect_children.items()),
            }
        ),
    )
    return inventory, parsed_by_id, path_by_id
