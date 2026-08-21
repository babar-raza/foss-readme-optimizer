"""Tests for the self-contained deterministic Aspose.org generator import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.facts import aspose_org_vendored_source as source_module


def test_committed_vendored_source_inventory_validates_without_sibling_checkout() -> None:
    source = source_module.load_vendored_aspose_org_source()

    assert source.source_commit == "92f213302a15797bc0bce1b8f34e45f11db02acc"
    assert len(source.files) == 16
    assert source.pipeline.joinpath("extraction/scout.py").is_file()
    assert source.pipeline.joinpath("scout_enrichers/_javadoc.py").is_file()


def test_vendored_source_rejects_changed_bytes(tmp_path: Path, monkeypatch) -> None:
    repository = tmp_path
    vendored = repository / "src/readme_agent/vendored_asposeorg"
    extraction = vendored / "scripts/pipeline/extraction"
    extraction.mkdir(parents=True)
    (extraction / "scout.py").write_text("changed", encoding="utf-8")
    manifest = repository / "data/imported/aspose_org_knowledge_generator_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source_commit": "a" * 40,
                "aggregate_sha256": "b" * 64,
                "files": {
                    "scripts/pipeline/extraction/scout.py": {
                        "destination": "scout.py",
                        "git_blob": "c" * 40,
                        "sha256": "d" * 64,
                        "bytes": 7,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    fake_module = repository / "src/readme_agent/facts/aspose_org_vendored_source.py"
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("", encoding="utf-8")
    monkeypatch.setattr(source_module, "__file__", str(fake_module))

    with pytest.raises(ValueError, match="byte mismatch"):
        source_module.load_vendored_aspose_org_source()
