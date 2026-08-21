"""Tests for the deterministic repository-scout compatibility adapter."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.repository_knowledge_adapter import adapt_scout_output


def _raw_output(root: Path, claims: list[dict]) -> None:
    required = (
        "absent_evidence.json",
        "api_surface.json",
        "class_graph.json",
        "coverage_matrix.json",
        "formats.json",
        "install.md",
        "limitations.md",
        "scout_report.json",
        "scout-validation.json",
        "snippets/snippets_index.json",
    )
    for relative in required:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    (root / "model.yaml").write_text("product: fixture\n", encoding="utf-8")
    (root / "claims.json").write_text(
        json.dumps({"claim_count": len(claims), "claims": claims}), encoding="utf-8"
    )


def _claim(path: str, *, text: str = "Widget.open() -> Document") -> dict:
    return {
        "claim_id": "CLM-widget-123456",
        "kind": "api_method",
        "text": text,
        "claim_source": "scout",
        "evidence": [{"file": path, "line": 4}],
    }


def test_adapter_merges_semantic_duplicates_and_retains_all_evidence(tmp_path: Path) -> None:
    _raw_output(tmp_path, [_claim("src/widget.py"), _claim("src/compat/widget.py")])

    adapt_scout_output(tmp_path, extracted_at="2026-08-21T00:00:00Z", generator_sha256="a" * 64)

    claims = json.loads((tmp_path / "claims.json").read_text(encoding="utf-8"))
    assert len(claims) == 1
    assert claims[0]["claim_id"].startswith("CLM-widget-")
    assert len(claims[0]["claim_id"].rsplit("-", maxsplit=1)[1]) == 16
    assert {item["file"] for item in claims[0]["evidence"]} == {
        "src/widget.py",
        "src/compat/widget.py",
    }


def test_adapter_rekeys_conflicting_upstream_ids_by_semantic_content(tmp_path: Path) -> None:
    _raw_output(tmp_path, [_claim("src/widget.py"), _claim("src/widget.py", text="Other fact")])

    adapt_scout_output(
        tmp_path,
        extracted_at="2026-08-21T00:00:00Z",
        generator_sha256="a" * 64,
    )

    claims = json.loads((tmp_path / "claims.json").read_text(encoding="utf-8"))
    assert len(claims) == 2
    assert len({claim["claim_id"] for claim in claims}) == 2
