"""Global deadline / per-stage timeout budget."""

from __future__ import annotations

import time

from readme_agent.supervisor.portfolio_proof_engine.deadline import DeadlineBudget


def test_no_total_seconds_never_expires():
    budget = DeadlineBudget(total_seconds=None)
    assert budget.expired() is False
    assert budget.remaining() is None


def test_expires_after_total_seconds_elapses():
    budget = DeadlineBudget(total_seconds=0.01)
    time.sleep(0.05)
    assert budget.expired() is True
    assert budget.remaining() == 0.0


def test_remaining_counts_down_and_never_goes_negative():
    budget = DeadlineBudget(total_seconds=1.0)
    remaining = budget.remaining()
    assert remaining is not None
    assert 0.0 <= remaining <= 1.0


def test_stage_timeout_none_never_times_out():
    budget = DeadlineBudget(total_seconds=None, per_stage_seconds=None)
    assert budget.stage_timed_out(time.monotonic() - 1000) is False


def test_stage_timeout_fires_after_per_stage_seconds():
    budget = DeadlineBudget(total_seconds=None, per_stage_seconds=0.01)
    started = time.monotonic()
    time.sleep(0.05)
    assert budget.stage_timed_out(started) is True


def test_stage_timeout_not_yet_fired():
    budget = DeadlineBudget(total_seconds=None, per_stage_seconds=10.0)
    assert budget.stage_timed_out(time.monotonic()) is False
