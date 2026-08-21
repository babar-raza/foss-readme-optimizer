"""Preserve internally inconsistent product-truth bundles before recollection."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, sha256_file, write_redacted_json

_PRESERVED_DIRECTORIES = ("facts",)
_PRESERVED_FILES = ("manifest.json", "sha256sums.txt", "knowledge-application.json")


class InvalidProductTruthArchived(RuntimeError):
    """Signal that a preserved inconsistent cache must be recollected."""


def preserve_invalid_product_truth(
    bundle_dir: Path,
    manifest: dict,
    *,
    actual_facts_hash: str,
    actual_outcome: str,
    reason: str,
) -> Path:
    """Copy one checksum-valid but semantically inconsistent fact boundary once."""

    manifest_path = bundle_dir / "manifest.json"
    facts_path = bundle_dir / "facts" / "product-facts.json"
    identity_payload = json.dumps(
        {
            "manifest_sha256": sha256_file(manifest_path)[0],
            "facts_sha256": sha256_file(facts_path)[0],
            "actual_facts_hash": actual_facts_hash,
            "actual_outcome": actual_outcome,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    identity = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()
    destination = bundle_dir / "invalidated-product-truth" / identity[:16]
    record_path = destination / "invalid-product-truth.json"
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("identity") != identity:
            raise RuntimeError(f"invalid product-truth archive collision in {destination}")
        return destination

    destination.mkdir(parents=True, exist_ok=False)
    for name in _PRESERVED_DIRECTORIES:
        source = bundle_dir / name
        if source.is_dir():
            shutil.copytree(source, destination / name)
    for name in _PRESERVED_FILES:
        source = bundle_dir / name
        if source.is_file():
            shutil.copy2(source, destination / name)
    write_redacted_json(
        record_path,
        {
            "schema_version": 1,
            "identity": identity,
            "org_repo": manifest.get("org_repo"),
            "source_revision": manifest.get("source_revision"),
            "manifest_facts_hash": manifest.get("facts_hash"),
            "actual_facts_hash": actual_facts_hash,
            "manifest_outcome": manifest.get("lifecycle_status"),
            "actual_outcome": actual_outcome,
            "reason": reason,
        },
    )
    refresh_sha256sums(destination)
    return destination


__all__ = ["InvalidProductTruthArchived", "preserve_invalid_product_truth"]
