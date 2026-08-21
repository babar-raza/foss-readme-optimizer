"""Tests for deterministic presentation-knowledge import."""

import importlib.util
import json
from pathlib import Path

import pytest


def _module():
    path = Path("scripts/data-refresh/import_presentation_knowledge.py").resolve()
    spec = importlib.util.spec_from_file_location("import_presentation_knowledge", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_ledger(root: Path) -> None:
    path = root / "widget" / "java" / "content-dispositions.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            [
                {
                    "unit_id": "u1",
                    "excerpt": "- Create widgets with `Widget.open()`.",
                    "salient_tokens": ["Widget", "open"],
                    "target_section": "Key Capabilities",
                    "verification": {
                        "status": "verified_against_source",
                        "evidence_type": "clone_cache_path",
                        "evidence_ref": "src/Widget.java",
                    },
                },
                {
                    "unit_id": "u2",
                    "excerpt": "Ignored circular statement.",
                    "salient_tokens": ["Widget"],
                    "target_section": "Key Capabilities",
                    "verification": {
                        "status": "verified_against_source",
                        "evidence_type": "candidate_section_reference",
                        "evidence_ref": "Key Capabilities",
                    },
                },
            ]
        ),
        encoding="utf-8",
    )


def test_build_catalog_keeps_only_source_cited_hints(tmp_path: Path, monkeypatch):
    module = _module()
    source = tmp_path / "reports"
    _write_ledger(source)
    registry = tmp_path / "products.json"
    registry.write_text(json.dumps([{"family": "widget", "platform": "java"}]), encoding="utf-8")
    monkeypatch.setattr(
        module,
        "_git_value",
        lambda _root, *args: "a" * 40 if args == ("rev-parse", "HEAD") else "",
    )

    catalog = module.build_catalog(source, registry)

    assert catalog.repository_count == 1
    assert catalog.source_file_count == 1
    assert len(catalog.hints) == 1
    assert catalog.hints[0].text == "Create widgets with `Widget.open()`."
    assert catalog.hints[0].anchors == ["open", "Widget"]


def test_build_catalog_fails_on_registry_denominator_mismatch(tmp_path: Path, monkeypatch):
    module = _module()
    source = tmp_path / "reports"
    _write_ledger(source)
    registry = tmp_path / "products.json"
    registry.write_text(
        json.dumps(
            [
                {"family": "widget", "platform": "java"},
                {"family": "missing", "platform": "go"},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "_git_value", lambda *_args: "")

    with pytest.raises(ValueError, match="denominator mismatch"):
        module.build_catalog(source, registry)
