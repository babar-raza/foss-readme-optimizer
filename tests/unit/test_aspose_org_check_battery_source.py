"""Tests for the committed-object Aspose.org acceptance-battery vendor boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def test_vendored_check_battery_matches_its_content_addressed_manifest() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / "data/imported/aspose_org_check_battery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert manifest["source_mode"] == "committed_git_objects"
    assert len(manifest["source_commit"]) == 40
    assert len(manifest["files"]) == 2

    aggregate_lines: list[str] = []
    for item in sorted(manifest["files"], key=lambda value: value["source_path"]):
        destination = root / item["destination_path"]
        assert destination.is_file()
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        assert digest == item["sha256"]
        aggregate_lines.append(f"{item['source_path']}:{digest}")

    aggregate = hashlib.sha256("\n".join(aggregate_lines).encode()).hexdigest()
    assert aggregate == manifest["aggregate_sha256"]
