"""Coverage and blocking-policy tests for the vendored check-battery
classification (`data/aspose_check_classification.json`) and its wiring
into `validation/aspose_checks_bridge.py`."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.validation.aspose_checks import load_check_registry
from readme_agent.validation.aspose_checks_bridge import (
    AsposeCheckFindingV1,
    AsposeCheckResultV1,
    blocking_aspose_check_findings,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLASSIFICATION_PATH = _REPO_ROOT / "data" / "aspose_check_classification.json"
_VALID_CLASSIFICATIONS = {
    "applicable_reusable",
    "applicable_after_adaptation",
    "diagnostic_heuristic",
    "unrelated",
}


def _load_classification() -> dict:
    return json.loads(_CLASSIFICATION_PATH.read_text(encoding="utf-8"))


def test_classification_file_exists_and_is_well_formed():
    raw = _load_classification()

    assert raw["schema_version"] == 1
    assert isinstance(raw["checks"], list)
    assert raw["check_count"] == len(raw["checks"])


def test_classification_covers_every_check_in_the_current_registry():
    """No unclassified/skipped-silently check: every real check in the
    vendored battery has exactly one classification entry, and no stale
    entry names a check the registry no longer has."""

    registry = load_check_registry()
    raw = _load_classification()

    classified_names = {entry["check_name"] for entry in raw["checks"]}
    assert classified_names == set(registry)


def test_every_classification_entry_has_an_explicit_reason_and_valid_bucket():
    raw = _load_classification()

    for entry in raw["checks"]:
        assert entry["classification"] in _VALID_CLASSIFICATIONS
        assert entry["reason"], f"{entry['check_name']} has no reason recorded"
        assert isinstance(entry["blocking"], bool)
        assert isinstance(entry["runnable_now"], bool)


def test_blocking_is_never_true_for_a_non_runnable_or_heuristic_check():
    """Never treat 'skipped' as 'passed', and never block on a heuristic:
    a check that isn't runnable today, or is classified diagnostic, can
    never carry `blocking: true`."""

    raw = _load_classification()

    for entry in raw["checks"]:
        if not entry["runnable_now"] or entry["classification"] == "diagnostic_heuristic":
            assert entry["blocking"] is False


def test_blocking_count_matches_the_actual_blocking_entries():
    raw = _load_classification()

    assert raw["blocking_count"] == sum(1 for entry in raw["checks"] if entry["blocking"])


def test_at_least_one_check_is_promoted_to_blocking():
    """A real, non-trivial promotion happened -- this is not an all-zero
    placeholder classification."""

    raw = _load_classification()

    assert raw["blocking_count"] > 0


def _make_result(*findings: AsposeCheckFindingV1) -> AsposeCheckResultV1:
    return AsposeCheckResultV1(
        valid=not any(f.severity == "critical" for f in findings),
        checks_run=tuple(f.check_name for f in findings),
        checks_skipped=(),
        checks_errored=(),
        findings=findings,
    )


def test_blocking_aspose_check_findings_filters_to_classified_blocking_checks_only():
    raw = _load_classification()
    blocking_name = next(e["check_name"] for e in raw["checks"] if e["blocking"])
    nonblocking_name = next(e["check_name"] for e in raw["checks"] if not e["blocking"])

    blocking_finding = AsposeCheckFindingV1(
        check_name=blocking_name, severity="critical", section=None, message="real defect"
    )
    nonblocking_finding = AsposeCheckFindingV1(
        check_name=nonblocking_name, severity="critical", section=None, message="not promoted"
    )

    result = _make_result(blocking_finding, nonblocking_finding)
    blocking = blocking_aspose_check_findings(result)

    assert blocking == [blocking_finding]


def test_blocking_aspose_check_findings_empty_when_no_findings_are_classified_blocking():
    raw = _load_classification()
    nonblocking_name = next(e["check_name"] for e in raw["checks"] if not e["blocking"])

    result = _make_result(
        AsposeCheckFindingV1(
            check_name=nonblocking_name, severity="critical", section=None, message="advisory only"
        )
    )

    assert blocking_aspose_check_findings(result) == []
