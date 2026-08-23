"""Materialize immutable first/replay views of one local-POC transaction."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from readme_agent.evidence.writer import refresh_sha256sums, verify_sha256sums

ReplaySnapshotLabel = Literal["first", "replay"]


class ReplaySnapshotError(RuntimeError):
    """A transaction snapshot is missing, corrupt, or bound to another candidate."""


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
    """Return the short candidate/reviewer-bound root for immutable transaction views."""

    manifest = _manifest(bundle_dir)
    candidate_hash = manifest.get("candidate_hash")
    reviewer_hash = manifest.get("reviewer_standard_hash")
    source_revision = manifest.get("source_revision")
    if not all(isinstance(item, str) and item for item in (candidate_hash, reviewer_hash)):
        raise ReplaySnapshotError("transaction snapshots require candidate and reviewer identities")
    if not isinstance(source_revision, str) or not source_revision:
        raise ReplaySnapshotError("transaction snapshot requires a source revision")
    assert isinstance(candidate_hash, str)
    assert isinstance(reviewer_hash, str)
    identity = hashlib.sha256(
        f"{source_revision}\0{candidate_hash}\0{reviewer_hash}".encode()
    ).hexdigest()
    # Keep the snapshot path comfortably below Windows MAX_PATH. Packet-cache filenames are
    # already 64-byte hashes, so descriptive parent names made an otherwise valid bundle
    # impossible to seal on default Windows installations.
    return bundle_dir.parent / "_tx" / identity[:16]


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
    for key in ("org_repo", "source_revision", "candidate_hash", "reviewer_standard_hash"):
        if actual.get(key) != expected_manifest.get(key):
            raise ReplaySnapshotError(f"existing transaction snapshot has stale {key}: {path}")
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
        shutil.copytree(bundle_dir, temporary, ignore=_copy_filter)
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
