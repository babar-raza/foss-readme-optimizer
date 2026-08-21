"""Tests for portfolio knowledge-selection denominator integrity."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from readme_agent.facts import portfolio_knowledge_selection as selection


def _receipt(path: Path, *, org_repo: str, generator: str = "a" * 64) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-21T00:00:00Z",
                "generator_sha256": generator,
                "requested_repositories": [org_repo],
                "entries": [
                    {
                        "org_repo": org_repo,
                        "family": "widget",
                        "platform": "python",
                        "source_revision": None,
                        "status": "non_processable_no_implementation",
                        "claim_count": 0,
                        "generator_sha256": generator,
                        "output_root": None,
                        "detail": "typed disposition",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_selection_audit_accepts_one_exact_typed_disposition(tmp_path, monkeypatch) -> None:
    org_repo = "org/Aspose.Widget-FOSS-for-Python"
    entry = SimpleNamespace(org_repo=org_repo, family="widget", platform="python")
    monkeypatch.setattr(selection, "load_products", lambda: (entry,))

    report = selection.audit_portfolio_knowledge_selection(
        (_receipt(tmp_path / "refresh.json", org_repo=org_repo),),
        output_dir=tmp_path / "output",
    )

    assert report.denominator == 1
    assert report.typed_dispositions == 1
    assert report.failed == 0


def test_selection_audit_rejects_a_denominator_gap(tmp_path, monkeypatch) -> None:
    org_repo = "org/Aspose.Widget-FOSS-for-Python"
    missing = "org/Aspose.Other-FOSS-for-Python"
    monkeypatch.setattr(
        selection,
        "load_products",
        lambda: (
            SimpleNamespace(org_repo=org_repo, family="widget", platform="python"),
            SimpleNamespace(org_repo=missing, family="other", platform="python"),
        ),
    )

    with pytest.raises(ValueError, match="denominator mismatch"):
        selection.audit_portfolio_knowledge_selection(
            (_receipt(tmp_path / "refresh.json", org_repo=org_repo),),
            output_dir=tmp_path / "output",
        )
