"""Coverage and blocking-policy tests for the vendored check-battery
classification (`data/aspose_check_classification.json`) and its wiring
into `validation/aspose_checks_bridge.py`."""

from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

import pytest

from readme_agent.validation.aspose_checks import load_check_registry
from readme_agent.validation.aspose_checks_bridge import (
    AsposeCheckFindingV1,
    AsposeCheckResultV1,
    blocking_aspose_check_findings,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLASSIFICATION_PATH = _REPO_ROOT / "data" / "aspose_check_classification.json"
_SCRIPT_DIR = _REPO_ROOT / "scripts" / "data-refresh"


@pytest.fixture
def classify_module():
    sys.path.insert(0, str(_SCRIPT_DIR))
    try:
        module = import_module("classify_aspose_checks")
        yield module
    finally:
        sys.path.remove(str(_SCRIPT_DIR))
        sys.modules.pop("classify_aspose_checks", None)


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


def test_missing_classification_file_fails_closed(monkeypatch, tmp_path):
    """Gate R4 regression: a missing classification file must raise, never
    silently gate nothing (the old fail-open behavior this replaces)."""

    import readme_agent.validation.aspose_checks_bridge as bridge

    monkeypatch.setattr(bridge, "_CLASSIFICATION_PATH", tmp_path / "does-not-exist.json")
    result = _make_result(
        AsposeCheckFindingV1(
            check_name="check_no_leaked_docstring_artifacts",
            severity="critical",
            section=None,
            message="x",
        )
    )

    with pytest.raises(RuntimeError):
        blocking_aspose_check_findings(result)


def test_corrupt_classification_file_fails_closed(monkeypatch, tmp_path):
    import readme_agent.validation.aspose_checks_bridge as bridge

    corrupt = tmp_path / "aspose_check_classification.json"
    corrupt.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(bridge, "_CLASSIFICATION_PATH", corrupt)
    result = _make_result()

    with pytest.raises(RuntimeError):
        blocking_aspose_check_findings(result)


def test_classification_file_missing_checks_list_fails_closed(monkeypatch, tmp_path):
    import readme_agent.validation.aspose_checks_bridge as bridge

    wrong_shape = tmp_path / "aspose_check_classification.json"
    wrong_shape.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    monkeypatch.setattr(bridge, "_CLASSIFICATION_PATH", wrong_shape)
    result = _make_result()

    with pytest.raises(RuntimeError):
        blocking_aspose_check_findings(result)


def test_a_check_never_genuinely_run_against_any_fixture_never_auto_promotes(classify_module):
    """Gate R7 regression: a real bug this classification's own honesty
    depends on. `dependency_snapshot`-needing checks became `runnable_now`
    (Gate R6c) before any committed fixture's ProductFactsV2 actually
    carried the fact -- every one of the three real fixtures was built
    before that field existed, so `run_aspose_checks()` skips these checks
    entirely rather than running them with real data. The old logic
    (`name not in fired_critical`) could not tell "skipped everywhere" apart
    from "ran everywhere and found nothing", and would have promoted these
    checks to `applicable_reusable`/`blocking: true` with a reason claiming
    "zero false positives observed" for a check that was never actually
    exercised -- a vacuous, false empirical-validation claim."""

    registry = load_check_registry()
    dependency_snapshot_checks = {
        name
        for name, descriptor in registry.items()
        if "dependency_snapshot" in descriptor.parameters
    }
    assert dependency_snapshot_checks  # the real checks this bug affects genuinely exist

    fired_critical, genuinely_run, validated_against = classify_module._observed_critical_findings()

    assert validated_against  # the real fixtures loaded successfully
    assert dependency_snapshot_checks.isdisjoint(genuinely_run), (
        "committed fixtures predate the dependency_snapshot fact -- these checks must not "
        "appear as genuinely run until the fixtures are deliberately refreshed"
    )
    assert dependency_snapshot_checks.isdisjoint(fired_critical)

    classification = classify_module.build_classification()
    entries_by_name = {e["check_name"]: e for e in classification["checks"]}
    for name in dependency_snapshot_checks:
        entry = entries_by_name[name]
        if entry["runnable_now"] and entry["severity"] == "hard_gate":
            assert entry["blocking"] is False
            assert "never genuinely exercised" in entry["reason"]
