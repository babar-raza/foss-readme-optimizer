"""Own the canonical filesystem layout for finalized README promotion."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from readme_agent.evidence.file_inventory import enumerate_files, filesystem_path
from readme_agent.evidence.writer import verify_sha256sums

CANONICAL_ROOT_FILES = {"README.md", "cohort-manifest.json", "sha256sums.txt"}


def _new_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "manifest_type": "FinalizedVerifiedReadmeCohortManifestV1",
        "scope": "PARTIAL-VERIFIED-PORTFOLIO",
        "registry_path": "data/products.json",
        "effects": {
            "product_effects": 0,
            "default_branch_writes": 0,
            "pull_requests": 0,
        },
        "repositories": [],
        "promotion_exclusions": [],
    }


def _read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _reject_symlinks(root: Path) -> None:
    """Reject every link before inventory hashing or canonical-tree mutation."""

    def raise_walk_error(error: OSError) -> None:
        raise error

    physical_root = filesystem_path(root)
    for current_root, directories, filenames in os.walk(
        physical_root,
        topdown=True,
        onerror=raise_walk_error,
        followlinks=False,
    ):
        for name in [*directories, *filenames]:
            path = Path(current_root) / name
            if path.is_symlink():
                raise ValueError(f"unsupported symlink in finalized cohort: {path}")


def load_or_initialize_manifest(output_root: Path, *, repo_root: Path) -> dict[str, Any]:
    """Load a checksum-valid cohort, or initialize only a genuinely empty root."""

    if output_root.is_symlink() or (output_root.exists() and not output_root.is_dir()):
        raise ValueError(f"unsupported finalized cohort output root: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    _reject_symlinks(output_root)
    children = list(output_root.iterdir())
    if not children:
        (output_root / "repositories").mkdir()
        return _new_manifest()
    existing_files = {relative.as_posix() for relative, _path in enumerate_files(output_root)}
    missing_root_files = CANONICAL_ROOT_FILES - existing_files
    if missing_root_files or not verify_sha256sums(output_root):
        raise ValueError(
            "existing finalized cohort is unrecognized or checksum-invalid: "
            f"missing={sorted(missing_root_files)}"
        )
    manifest = _read_manifest(output_root / "cohort-manifest.json")
    prior_rows = [item for item in manifest.get("repositories", []) if isinstance(item, dict)]
    legacy_roots = {
        repository.replace("/", "__")
        for item in prior_rows
        if isinstance((repository := item.get("repository")), str)
    }
    allowed_roots = CANONICAL_ROOT_FILES | {"repositories"} | legacy_roots
    unrecognized_roots = sorted(
        child.name for child in output_root.iterdir() if child.name not in allowed_roots
    )
    if unrecognized_roots:
        raise ValueError(
            f"existing finalized cohort contains unrecognized root entries: {unrecognized_roots}"
        )
    repositories_root = output_root / "repositories"
    repositories_root.mkdir(exist_ok=True)
    validate_repository_artifact_set(prior_rows, output_root, repo_root=repo_root)
    return manifest


def _expected_repository_files(
    repositories: list[dict], output_root: Path, *, repo_root: Path
) -> set[Path]:
    expected: set[Path] = set()
    for item in repositories:
        values: list[object] = [item.get("committed_readme")]
        committed = item.get("committed_artifacts")
        if isinstance(committed, dict):
            values.extend(
                value[0]
                for value in committed.values()
                if isinstance(value, list) and len(value) == 2
            )
        for value in values:
            if not isinstance(value, str):
                raise ValueError(f"manifest repository artifact path is invalid: {value!r}")
            path = (repo_root / value).resolve()
            path.relative_to(output_root.resolve())
            expected.add(path)
    return expected


def validate_repository_artifact_set(
    repositories: list[dict], output_root: Path, *, repo_root: Path
) -> None:
    """Fail before mutation when the canonical tree differs from its manifest."""

    repositories_root = output_root / "repositories"
    _reject_symlinks(repositories_root)
    expected_files = _expected_repository_files(repositories, output_root, repo_root=repo_root)
    actual_files = {
        (repositories_root / relative).resolve()
        for relative, _physical in enumerate_files(repositories_root)
    }
    if actual_files != expected_files:
        unexpected = sorted(path.as_posix() for path in actual_files - expected_files)
        missing = sorted(path.as_posix() for path in expected_files - actual_files)
        raise ValueError(
            "canonical review tree contains unrecognized or missing artifacts: "
            f"unexpected={unexpected}; missing={missing}"
        )


def _empty_leaf_directories(repositories_root: Path) -> list[tuple[Path, Path]]:
    """Return fresh logical/physical pairs for empty leaves, including long Windows paths."""

    physical_root = filesystem_path(repositories_root)
    leaves: list[tuple[Path, Path]] = []
    pending = [physical_root]
    while pending:
        physical = pending.pop()
        entries = sorted(os.scandir(physical), key=lambda entry: entry.name.casefold())
        directories: list[Path] = []
        for entry in entries:
            entry_path = Path(entry.path)
            if entry.is_symlink():
                raise ValueError(f"unsupported symlink in canonical review tree: {entry_path}")
            if entry.is_dir(follow_symlinks=False):
                directories.append(entry_path)
        pending.extend(reversed(directories))
        if not entries and physical != physical_root:
            relative = physical.relative_to(physical_root)
            leaves.append((repositories_root / relative, physical))
    return leaves


def remove_obsolete_empty_directories(output_root: Path) -> None:
    """Remove empty managed descendants without deleting files or nonempty directories."""

    repositories_root = output_root / "repositories"
    _reject_symlinks(repositories_root)
    repositories_root.resolve().relative_to(output_root.resolve())
    while leaves := _empty_leaf_directories(repositories_root):
        for logical, physical in leaves:
            try:
                os.rmdir(physical)
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    f"canonical directory disappeared during cleanup: {logical}"
                ) from exc
