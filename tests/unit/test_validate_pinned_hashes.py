"""Tests for scripts/governance/validate_pinned_hashes.py (Decision #109, requirement
GOV-032, 2026-08-27 production recovery sprint). Per this project's own evidence standard,
a new gate needs a regression test proving it actually catches the failure mode it claims
to, not just a plausible-looking diff."""

from __future__ import annotations

import json

from governance import validate_pinned_hashes as vph


def test_real_repository_state_is_clean():
    """The live repository, as of this fix landing, must already satisfy every pin --
    if this fails, either a real drift was introduced or the checker itself is wrong."""

    assert vph.main() == 0


def _write_catalog(path, records):
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")


def _base_records():
    return [
        {"requirement_id": "GOV-001", "status": "IMPLEMENTED"},
        {"requirement_id": "GOV-002", "status": "PLANNED"},
        {"requirement_id": "CORE-001", "status": "BACKLOG"},
    ]


def _base_requirements_md():
    return (
        "The catalog contains **3** requirements:\n\n"
        "- `BACKLOG`: 1\n"
        "- `IMPLEMENTED`: 1\n"
        "- `PLANNED`: 1\n\n"
        "Families: `CORE` 1, `GOV` 2.\n"
    )


class TestRequirementsMdConsistency:
    def test_matching_summary_reports_no_mismatch(self, tmp_path, monkeypatch):
        catalog = tmp_path / "catalog.jsonl"
        _write_catalog(catalog, _base_records())
        monkeypatch.setattr(vph, "REQUIREMENTS_CATALOG_PATH", catalog)

        md = tmp_path / "requirements.md"
        md.write_text(_base_requirements_md(), encoding="utf-8")
        monkeypatch.setattr(vph, "REQUIREMENTS_MD_PATH", md)

        assert vph._check_requirements_md(vph._jsonl_records(catalog)) == []

    def test_stale_total_count_is_caught(self, tmp_path, monkeypatch):
        catalog = tmp_path / "catalog.jsonl"
        _write_catalog(catalog, _base_records())
        monkeypatch.setattr(vph, "REQUIREMENTS_CATALOG_PATH", catalog)

        md = tmp_path / "requirements.md"
        # Deliberately staleness-mismatched: the file was never appended after a real
        # catalog change, exactly the drift class this checker exists to catch.
        md.write_text(_base_requirements_md().replace("**3**", "**2**"), encoding="utf-8")
        monkeypatch.setattr(vph, "REQUIREMENTS_MD_PATH", md)

        mismatches = vph._check_requirements_md(vph._jsonl_records(catalog))

        assert len(mismatches) == 1
        assert mismatches[0].label == "plans/requirements.md total count"
        assert "recorded 2, catalog has 3" in mismatches[0].detail
        assert mismatches[0].fix_command  # a usable fix command is always present

    def test_stale_status_count_is_caught(self, tmp_path, monkeypatch):
        catalog = tmp_path / "catalog.jsonl"
        _write_catalog(catalog, _base_records())
        monkeypatch.setattr(vph, "REQUIREMENTS_CATALOG_PATH", catalog)

        md = tmp_path / "requirements.md"
        stale_text = _base_requirements_md().replace("`PLANNED`: 1", "`PLANNED`: 5")
        md.write_text(stale_text, encoding="utf-8")
        monkeypatch.setattr(vph, "REQUIREMENTS_MD_PATH", md)

        mismatches = vph._check_requirements_md(vph._jsonl_records(catalog))

        assert any(m.label == "plans/requirements.md `PLANNED` count" for m in mismatches)

    def test_stale_family_line_is_caught(self, tmp_path, monkeypatch):
        catalog = tmp_path / "catalog.jsonl"
        _write_catalog(catalog, _base_records())
        monkeypatch.setattr(vph, "REQUIREMENTS_CATALOG_PATH", catalog)

        md = tmp_path / "requirements.md"
        md.write_text(_base_requirements_md().replace("`GOV` 2", "`GOV` 99"), encoding="utf-8")
        monkeypatch.setattr(vph, "REQUIREMENTS_MD_PATH", md)

        mismatches = vph._check_requirements_md(vph._jsonl_records(catalog))

        assert any(m.label == "plans/requirements.md Families line" for m in mismatches)


class TestGraphPointerConsistency:
    def test_matching_pointer_reports_no_mismatch(self, tmp_path, monkeypatch):
        target = tmp_path / "catalog.jsonl"
        _write_catalog(target, _base_records())
        actual_sha256 = vph._sha256_bytes(target.read_bytes())

        graph = tmp_path / "graph.yaml"
        graph.write_text(
            "requirement_catalog:\n"
            f"  path: {target.name}\n"
            f"  sha256: {actual_sha256}\n"
            "  record_count: 3\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(vph, "GRAPH_PATH", graph)
        monkeypatch.setattr(vph, "REPO_ROOT", tmp_path)

        assert vph._check_graph_pointers() == []

    def test_stale_pointer_sha256_is_caught(self, tmp_path, monkeypatch):
        target = tmp_path / "catalog.jsonl"
        _write_catalog(target, _base_records())

        graph = tmp_path / "graph.yaml"
        graph.write_text(
            "requirement_catalog:\n"
            f"  path: {target.name}\n"
            "  sha256: 0000000000000000000000000000000000000000000000000000000000000000\n"
            "  record_count: 3\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(vph, "GRAPH_PATH", graph)
        monkeypatch.setattr(vph, "REPO_ROOT", tmp_path)

        mismatches = vph._check_graph_pointers()

        assert any(m.label == "graph `requirement_catalog.sha256`" for m in mismatches)

    def test_stale_pointer_record_count_is_caught(self, tmp_path, monkeypatch):
        target = tmp_path / "catalog.jsonl"
        _write_catalog(target, _base_records())
        actual_sha256 = vph._sha256_bytes(target.read_bytes())

        graph = tmp_path / "graph.yaml"
        graph.write_text(
            "requirement_catalog:\n"
            f"  path: {target.name}\n"
            f"  sha256: {actual_sha256}\n"
            "  record_count: 999\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(vph, "GRAPH_PATH", graph)
        monkeypatch.setattr(vph, "REPO_ROOT", tmp_path)

        mismatches = vph._check_graph_pointers()

        assert any(m.label == "graph `requirement_catalog.record_count`" for m in mismatches)


class TestMainExitCode:
    def test_clean_state_exits_zero(self, tmp_path, monkeypatch, capsys):
        catalog = tmp_path / "catalog.jsonl"
        _write_catalog(catalog, _base_records())
        monkeypatch.setattr(vph, "REQUIREMENTS_CATALOG_PATH", catalog)

        md = tmp_path / "requirements.md"
        md.write_text(_base_requirements_md(), encoding="utf-8")
        monkeypatch.setattr(vph, "REQUIREMENTS_MD_PATH", md)

        graph = tmp_path / "graph.yaml"
        graph.write_text("{}\n", encoding="utf-8")
        monkeypatch.setattr(vph, "GRAPH_PATH", graph)
        monkeypatch.setattr(vph, "REPO_ROOT", tmp_path)

        assert vph.main() == 0
        assert "clean" in capsys.readouterr().out

    def test_mismatch_exits_one_with_fix_command_printed(self, tmp_path, monkeypatch, capsys):
        catalog = tmp_path / "catalog.jsonl"
        _write_catalog(catalog, _base_records())
        monkeypatch.setattr(vph, "REQUIREMENTS_CATALOG_PATH", catalog)

        md = tmp_path / "requirements.md"
        md.write_text(_base_requirements_md().replace("**3**", "**2**"), encoding="utf-8")
        monkeypatch.setattr(vph, "REQUIREMENTS_MD_PATH", md)

        graph = tmp_path / "graph.yaml"
        graph.write_text("{}\n", encoding="utf-8")
        monkeypatch.setattr(vph, "GRAPH_PATH", graph)
        monkeypatch.setattr(vph, "REPO_ROOT", tmp_path)

        assert vph.main() == 1
        output = capsys.readouterr().out
        assert "ERROR: plans/requirements.md total count" in output
        assert "fix:" in output
