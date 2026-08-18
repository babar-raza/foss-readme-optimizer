"""Detect drift between the pinned aspose.org import corpus and the live upstream tree.

Phase-3 machinery of the 2026-08-18 mission recovery. `data/imported/**` is the
optimizer's *owned*, hash-manifested copy of exactly the aspose.org inputs the
pipeline consumes (knowledge bundles, registries, keywords) -- runtime never
reads the aspose.org checkout. This tool is the sync model's DETECTION half:

- pins the aspose.org revision it compared against (HEAD + dirty flag);
- compares every imported member's recorded sha256 with the current upstream
  bytes;
- classifies each drifted member's SEMANTIC IMPACT (which optimizer concern
  its change can affect), so an update decision is made per concern rather
  than as a blind overwrite;
- writes a dated evidence report and NEVER writes into `data/imported/`.

The acceptance half (applying an update behind parity tests, preserving local
Qwen-specific adaptations) is a separate, deliberate step -- this report is
its required input, not its substitute.

Usage:
    .venv/Scripts/python scripts/data-refresh/detect_aspose_upstream_drift.py \
        [--aspose-root D:/onedrive/Documents/GitHub/aspose.org]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORTED_ROOT = REPO_ROOT / "data" / "imported"
EVIDENCE_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "aspose-upstream-drift"

# Which optimizer concern a drifted member can affect. Anything unlisted maps
# to "unclassified" and must be triaged by hand before any update is applied.
_SEMANTIC_IMPACT = {
    "api_surface.json": "facts.api_public_surface / API Reference parity",
    "api_surface.md": "facts.api_public_surface / API Reference parity",
    "formats.json": "format claims / diagram format evidence",
    "formats.md": "format claims / diagram format evidence",
    "claims.json": "dependency-claim corroboration",
    "limitations.md": "Scope and Limitations sourcing",
    "model.yaml": "knowledge pin (repo_sha) -- upstream re-promoted knowledge",
    "merge_report.md": "informational only",
    "aspose_com_targets.json": "Enterprise/backlink target selection",
    "diagram_archetypes.json": "At-a-Glance diagram archetype",
    "diagram_capability_dependencies.json": "At-a-Glance capability edges",
    "families.json": "family display names",
    "families_order.json": "family ordering",
    "api_reference_class_exclusions.json": "API Reference exclusions",
    "backlink_exceptions.json": "backlink policy",
    "package_registry.json": "install identity / registry publication truth",
    "format_descriptions.json": "format-name casing",
    "registry_exclusions.json": "registry admission",
    "products.json": "product roster",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(aspose_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(aspose_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _compare_bundle(manifest_path: Path, aspose_root: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    family = manifest.get("family")
    platform = manifest.get("platform")
    upstream_dir = aspose_root / "knowledge" / str(family) / str(platform) / "merged"
    members = {}
    drifted = 0
    missing = 0
    for member, meta in sorted(manifest.get("members", {}).items()):
        upstream_file = upstream_dir / member
        if not upstream_file.is_file():
            members[member] = {"state": "missing_upstream"}
            missing += 1
            continue
        current = _sha256(upstream_file)
        if current == meta.get("sha256"):
            state = "unchanged"
        else:
            state = "drifted"
            drifted += 1
        members[member] = {
            "state": state,
            "impact": _SEMANTIC_IMPACT.get(member, "unclassified"),
        }
    return {
        "family": family,
        "platform": platform,
        "pinned_repo_sha": manifest.get("repo_sha"),
        "drifted_members": drifted,
        "missing_upstream_members": missing,
        "members": {
            member: meta for member, meta in members.items() if meta["state"] != "unchanged"
        },
    }


def _compare_data_files(aspose_root: Path) -> list[dict]:
    rows = []
    imported_data = IMPORTED_ROOT / "data"
    if not imported_data.is_dir():
        return rows
    for path in sorted(imported_data.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(imported_data)
        upstream = aspose_root / "data" / relative
        if not upstream.is_file():
            rows.append({"file": str(relative), "state": "missing_upstream"})
            continue
        if _sha256(upstream) != _sha256(path):
            rows.append(
                {
                    "file": str(relative),
                    "state": "drifted",
                    "impact": _SEMANTIC_IMPACT.get(path.name, "unclassified"),
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aspose-root",
        default="D:/onedrive/Documents/GitHub/aspose.org",
        help="read-only aspose.org checkout to compare against",
    )
    args = parser.parse_args()
    aspose_root = Path(args.aspose_root)
    if not aspose_root.is_dir():
        print(f"error: aspose.org root not found: {aspose_root}")
        return 2

    bundles = [
        _compare_bundle(manifest_path, aspose_root)
        for manifest_path in sorted(IMPORTED_ROOT.glob("knowledge/*/*/merged/bundle_manifest.json"))
    ]
    data_rows = _compare_data_files(aspose_root)
    drifted_bundles = [
        row for row in bundles if row["drifted_members"] or row["missing_upstream_members"]
    ]
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "aspose_root": str(aspose_root),
        "upstream_head": _git(aspose_root, "rev-parse", "HEAD"),
        "upstream_dirty_paths": len(
            [line for line in _git(aspose_root, "status", "--porcelain").splitlines() if line]
        ),
        "bundle_count": len(bundles),
        "bundles_with_drift": len(drifted_bundles),
        "bundles": drifted_bundles,
        "data_file_drift": data_rows,
        "note": (
            "Detection only. Applying any update is a separate, deliberate step that must "
            "run the parity suites for every impacted concern and must never overwrite "
            "local Qwen-specific adaptations blindly."
        ),
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE_DIR / f"drift-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    out_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(
        f"upstream {report['upstream_head'][:12]} (dirty_paths={report['upstream_dirty_paths']}): "
        f"{report['bundles_with_drift']}/{report['bundle_count']} bundles drifted, "
        f"{len(data_rows)} data files drifted -> {out_path.relative_to(REPO_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
