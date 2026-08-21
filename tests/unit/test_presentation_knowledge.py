"""Tests for current-source verification of imported presentation hints."""

import json
from pathlib import Path

from readme_agent.facts.presentation_knowledge import presentation_knowledge_facts


def _catalog(tmp_path: Path, hints: list[dict]) -> Path:
    path = tmp_path / "presentation-knowledge.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "producer_head": "a" * 40,
                "producer_dirty_fingerprint": "b" * 64,
                "source_tree_sha256": "c" * 64,
                "repository_count": 1,
                "source_file_count": 1,
                "hints": hints,
            }
        ),
        encoding="utf-8",
    )
    return path


def _hint(
    *,
    unit_id: str,
    field: str,
    text: str,
    evidence_path: str,
    anchors: list[str],
) -> dict:
    return {
        "schema_version": 1,
        "family": "widget",
        "platform": "java",
        "unit_id": unit_id,
        "field": field,
        "text": text,
        "evidence_path": evidence_path,
        "anchors": anchors,
        "source_file_sha256": "d" * 64,
    }


def test_current_source_promotes_capability_and_explicit_limitation(tmp_path: Path):
    source = tmp_path / "src" / "Widget.java"
    source.parent.mkdir()
    source.write_text(
        'public class Widget {\n  public void open() { System.out.println("open"); }\n}\n',
        encoding="utf-8",
    )
    (source.parent / "Renderer.java").write_text(
        "public class Renderer {\n"
        "  public void render() { throw new UnsupportedOperationException(); }\n"
        "}\n",
        encoding="utf-8",
    )
    catalog = _catalog(
        tmp_path,
        [
            _hint(
                unit_id="u1",
                field="product.capabilities",
                text="Open widgets with\n  `Widget.open()`.",
                evidence_path="src/Widget.java",
                anchors=["Widget", "open"],
            ),
            _hint(
                unit_id="u2",
                field="product.limitations",
                text="The `render()` operation is unsupported.",
                evidence_path="src/Renderer.java",
                anchors=["render"],
            ),
        ],
    )

    facts, selection = presentation_knowledge_facts(
        "widget",
        "java",
        root=tmp_path,
        source_revision="e" * 40,
        observed_at=None,
        catalog_path=catalog,
    )

    assert selection.accepted == 2
    assert selection.rejected == 0
    assert {fact.field for fact in facts} == {"product.capabilities", "product.limitations"}
    assert all(fact.verification_state == "verified" for fact in facts)
    capability = next(fact for fact in facts if fact.field == "product.capabilities")
    assert capability.value == ["Open widgets with `Widget.open()`."]
    assert all(
        assessment.accepted for fact in facts for assessment in fact.evidence_assessments or []
    )


def test_stale_anchor_and_escaping_evidence_fail_closed(tmp_path: Path):
    source = tmp_path / "Widget.ts"
    source.write_text("export class Widget { open(): void {} }\n", encoding="utf-8")
    catalog = _catalog(
        tmp_path,
        [
            _hint(
                unit_id="u1",
                field="product.capabilities",
                text="Export scenes with `MissingExporter`.",
                evidence_path="Widget.ts",
                anchors=["MissingExporter"],
            ),
            _hint(
                unit_id="u2",
                field="product.capabilities",
                text="Open widgets with `Widget`.",
                evidence_path="../outside.ts",
                anchors=["Widget"],
            ),
        ],
    )

    facts, selection = presentation_knowledge_facts(
        "widget",
        "java",
        root=tmp_path,
        source_revision="e" * 40,
        observed_at=None,
        catalog_path=catalog,
    )

    assert facts == []
    assert selection.accepted == 0
    assert selection.rejected == 2
    assert all(item.status == "rejected" for item in selection.dispositions)
