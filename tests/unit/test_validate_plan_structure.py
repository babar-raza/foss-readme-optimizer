"""Tests for scripts/governance/validate_plan_structure.py -- this gate has run live against
every commit since decision #46 (TC-26) but had no unit coverage of its own until TC-14 added the
GOV-022 wave-reconciliation check below. Per this project's own evidence standard, a "fixed"/"new"
gate needs a regression test proving it actually catches the failure mode it claims to, not just a
plausible-looking diff."""

from pathlib import Path

from governance.validate_plan_structure import (
    Result,
    _split_table_row,
    check_logs_shard_index_consistency,
    check_master_section_order,
    check_requirement_row_column_counts,
    check_requirements,
    check_specialist_module_map_completeness,
    check_wave_reconciliation_gate,
)


class TestRealRepoIsClean:
    """Smoke tests against the actual repo files -- these are the same checks that already run
    as a live pre-commit hook and CI step; this class just gives that a pytest-visible home."""

    def test_real_master_md_section_order_is_clean(self):
        result = Result()
        check_master_section_order(result)
        assert result.errors == []

    def test_real_requirements_md_rows_are_valid(self):
        result = Result()
        check_requirements(result)
        assert result.errors == []

    def test_real_logs_shard_index_is_consistent(self):
        result = Result()
        check_logs_shard_index_consistency(result)
        assert result.errors == []

    def test_real_specialist_module_map_is_complete(self):
        result = Result()
        check_specialist_module_map_completeness(result)
        assert result.errors == []

    def test_real_requirements_md_rows_have_correct_column_counts(self):
        result = Result()
        check_requirement_row_column_counts(result)
        assert result.errors == []


class TestRequirementRowColumnCounts:
    """Found live 2026-07-22: five real `requirements.md` rows (`OPS-009`, `EFF-004`, `ORC-006`,
    `VER-005`, `SCL-005`) had an unescaped `|` inside inline code (a shell pipe, a Python `str |
    None` union) that silently split one cell into two, or merged two cells into one -- a naive
    `.split("|")` misreads these rows; a real GFM-aware split, honoring `\\|` escaping, does not."""

    def test_split_table_row_respects_escaped_pipes(self):
        line = "| REQ-001 | P1 | IMPLEMENTED | uses `str \\| None` | evidence | Decision 1 |"
        cells = _split_table_row(line)
        assert len(cells) == 6
        assert cells[3] == "uses `str \\| None`"

    def test_split_table_row_naive_split_would_have_misread_it(self):
        """Negative control: without escaping, the exact same content DOES split into 7 cells --
        proving the escape (not incidental cell content) is what makes the count correct."""
        line = "| REQ-001 | P1 | IMPLEMENTED | uses `str | None` | evidence | Decision 1 |"
        cells = _split_table_row(line)
        assert len(cells) == 7

    def test_row_with_unescaped_pipe_in_inline_code_is_flagged(self, tmp_path, monkeypatch):
        import governance.validate_plan_structure as vps

        requirements = tmp_path / "requirements.md"
        requirements.write_text(
            "| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |\n"
            "|---|---|---|---|---|---|\n"
            "| REQ-001 | P1 | IMPLEMENTED | text | uses `str | None` here | Decision 1 |\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(vps, "REQUIREMENTS_MD", requirements)

        result = Result()
        check_requirement_row_column_counts(result)

        assert len(result.errors) == 1
        assert "REQ-001" in result.errors[0]
        assert "7 cells" in result.errors[0]

    def test_row_with_escaped_pipe_is_not_flagged(self, tmp_path, monkeypatch):
        import governance.validate_plan_structure as vps

        requirements = tmp_path / "requirements.md"
        requirements.write_text(
            "| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |\n"
            "|---|---|---|---|---|---|\n"
            "| REQ-001 | P1 | IMPLEMENTED | text | uses `str \\| None` here | Decision 1 |\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(vps, "REQUIREMENTS_MD", requirements)

        result = Result()
        check_requirement_row_column_counts(result)

        assert result.errors == []

    def test_row_with_a_missing_pipe_merging_two_cells_is_flagged(self, tmp_path, monkeypatch):
        import governance.validate_plan_structure as vps

        requirements = tmp_path / "requirements.md"
        requirements.write_text(
            "| ID | Priority | Status | Requirement | Acceptance evidence | Traceability |\n"
            "|---|---|---|---|---|---|\n"
            "| REQ-001 | P1 | IMPLEMENTED | text merged with evidence | Decision 1 |\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(vps, "REQUIREMENTS_MD", requirements)

        result = Result()
        check_requirement_row_column_counts(result)

        assert len(result.errors) == 1
        assert "5 cells" in result.errors[0]


class TestWaveReconciliationGate:
    """GOV-022: a Build Checklist wave may not flip `[ ]` -> `[x]` without a matching logs/ entry
    in the same change. Uses tmp_path fixtures and the injectable `previous_master_text` seam --
    never touches the real plans/master.md or logs/."""

    def _write_master(self, tmp_path: Path, waves_block: str) -> Path:
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        master = plans_dir / "master.md"
        master.write_text(f"## Build Checklist\n\n{waves_block}\n", encoding="utf-8")
        return master

    def _write_logs(self, tmp_path: Path, wave_phase_cell: str) -> Path:
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        shard = logs_dir / "2026-07-22.md"
        shard.write_text(
            "| Date | Tags | Decisions | Requirements | Wave/Phase | Summary |\n"
            "|---|---|---|---|---|---|\n"
            f"| 2026-07-22 | tags | # | `REQ-001` | {wave_phase_cell} | summary text |\n",
            encoding="utf-8",
        )
        return logs_dir

    def test_newly_checked_wave_with_no_matching_log_entry_is_an_error(self, tmp_path, monkeypatch):
        import governance.validate_plan_structure as vps

        previous_text = "## Build Checklist\n\n- [ ] Wave 9 -- description\n"
        master = self._write_master(tmp_path, "- [x] Wave 9 -- description")
        logs_dir = self._write_logs(tmp_path, "Wave 2")  # unrelated wave -- deliberately no match

        monkeypatch.setattr(vps, "MASTER_MD", master)
        monkeypatch.setattr(vps, "LOGS_DIR", logs_dir)

        result = Result()
        check_wave_reconciliation_gate(result, previous_master_text=previous_text)

        assert len(result.errors) == 1
        assert "Wave 9" in result.errors[0]
        assert "GOV-022" in result.errors[0]

    def test_newly_checked_wave_with_a_matching_log_entry_passes(self, tmp_path, monkeypatch):
        import governance.validate_plan_structure as vps

        previous_text = "## Build Checklist\n\n- [ ] Wave 9 -- description\n"
        master = self._write_master(tmp_path, "- [x] Wave 9 -- description")
        logs_dir = self._write_logs(tmp_path, "Wave 9")

        monkeypatch.setattr(vps, "MASTER_MD", master)
        monkeypatch.setattr(vps, "LOGS_DIR", logs_dir)

        result = Result()
        check_wave_reconciliation_gate(result, previous_master_text=previous_text)

        assert result.errors == []

    def test_a_sub_numbered_log_entry_satisfies_its_whole_number_wave(self, tmp_path, monkeypatch):
        """`Wave 8.6` in a log entry should reconcile a `Wave 8` checklist item -- sub-phases are
        part of the same wave, not a separate one."""
        import governance.validate_plan_structure as vps

        previous_text = "## Build Checklist\n\n- [ ] Wave 8 -- description\n"
        master = self._write_master(tmp_path, "- [x] Wave 8 -- description")
        logs_dir = self._write_logs(tmp_path, "Wave 8.6")

        monkeypatch.setattr(vps, "MASTER_MD", master)
        monkeypatch.setattr(vps, "LOGS_DIR", logs_dir)

        result = Result()
        check_wave_reconciliation_gate(result, previous_master_text=previous_text)

        assert result.errors == []

    def test_an_already_checked_wave_is_never_retroactively_flagged(self, tmp_path, monkeypatch):
        """Waves 0-8 were checked off before this gate (or its logging tool) existed. A wave that
        was ALREADY `[x]` at HEAD must never be re-flagged just because it still has no matching
        logs/ entry -- only a fresh `[ ]` -> `[x]` transition in the change under review counts."""
        import governance.validate_plan_structure as vps

        previous_text = "## Build Checklist\n\n- [x] Wave 3 -- description\n"
        master = self._write_master(tmp_path, "- [x] Wave 3 -- description")
        logs_dir = self._write_logs(tmp_path, "Wave 9")  # no Wave 3 entry anywhere

        monkeypatch.setattr(vps, "MASTER_MD", master)
        monkeypatch.setattr(vps, "LOGS_DIR", logs_dir)

        result = Result()
        check_wave_reconciliation_gate(result, previous_master_text=previous_text)

        assert result.errors == []

    def test_no_git_history_available_skips_the_check_without_erroring(self, tmp_path, monkeypatch):
        import governance.validate_plan_structure as vps

        master = self._write_master(tmp_path, "- [x] Wave 9 -- description")
        monkeypatch.setattr(vps, "MASTER_MD", master)

        result = Result()
        check_wave_reconciliation_gate(result, previous_master_text=None)

        assert result.errors == []
