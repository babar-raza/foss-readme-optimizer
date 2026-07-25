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


def test_full_registry_status_rows_cover_every_products_json_entry_live(matrix_tool):
    """RPOC-072: the per-repo table must have exactly as many rows as
    `data/products.json` has entries, computed live at test time (not hard-coded),
    proving the row-count guarantee against this repo's actual current registry."""
    products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))

    rows, manifest_path, manifest = matrix_tool._full_registry_readme_poc_status_rows()

    assert len(rows) == len(products)
    assert {row["org_repo"] for row in rows} == {
        f"{entry['repo_url'].split('github.com/', 1)[1]}" for entry in products
    }
    # Every row must resolve to *some* status string -- never None/missing.
    for row in rows:
        assert row["readme_poc_status"]
    # This repo has a real, committed portfolio-proof-manifest.json today, so the
    # lookup must find it rather than falling back to "no manifest" mode.
    assert manifest_path is not None
    assert manifest is not None


def test_generator_runs_without_error_against_current_real_data(matrix_tool):
    """The full generator (build_matrix + build_status_markdown) must run clean
    against this repo's actual current data -- no monkeypatching -- and the
    rendered markdown must contain exactly one repo row per products.json entry."""
    products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    matrix = matrix_tool.build_matrix()

    markdown = matrix_tool.build_status_markdown(matrix)

    assert "## Full-registry README POC status" in markdown
    # The repo table's rows are the only "| " lines before the "## Requirement
    # status counts" heading; slicing there avoids double-counting the
    # differently-shaped requirement-status table that follows it.
    full_registry_section = markdown.split("## Requirement status counts", 1)[0]
    repo_table_lines = [
        line
        for line in full_registry_section.splitlines()
        if line.startswith("| ") and "Org/Repo" not in line and "---" not in line
    ]
    assert len(repo_table_lines) == len(products)


def test_repo_genuinely_absent_from_manifest_shows_not_yet_run(matrix_tool, tmp_path, monkeypatch):
    """A repo with no entry at all in the most recent portfolio manifest (e.g. a
    Java pilot run through the separate evidence path, or a brand-new registry
    entry) must be reported "not yet run" -- never crash, never be silently
    dropped, never show a fabricated populated status."""
    products_path = tmp_path / "products.json"
    products_path.write_text(
        json.dumps(
            [
                {
                    "family": "widget",
                    "platform": "python",
                    "repo_name": "Widget-FOSS-for-Python",
                    "repo_url": "https://github.com/widget-foss/Widget-FOSS-for-Python",
                    "clone_url": "https://github.com/widget-foss/Widget-FOSS-for-Python.git",
                    "active": True,
                    "discovered_via": "github",
                    "mode": "dry_run",
                    "ecosystem": "python",
                    "policy_profile": "widget-foss",
                },
                {
                    "family": "widget",
                    "platform": "java",
                    "repo_name": "Widget-FOSS-for-Java",
                    "repo_url": "https://github.com/widget-foss/Widget-FOSS-for-Java",
                    "clone_url": "https://github.com/widget-foss/Widget-FOSS-for-Java.git",
                    "active": True,
                    "discovered_via": "github",
                    "mode": "full",
                    "ecosystem": "java",
                    "policy_profile": "widget-foss",
                },
            ]
        ),
        encoding="utf-8",
    )

    evidence_root = tmp_path / "evidence"
    manifest_dir = evidence_root / "level8-portfolio-readme-proposals-2026-07-25"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "portfolio-proof-manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-25T00:00:00+00:00",
                "results": [
                    {
                        "org_repo": "widget-foss/Widget-FOSS-for-Python",
                        "ecosystem": "python",
                        "readme_poc_status": None,
                    }
                    # Widget-FOSS-for-Java (the "Java pilot" stand-in) is
                    # deliberately absent -- it runs through a separate
                    # evidence path and must not crash or be dropped.
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(matrix_tool, "PRODUCTS_JSON", products_path)
    monkeypatch.setattr(matrix_tool, "EVIDENCE_ROOT", evidence_root)

    rows, manifest_path, manifest = matrix_tool._full_registry_readme_poc_status_rows()

    assert manifest_path == manifest_dir / "portfolio-proof-manifest.json"
    by_org_repo = {row["org_repo"]: row for row in rows}
    assert len(rows) == 2
    assert by_org_repo["widget-foss/Widget-FOSS-for-Python"]["readme_poc_status"] == "not_set"
    assert by_org_repo["widget-foss/Widget-FOSS-for-Java"]["readme_poc_status"] == "not yet run"


def test_no_manifest_at_all_reports_every_repo_not_yet_run(matrix_tool, tmp_path, monkeypatch):
    """When no portfolio-proof-manifest.json exists anywhere under the evidence
    root (e.g. a fresh checkout before the first portfolio run), every repo must
    still show "not yet run" -- not a crash, not an empty table."""
    products_path = tmp_path / "products.json"
    products_path.write_text(
        json.dumps(
            [
                {
                    "family": "widget",
                    "platform": "python",
                    "repo_name": "Widget-FOSS-for-Python",
                    "repo_url": "https://github.com/widget-foss/Widget-FOSS-for-Python",
                    "clone_url": "https://github.com/widget-foss/Widget-FOSS-for-Python.git",
                    "active": True,
                    "discovered_via": "github",
                    "mode": "dry_run",
                    "ecosystem": "python",
                    "policy_profile": "widget-foss",
                }
            ]
        ),
        encoding="utf-8",
    )
    empty_evidence_root = tmp_path / "no-evidence-here"

    monkeypatch.setattr(matrix_tool, "PRODUCTS_JSON", products_path)
    monkeypatch.setattr(matrix_tool, "EVIDENCE_ROOT", empty_evidence_root)

    rows, manifest_path, manifest = matrix_tool._full_registry_readme_poc_status_rows()

    assert manifest_path is None
    assert manifest is None
    assert len(rows) == 1
    assert rows[0]["readme_poc_status"] == "not yet run"


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
