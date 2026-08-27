"""Materialize immutable first/replay views of one local-POC transaction."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums, win_long_path

ReplaySnapshotLabel = Literal["first", "replay"]


class ReplaySnapshotError(RuntimeError):
    """A transaction snapshot is missing, corrupt, or bound to another candidate."""


def _long_path(path: Path | str) -> str | Path:
    """`path`, prefixed for Win32 MAX_PATH safety when running on Windows.

    `bundle_dir` (the copy source below) is `<repo>/<40-char revision>/`, already
    measured beyond 260 characters for a real repository name in this same evidence
    tree (`local_poc_review_cache_preservation.py::_long_path` documents the identical
    shape) -- `temporary`/`target` are deliberately kept short (`_tx/<16-hex>/...`,
    see `transaction_snapshot_root()`), so only the `bundle_dir` side of the copy
    below needs this.
    """

    return win_long_path(path) if os.name == "nt" else path


def _manifest(bundle_dir: Path) -> dict:
    path = bundle_dir / "manifest.json"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplaySnapshotError(f"transaction manifest is unreadable: {path}") from exc
    if not isinstance(loaded, dict):
        raise ReplaySnapshotError(f"transaction manifest is not an object: {path}")
    return loaded


def transaction_snapshot_root(bundle_dir: Path) -> Path:
    """Return the short complete-transaction-bound root for immutable transaction views."""

    manifest = _manifest(bundle_dir)
    identity = hashlib.sha256(
        json.dumps(
            _transaction_identity(manifest),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    # Keep the snapshot path comfortably below Windows MAX_PATH. Packet-cache filenames are
    # already 64-byte hashes, so descriptive parent names made an otherwise valid bundle
    # impossible to seal on default Windows installations.
    return bundle_dir.parent / "_tx" / identity[:16]


def _transaction_identity(manifest: dict) -> dict:
    """Bind snapshots to every dependency that may change a sealed transaction."""

    required = (
        "org_repo",
        "source_revision",
        "facts_hash",
        "fact_acceptance_contract_hash",
        "candidate_hash",
        "candidate_stage_dependency_key",
        "prompt_registry_content_hash",
        "deterministic_validation_hash",
        "reviewer_standard_hash",
    )
    missing = [
        key for key in required if not isinstance(manifest.get(key), str) or not manifest[key]
    ]
    prompt_dependencies = manifest.get("prompt_dependency_hashes")
    if not isinstance(prompt_dependencies, dict):
        missing.append("prompt_dependency_hashes")
    if missing:
        raise ReplaySnapshotError(
            "transaction snapshot is missing complete identity: " + ", ".join(sorted(missing))
        )
    return {
        **{key: manifest[key] for key in required},
        "prompt_dependency_hashes": prompt_dependencies,
    }


def first_snapshot_path(bundle_dir: Path) -> Path:
    return transaction_snapshot_root(bundle_dir) / "f"


def replay_snapshot_path(bundle_dir: Path) -> Path:
    manifest = _manifest(bundle_dir)
    acceptance_hash = manifest.get("benchmark_acceptance_hash")
    if not isinstance(acceptance_hash, str) or len(acceptance_hash) != 64:
        raise ReplaySnapshotError("replay snapshot requires benchmark-acceptance identity")
    return transaction_snapshot_root(bundle_dir) / f"r-{acceptance_hash[:8]}"


def _copy_filter(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in {"superseded", "sha256sums.txt"}}


def _verify_existing(path: Path, expected_manifest: dict) -> Path:
    if not verify_sha256sums(path):
        raise ReplaySnapshotError(
            f"existing transaction snapshot fails checksum validation: {path}"
        )
    actual = _manifest(path)
    if _transaction_identity(actual) != _transaction_identity(expected_manifest):
        raise ReplaySnapshotError(f"existing transaction snapshot has stale identity: {path}")
    return path


def materialize_transaction_snapshot(
    bundle_dir: Path,
    *,
    label: ReplaySnapshotLabel,
) -> Path:
    """Copy the current transaction once; never overwrite an existing sealed view."""

    expected = _manifest(bundle_dir)
    target = (
        first_snapshot_path(bundle_dir) if label == "first" else replay_snapshot_path(bundle_dir)
    )
    if target.exists():
        return _verify_existing(target, expected)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="~", dir=target.parent.parent))
    try:
        shutil.rmtree(temporary)
        # `temporary` (`_tx/<16-hex>/~xxxxxxxx`) was kept short by design (see
        # `transaction_snapshot_root()`), but it still nests under the same long
        # `<repo>/<40-char revision>/`-adjacent parent as `bundle_dir` -- a deep child
        # entry copied into it (e.g. `review/bounded-packet-cache/<64-hex>.json`) can
        # still cross 260 characters, so the destination needs the same prefixing as
        # the source.
        shutil.copytree(_long_path(bundle_dir), _long_path(temporary), ignore=_copy_filter)
        refresh_sha256sums(temporary)
        if not verify_sha256sums(temporary):
            raise ReplaySnapshotError("new transaction snapshot failed checksum validation")
        os.replace(temporary, target)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    return _verify_existing(target, expected)


__all__ = [
    "ReplaySnapshotError",
    "first_snapshot_path",
    "materialize_transaction_snapshot",
    "replay_snapshot_path",
    "transaction_snapshot_root",
]
