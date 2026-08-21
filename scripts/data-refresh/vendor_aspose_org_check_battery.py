#!/usr/bin/env python3
"""Vendor the qualified README acceptance battery from a committed Aspose.org revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORED_ROOT = REPO_ROOT / "src/readme_agent/vendored_asposeorg"
MANIFEST_PATH = REPO_ROOT / "data/imported/aspose_org_check_battery_manifest.json"
SOURCE_PATHS = (
    "scripts/pipeline/commands/foss/readme_refresh_checks.py",
    "scripts/pipeline/lib/api_table_dupes.py",
)


def _git(repository: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(detail or f"git {' '.join(args)} failed")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repository", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()

    source_repository = args.source_repository.resolve()
    source_commit = (
        _git(source_repository, "rev-parse", f"{args.source_revision}^{{commit}}")
        .decode("ascii")
        .strip()
    )
    if _git(source_repository, "status", "--porcelain"):
        print("source worktree is dirty; reading committed objects only")

    files: list[dict[str, str]] = []
    for source_path in SOURCE_PATHS:
        blob = _git(source_repository, "show", f"{source_commit}:{source_path}")
        destination = VENDORED_ROOT / source_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(blob)
        files.append(
            {
                "source_path": source_path,
                "destination_path": destination.relative_to(REPO_ROOT).as_posix(),
                "sha256": hashlib.sha256(blob).hexdigest(),
            }
        )

    aggregate_payload = "\n".join(
        f"{item['source_path']}:{item['sha256']}"
        for item in sorted(files, key=lambda x: x["source_path"])
    ).encode()
    manifest = {
        "schema_version": 1,
        "source_repository": str(source_repository),
        "source_commit": source_commit,
        "source_mode": "committed_git_objects",
        "aggregate_sha256": hashlib.sha256(aggregate_payload).hexdigest(),
        "files": files,
        "qualification": (
            "Upstream checks are imported as evidence-bearing candidates. Local classification, "
            "fixtures, and bridge support decide whether each check is blocking, diagnostic, "
            "adaptation-required, or not applicable. Upstream controller state is never imported."
        ),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"vendored {len(files)} files from {source_commit}; "
        f"aggregate={manifest['aggregate_sha256']}"
    )


if __name__ == "__main__":
    main()
