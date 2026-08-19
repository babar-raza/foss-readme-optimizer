"""Gate R7: every one of the 89+ vendored aspose.org checks gets exactly
one accounted outcome per real run (pass/fail/skip/error/not_applicable),
with a real reason -- closing the gap where run_aspose_checks()'s own
checks_run/checks_skipped/checks_errored were computed and then discarded
by every caller."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.validation.aspose_check_coverage import build_check_coverage_report
from readme_agent.validation.aspose_checks import load_check_registry
from readme_agent.validation.aspose_checks_bridge import (
    AsposeCheckFindingV1,
    AsposeCheckResultV1,
    load_blocking_check_names,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLASSIFICATION_PATH = _REPO_ROOT / "data" / "aspose_check_classification.json"


def _real_classification() -> dict:
    return json.loads(_CLASSIFICATION_PATH.read_text(encoding="utf-8"))


def test_every_registered_check_gets_exactly_one_outcome():
    registry = load_check_registry()
    result = AsposeCheckResultV1(
        valid=True,
        checks_run=(),
        checks_skipped=tuple(registry),
        checks_errored=(),
        findings=(),
    )

    report = build_check_coverage_report(result, _real_classification())

    assert report.check_count == len(registry)
    assert len(report.entries) == len(registry)
    assert {entry.check_name for entry in report.entries} == set(registry)
    names = [entry.check_name for entry in report.entries]
    assert len(names) == len(set(names))  # each check appears exactly once
    assert (
        report.pass_count
        + report.fail_count
        + report.skip_count
        + report.error_count
        + report.not_applicable_count
        == report.check_count
    )


def test_a_check_with_a_real_finding_is_fail_not_pass():
    registry = load_check_registry()
    some_check = next(iter(registry))
    result = AsposeCheckResultV1(
        valid=False,
        checks_run=(some_check,),
        checks_skipped=tuple(name for name in registry if name != some_check),
        checks_errored=(),
        findings=(
            AsposeCheckFindingV1(
                check_name=some_check, severity="critical", section=None, message="real defect"
            ),
        ),
    )

    report = build_check_coverage_report(result, _real_classification())

    entry = next(e for e in report.entries if e.check_name == some_check)
    assert entry.outcome == "fail"
    assert report.fail_count == 1


def test_a_check_that_ran_clean_is_pass():
    registry = load_check_registry()
    some_check = next(iter(registry))
    result = AsposeCheckResultV1(
        valid=True,
        checks_run=(some_check,),
        checks_skipped=tuple(name for name in registry if name != some_check),
        checks_errored=(),
        findings=(),
    )

    report = build_check_coverage_report(result, _real_classification())

    entry = next(e for e in report.entries if e.check_name == some_check)
    assert entry.outcome == "pass"
    assert report.pass_count == 1


def test_an_errored_check_is_error_not_silently_skipped():
    registry = load_check_registry()
    some_check = next(iter(registry))
    result = AsposeCheckResultV1(
        valid=True,
        checks_run=(),
        checks_skipped=tuple(name for name in registry if name != some_check),
        checks_errored=(some_check,),
        findings=(),
    )

    report = build_check_coverage_report(result, _real_classification())

    entry = next(e for e in report.entries if e.check_name == some_check)
    assert entry.outcome == "error"
    assert report.error_count == 1


def test_blocking_flag_matches_the_real_governed_blocking_set():
    registry = load_check_registry()
    result = AsposeCheckResultV1(
        valid=True,
        checks_run=(),
        checks_skipped=tuple(registry),
        checks_errored=(),
        findings=(),
    )
    blocking_names = load_blocking_check_names()

    report = build_check_coverage_report(result, _real_classification())

    for entry in report.entries:
        assert entry.blocking == (entry.check_name in blocking_names)
    assert any(entry.blocking for entry in report.entries)  # real, non-trivial


def test_real_end_to_end_report_against_the_real_registry_and_classification():
    """Runs the actual bridge (no mocking) against a minimal real candidate
    and confirms the resulting coverage report is internally consistent."""

    from readme_agent.validation.aspose_checks_bridge import run_aspose_checks

    result = run_aspose_checks("# Widget\n\nA small tool.\n", None)

    report = build_check_coverage_report(result, _real_classification())

    assert report.check_count == len(load_check_registry())
    assert report.pass_count + report.fail_count == len(result.checks_run)
    assert report.skip_count >= len(result.checks_skipped)
    assert report.error_count == len(result.checks_errored)
