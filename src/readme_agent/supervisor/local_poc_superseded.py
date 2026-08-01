"""Preserve invalidated local README bundles as immutable superseded evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, sha256_file, write_redacted_json

_EVIDENCE_DIRECTORIES = ("facts", "assessment", "planning", "candidate", "review")
_DIRECTORY_HASH_LENGTH = 16


def preserve_superseded_candidate(
    bundle_dir: Path,
    prior_manifest: dict,
    *,
    reason: str,
) -> str | None:
    """Snapshot one displaced candidate and its evidence without inventing acceptance."""

    candidate_path = bundle_dir / "candidate" / "README.md"
    if not candidate_path.is_file():
        return None
    candidate_hash = sha256_file(candidate_path)[0]
    destination = bundle_dir / "superseded" / candidate_hash[:_DIRECTORY_HASH_LENGTH]
    preserved_candidate = destination / "candidate" / "README.md"
    if preserved_candidate.is_file():
        if sha256_file(preserved_candidate)[0] != candidate_hash:
            raise RuntimeError(f"superseded candidate hash collision in {destination}")
        record_path = destination / "superseded.json"
        if not record_path.is_file():
            raise RuntimeError(f"superseded candidate record is missing in {destination}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("candidate_hash") != candidate_hash:
            raise RuntimeError(f"superseded candidate identity collision in {destination}")
        return candidate_hash

    destination.mkdir(parents=True, exist_ok=False)
    for name in _EVIDENCE_DIRECTORIES:
        source = bundle_dir / name
        if source.is_dir():
            shutil.copytree(source, destination / name)
    for name in ("manifest.json", "sha256sums.txt"):
        source = bundle_dir / name
        if source.is_file():
            shutil.copy2(source, destination / name)
    manifest_candidate_hash = prior_manifest.get("candidate_hash")
    write_redacted_json(
        destination / "superseded.json",
        {
            "schema_version": 1,
            "candidate_hash": candidate_hash,
            "source_revision": prior_manifest.get("source_revision"),
            "prior_lifecycle_status": prior_manifest.get("lifecycle_status"),
            "prior_manifest_candidate_hash": manifest_candidate_hash,
            "candidate_binding": (
                "manifest_bound"
                if manifest_candidate_hash == candidate_hash
                else "retained_artifact_without_current_manifest_binding"
            ),
            "reason": reason,
        },
    )
    refresh_sha256sums(destination)
    return candidate_hash


def superseded_candidate_hashes(bundle_dir: Path) -> list[str]:
    """Return the deterministic set of preserved candidate identities."""

    root = bundle_dir / "superseded"
    if not root.is_dir():
        return []
    hashes: list[str] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        record_path = path / "superseded.json"
        if not record_path.is_file():
            raise RuntimeError(f"superseded candidate record is missing in {path}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        candidate_hash = record.get("candidate_hash")
        if not isinstance(candidate_hash, str) or len(candidate_hash) != 64:
            raise RuntimeError(f"superseded candidate identity is invalid in {path}")
        hashes.append(candidate_hash)
    return sorted(hashes)
