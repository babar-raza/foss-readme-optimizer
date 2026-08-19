#!/usr/bin/env python3
"""Build the deterministic, checksum-complete manifest for the imported
aspose.org knowledge corpus (`data/imported/knowledge/`).

Every file under `data/imported/knowledge/` is content-hashed, sorted by
repository-relative path, and rolled into one aggregate corpus hash --
independent of the per-bundle `bundle_manifest.json` files the corpus
happens to carry (only 18 of 31 product bundles have one; every bundle has
`model.yaml`, so this manifest does not depend on the incomplete file).

This is what lets the runtime treat "the complete corpus" as one stable,
checksum-bound unit (`facts/acceptance_contract.py`'s `imported_knowledge`
component hashes this manifest file, not the raw corpus, so cache
invalidation stays a single cheap file read) while still selecting only a
small, bounded, relevant slice of claims per run
(`facts/aspose_knowledge_selection.py`).

Deliberately carries no wall-clock generation timestamp: the manifest is
hashed byte-for-byte as a cache-invalidation component
(`facts/acceptance_contract.py`), so two runs against unchanged corpus
content must produce byte-identical output. When this needs to be
regenerated on demand, `git log -1 --format=%cI -- data/imported/
knowledge_manifest.json` already answers "when was this last (really)
regenerated" without adding a field that would otherwise change on every
run regardless of content.

Run:

    .venv/Scripts/python scripts/data-refresh/build_imported_knowledge_manifest.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = REPO_ROOT / "data" / "imported" / "knowledge"
OUTPUT_PATH = REPO_ROOT / "data" / "imported" / "knowledge_manifest.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_provenance(bundle_dir: Path) -> dict:
    model_path = bundle_dir / "model.yaml"
    if not model_path.is_file():
        return {}
    import yaml

    try:
        raw = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        "repo_sha": raw.get("repo_sha"),
        "repo_url": raw.get("repo_url"),
        "product_name": raw.get("product_name"),
        "version": raw.get("version") or None,
        "promoted_at": raw.get("promoted_at") or None,
    }


def build_manifest() -> dict:
    if not KNOWLEDGE_ROOT.is_dir():
        raise SystemExit(f"knowledge root not found: {KNOWLEDGE_ROOT}")

    file_entries: list[dict] = []
    for path in sorted(KNOWLEDGE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        file_entries.append(
            {
                "path": relative,
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )

    aggregate = hashlib.sha256()
    for entry in file_entries:
        aggregate.update(entry["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(entry["sha256"].encode("ascii"))
        aggregate.update(b"\0")

    bundles: list[dict] = []
    for family_dir in sorted(p for p in KNOWLEDGE_ROOT.iterdir() if p.is_dir()):
        for platform_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
            merged_dir = platform_dir / "merged"
            if not merged_dir.is_dir():
                continue
            claims_path = merged_dir / "claims.json"
            claim_count = None
            if claims_path.is_file():
                try:
                    raw_claims = json.loads(claims_path.read_text(encoding="utf-8"))
                    claim_count = len(raw_claims) if isinstance(raw_claims, list) else None
                except (json.JSONDecodeError, OSError):
                    claim_count = None
            merged_prefix = merged_dir.relative_to(REPO_ROOT).as_posix()
            bundle_files = sorted(
                (entry for entry in file_entries if entry["path"].startswith(merged_prefix)),
                key=lambda entry: entry["path"],
            )
            bundle_digest = hashlib.sha256()
            for entry in bundle_files:
                bundle_digest.update(entry["path"].encode("utf-8"))
                bundle_digest.update(b"\0")
                bundle_digest.update(entry["sha256"].encode("ascii"))
                bundle_digest.update(b"\0")
            bundles.append(
                {
                    "family": family_dir.name,
                    "platform": platform_dir.name,
                    "claim_count": claim_count,
                    "file_count": len(bundle_files),
                    "bundle_sha256": bundle_digest.hexdigest(),
                    **_bundle_provenance(merged_dir),
                }
            )

    return {
        "schema_version": 1,
        "generator": "scripts/data-refresh/build_imported_knowledge_manifest.py",
        "knowledge_root": KNOWLEDGE_ROOT.relative_to(REPO_ROOT).as_posix(),
        "file_count": len(file_entries),
        "aggregate_sha256": aggregate.hexdigest(),
        "bundles": bundles,
        "files": file_entries,
    }


def main() -> None:
    manifest = build_manifest()
    OUTPUT_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()}: "
        f"{manifest['file_count']} files, {len(manifest['bundles'])} bundles, "
        f"aggregate_sha256={manifest['aggregate_sha256'][:16]}..."
    )


if __name__ == "__main__":
    main()
