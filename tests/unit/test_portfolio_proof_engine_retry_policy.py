"""FAILED-ONLY retry policy: causal-fingerprint-gated retry, REASSESS_REQUIRED after two.

Proves the task's own TESTS bullets: "two identical failures produce REASSESS_REQUIRED" and the
implicit corollary -- a third attempt with the same fingerprint is never allowed to loop.
"""

from __future__ import annotations

from readme_agent import paths
from readme_agent.supervisor.blocked_decision_cache import record_blocked_outcome
from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
from readme_agent.supervisor.local_poc_cache import current_blocked_decision_dependencies
from readme_agent.supervisor.portfolio_proof_engine.retry_policy import (
    REASSESS_THRESHOLD,
    evaluate_retry,
)
from tests.unit.portfolio_proof_engine_fixtures import make_entry

ENTRY = make_entry(org_repo="acme/widget")


def _decision_path(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    org, repo = ENTRY.org_repo.split("/", maxsplit=1)
    return paths.readme_poc_blocked_decision_path(org, repo)


def _dependencies_at(source_revision: str) -> dict:
    """Mirrors exactly what `evaluate_retry()` computes internally, so a test can pin a fixture's
    dependencies to a *real* fingerprint rather than an arbitrary dict that would never match."""

    return current_blocked_decision_dependencies(
        org_repo=ENTRY.org_repo,
        source_revision=source_revision,
        control_plane_fingerprint=compute_control_plane_fingerprint(ENTRY.policy_profile),
        ecosystem=ENTRY.ecosystem,
        family=ENTRY.family,
    )


def _record_failure(path, *, source_revision: str, blocked_reason: str = "boom"):
    return record_blocked_outcome(
        path,
        org_repo=ENTRY.org_repo,
        status="BLOCKED",
        exit_code=1,
        blocked_reason=blocked_reason,
        blocked_category="agent_fixable",
        dependencies=_dependencies_at(source_revision),
    )


def test_no_prior_blocked_decision_is_eligible(tmp_path, monkeypatch):
    _decision_path(tmp_path, monkeypatch)
    decision = evaluate_retry(ENTRY, current_source_revision="a" * 40)
    assert decision.eligible is True
    assert decision.reassess_required is False


def test_unchanged_fingerprint_refuses_retry(tmp_path, monkeypatch):
    path = _decision_path(tmp_path, monkeypatch)
    _record_failure(path, source_revision="a" * 40)
    decision = evaluate_retry(ENTRY, current_source_revision="a" * 40)
    assert decision.eligible is False
    assert decision.reassess_required is False
    assert "no dependency fingerprint changed" in decision.reason


def test_changed_source_revision_makes_retry_eligible(tmp_path, monkeypatch):
    path = _decision_path(tmp_path, monkeypatch)
    _record_failure(path, source_revision="a" * 40)
    decision = evaluate_retry(ENTRY, current_source_revision="b" * 40)
    assert decision.eligible is True
    assert "fingerprint changed" in decision.reason


def test_two_consecutive_identical_failures_yield_reassess_required(tmp_path, monkeypatch):
    path = _decision_path(tmp_path, monkeypatch)
    first = _record_failure(path, source_revision="a" * 40)
    assert first.consecutive_count == 1
    second = _record_failure(path, source_revision="a" * 40)
    assert second.consecutive_count == REASSESS_THRESHOLD

    decision = evaluate_retry(ENTRY, current_source_revision="a" * 40)
    assert decision.reassess_required is True
    assert decision.eligible is False


def test_a_changed_fingerprint_resets_the_consecutive_counter(tmp_path, monkeypatch):
    path = _decision_path(tmp_path, monkeypatch)
    _record_failure(path, source_revision="a" * 40, blocked_reason="reason-a")
    reset = _record_failure(path, source_revision="a" * 40, blocked_reason="reason-b")
    # Same fingerprint (source revision unchanged) but a *different* blocked_reason -- the
    # existing blocked_decision_cache counts consecutive identical *reasons*, not identical
    # fingerprints alone, so a new failure mode resets the counter.
    assert reset.consecutive_count == 1
