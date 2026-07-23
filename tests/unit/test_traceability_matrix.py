"""Semantic closure checks for the generated implementation-truth matrix."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO_ROOT / "plans" / "investigations" / "tools" / "traceability_matrix.py"


@pytest.fixture
def matrix_tool():
    spec = importlib.util.spec_from_file_location("traceability_matrix", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolves_a_real_top_level_pytest_node(matrix_tool):
    resolved, finding = matrix_tool._test_symbol_resolves(
        "tests/unit/test_traceability_matrix.py",
        "test_resolves_a_real_top_level_pytest_node",
    )

    assert resolved is True
    assert finding is None


def test_resolves_a_real_pytest_class_suite(matrix_tool):
    resolved, finding = matrix_tool._test_symbol_resolves(
        "tests/unit/test_traceability_matrix.py",
        "TestSemanticSuiteReference",
    )

    assert resolved is True
    assert finding is None


def test_rejects_a_missing_pytest_node(matrix_tool):
    resolved, finding = matrix_tool._test_symbol_resolves(
        "tests/unit/test_traceability_matrix.py",
        "TestMissing::test_not_real",
    )

    assert resolved is False
    assert "does not exist" in finding


class TestSemanticSuiteReference:
    def test_suite_member(self):
        assert True


def test_hashes_and_parses_cited_json_evidence(matrix_tool, tmp_path, monkeypatch):
    evidence = tmp_path / "plans" / "investigations" / "evidence" / "proof.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"result": "pass"}', encoding="utf-8")
    monkeypatch.setattr(matrix_tool, "REPO_ROOT", tmp_path)

    metadata, finding = matrix_tool._evidence_metadata("plans/investigations/evidence/proof.json")

    assert finding is None
    assert metadata["json_valid"] is True
    assert metadata["bytes"] == 18
    assert len(metadata["sha256"]) == 64


@pytest.mark.parametrize(
    "evidence",
    [
        "**Still honestly unmet**: a second mutation path bypasses this guarantee.",
        "This requirement remains incomplete pending production proof.",
        "The acceptance is not implemented.",
        "Status should remain `PARTIAL` until the live rerun.",
    ],
)
def test_detects_acceptance_text_that_contradicts_implemented_status(matrix_tool, evidence):
    assert matrix_tool.CONTRADICTED_IMPLEMENTATION_RE.search(evidence)


def test_matrix_only_refresh_preserves_status_candidate(matrix_tool, tmp_path, monkeypatch):
    matrix_file = tmp_path / "matrix.json"
    status_file = tmp_path / "status.md"
    status_file.write_text("valuable uncommitted candidate\n", encoding="utf-8")
    monkeypatch.setattr(matrix_tool, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(matrix_tool, "OUT_DIR", tmp_path)
    monkeypatch.setattr(matrix_tool, "OUT_FILE", matrix_file)
    monkeypatch.setattr(matrix_tool, "STATUS_MD", status_file)
    monkeypatch.setattr(
        matrix_tool,
        "build_matrix",
        lambda: {
            "total_implemented_rows_checked": 0,
            "rows_with_high_confidence_findings": [],
            "rows_with_informational_findings_only": [],
            "rows_clean": [],
            "all_rows": [],
        },
    )

    assert matrix_tool.main(["--matrix-only"]) == 0
    assert json.loads(matrix_file.read_text(encoding="utf-8"))["all_rows"] == []
    assert status_file.read_text(encoding="utf-8") == "valuable uncommitted candidate\n"
