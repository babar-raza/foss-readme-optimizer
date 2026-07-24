"""Tests for run_official_checks.py's tree-precondition recording
(`DD-RECORD-EVIDENCE-PRECONDITIONS`, `plans/codex/production-system-redesign.md`).

Regression coverage for a real, PROVEN incident: 4 historical runs were once cited as evidence
"against the same unchanged tree" when the tree was actually being edited between attempts (ruff-
format's own file count climbed mid-sequence, and the commit later cited as the frozen baseline
postdated the last attempt by 68 seconds). These tests prove the new labeling makes that exact
mislabeling impossible to miss."""

from governance.run_official_checks import _print_tree_precondition


class TestPrintTreePrecondition:
    def test_clean_status_prints_tree_clean(self, capsys):
        _print_tree_precondition("start", "")
        out = capsys.readouterr().out
        assert "TREE CLEAN" in out
        assert "TREE DIRTY" not in out

    def test_whitespace_only_status_prints_tree_clean(self, capsys):
        _print_tree_precondition("start", "\n  \n")
        out = capsys.readouterr().out
        assert "TREE CLEAN" in out

    def test_dirty_status_prints_tree_dirty_with_file_list(self, capsys):
        _print_tree_precondition("start", " M src/readme_agent/foo.py\n?? new_file.py\n")
        out = capsys.readouterr().out
        assert "TREE DIRTY" in out
        assert "src/readme_agent/foo.py" in out
        assert "new_file.py" in out

    def test_label_names_the_precondition_moment(self, capsys):
        _print_tree_precondition("end", "")
        out = capsys.readouterr().out
        assert "(end)" in out
