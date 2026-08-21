"""Verify the tracked owner-audit ingest without hiding line-ending normalization."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_ROOT = REPO_ROOT / "plans" / "investigations" / "owner_audit" / "execution-2026-08-20"
MANIFEST_PATH = AUDIT_ROOT / "MANIFEST.json"
SOURCE_ROOT = REPO_ROOT / "runs" / "owner_audit_staging"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalized_lf(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n")


def _source_path(item: dict[str, Any]) -> Path:
    relative = str(item["path"])
    lane = str(item["lane"])
    suffix = relative.split(f"/{lane}/", maxsplit=1)[1]
    return REPO_ROOT / str(item["source_staging_dir"]) / suffix


def restore_source_bytes() -> int:
    """Restore only manifest-bound source bytes after accidental formatter changes."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    restored = 0
    for item in manifest["files"]:
        source = _source_path(item)
        payload = source.read_bytes()
        if _sha256(payload) != item["sha256"]:
            raise ValueError(f"source evidence no longer matches manifest: {source}")
        destination = REPO_ROOT / item["path"]
        if destination.read_bytes() != payload:
            shutil.copyfile(source, destination)
            restored += 1
    return restored


def validate() -> dict[str, Any]:
    """Return a deterministic receipt or raise for any unexplained byte difference."""

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records = manifest.get("files")
    if not isinstance(records, list) or manifest.get("file_count") != len(records):
        raise ValueError("owner-audit manifest count does not match its file inventory")

    exact = 0
    normalized = 0
    observed_paths: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("owner-audit manifest contains a non-object file record")
        relative = item.get("path")
        expected = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError("owner-audit manifest file record is missing path or sha256")
        path = (REPO_ROOT / relative).resolve()
        if AUDIT_ROOT.resolve() not in path.parents:
            raise ValueError(f"owner-audit path escapes evidence root: {relative}")
        if relative in observed_paths:
            raise ValueError(f"duplicate owner-audit manifest path: {relative}")
        observed_paths.add(relative)
        if not path.is_file():
            raise ValueError(f"missing owner-audit evidence file: {relative}")
        payload = path.read_bytes()
        actual = _sha256(payload)
        if actual == expected:
            exact += 1
            continue
        # The ingest manifest records copied source bytes. Git's repository-wide eol=lf
        # policy may change CRLF text to LF. Accept only that exact, reversible transform.
        source = _source_path(item)
        source_payload = source.read_bytes() if source.is_file() else b""
        if (
            source_payload
            and _sha256(source_payload) == expected
            and _normalized_lf(source_payload) == payload
        ):
            normalized += 1
            continue
        raise ValueError(
            f"unexplained owner-audit byte mismatch: {relative} ({actual} != {expected})"
        )

    return {
        "schema_version": 1,
        "manifest": MANIFEST_PATH.relative_to(REPO_ROOT).as_posix(),
        "manifest_sha256": _sha256(MANIFEST_PATH.read_bytes()),
        "declared_files": len(records),
        "verified_exact": exact,
        "verified_lf_normalized": normalized,
        "unverified": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-source-bytes", action="store_true")
    args = parser.parse_args()
    try:
        if args.restore_source_bytes:
            print(f"restored_source_files: {restore_source_bytes()}")
        receipt = validate()
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
