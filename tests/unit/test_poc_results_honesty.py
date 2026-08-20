"""Regressions for `commands_poc.py`'s status/RESULTS.md honesty: a rejected
or otherwise-invalid candidate must never be reported as accepted-equivalent
(`REVIEW_CANDIDATE`), and a re-run for the same repository must never leave a
stale, contradicting row behind for that repository."""

from __future__ import annotations

import readme_agent.commands_poc as commands_poc
from readme_agent.commands_poc import _append_results_row, _poc_status


def _verdict(outcome: str) -> dict:
    return {"verdict": outcome, "checks": {}, "reason": ""}


def _noop(reproducible: bool = True) -> dict:
    return {"verdict": "RENDER_REPRODUCIBLE" if reproducible else "RENDER_REPRODUCIBILITY_FAILED"}


def test_fully_clean_candidate_is_review_candidate():
    status = _poc_status(_verdict("accept"), review_open=False, ledger_valid=True, noop=_noop(True))

    assert status == "REVIEW_CANDIDATE"


def test_rejected_verdict_never_reports_as_review_candidate():
    status = _poc_status(_verdict("reject"), review_open=False, ledger_valid=True, noop=_noop(True))

    assert status != "REVIEW_CANDIDATE"
    assert status == "DIAGNOSTIC_VALIDATION_reject"


def test_open_review_never_reports_as_review_candidate():
    status = _poc_status(_verdict("accept"), review_open=True, ledger_valid=True, noop=_noop(True))

    assert status != "REVIEW_CANDIDATE"
    assert status == "DIAGNOSTIC_REVIEW_OPEN"


def test_invalid_disposition_ledger_never_reports_as_review_candidate():
    """The exact 2026-08-20 3D/Barcode shape: verdict=accept, review=ACCEPT,
    but disposition_ledger_valid=False -- must never present as accepted."""

    status = _poc_status(
        _verdict("accept"), review_open=False, ledger_valid=False, noop=_noop(True)
    )

    assert status != "REVIEW_CANDIDATE"
    assert status == "DIAGNOSTIC_DISPOSITION_LEDGER_INVALID"


def test_unreproducible_noop_never_reports_as_review_candidate():
    status = _poc_status(
        _verdict("accept"), review_open=False, ledger_valid=True, noop=_noop(False)
    )

    assert status != "REVIEW_CANDIDATE"
    assert status == "DIAGNOSTIC_NOOP_UNREPRODUCIBLE"


def test_review_open_takes_priority_over_ledger_invalidity_in_status_label():
    """Priority is a labeling detail, not a correctness gap -- either
    condition alone already keeps this out of REVIEW_CANDIDATE."""

    status = _poc_status(_verdict("accept"), review_open=True, ledger_valid=False, noop=_noop(True))

    assert status != "REVIEW_CANDIDATE"


def test_results_row_rewrite_replaces_the_stale_row_for_the_same_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(commands_poc, "_SHARE_ROOT", tmp_path)

    _append_results_row("org/repo-a", "DIAGNOSTIC_VALIDATION_reject", "path-a", "old issue")
    _append_results_row("org/repo-b", "REVIEW_CANDIDATE", "path-b", "none")
    _append_results_row("org/repo-a", "REVIEW_CANDIDATE", "path-a-2", "none")

    text = (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| org/")]

    assert len(rows) == 2
    repo_a_row = next(row for row in rows if "org/repo-a" in row)
    assert "REVIEW_CANDIDATE" in repo_a_row
    assert "DIAGNOSTIC_VALIDATION_reject" not in text
    assert "old issue" not in text


def test_results_row_rewrite_never_carries_forward_non_table_content(tmp_path, monkeypatch):
    """A stray hand-edited summary (e.g. a manually inserted "DELIVERED"
    claim outside the canonical table shape) must never survive a rewrite --
    RESULTS.md is machine-generated evidence, not a hand-editable summary."""

    monkeypatch.setattr(commands_poc, "_SHARE_ROOT", tmp_path)
    results = tmp_path / "RESULTS.md"
    results.parent.mkdir(parents=True, exist_ok=True)
    results.write_text(
        "# POC results -- Delivered README files: **31 of 31**\n\n"
        "| org/repo-a | DELIVERED | none |\n\n"
        "| Repo | Status | File | Open issues |\n"
        "| --- | --- | --- | --- |\n"
        "| org/repo-a | DIAGNOSTIC_VALIDATION_reject | path-a | claim accountability rejected |\n",
        encoding="utf-8",
    )

    _append_results_row("org/repo-a", "DIAGNOSTIC_VALIDATION_reject", "path-a", "still rejected")

    text = results.read_text(encoding="utf-8")
    assert "DELIVERED" not in text
    assert text.count("org/repo-a") == 1


def test_results_header_is_canonical_after_a_write(tmp_path, monkeypatch):
    monkeypatch.setattr(commands_poc, "_SHARE_ROOT", tmp_path)

    _append_results_row("org/repo-a", "REVIEW_CANDIDATE", "path-a", "none")

    text = (tmp_path / "RESULTS.md").read_text(encoding="utf-8")
    assert text.startswith("# POC results\n")
    assert "| Repo | Status | File | Open issues |" in text
