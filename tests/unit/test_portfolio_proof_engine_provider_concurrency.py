"""Provider concurrency ceiling -- proves the gate never lets more than `max_concurrent` critical
sections run at once, under real thread contention (not just a single-threaded assertion)."""

from __future__ import annotations

import threading
import time

import pytest

from readme_agent.supervisor.portfolio_proof_engine.provider_concurrency import (
    ProviderConcurrencyGate,
    run_deterministic_fanout,
)


def test_gate_defaults_to_two():
    gate = ProviderConcurrencyGate()
    assert gate.max_concurrent == 2


def test_gate_never_exceeds_its_configured_max_under_contention():
    gate = ProviderConcurrencyGate(max_concurrent=2)
    workers = 8

    def _work():
        with gate.acquire():
            time.sleep(0.02)

    threads = [threading.Thread(target=_work) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert 1 <= gate.observed_max_concurrent <= 2


def test_gate_rejects_non_positive_max_concurrent():
    with pytest.raises(ValueError):
        ProviderConcurrencyGate(max_concurrent=0)


def test_run_deterministic_fanout_preserves_results_serial_and_parallel():
    assert run_deterministic_fanout([1, 2, 3], lambda x: x * 2, max_workers=1) == [2, 4, 6]
    assert sorted(run_deterministic_fanout([1, 2, 3], lambda x: x * 2, max_workers=4)) == [
        2,
        4,
        6,
    ]


def test_run_deterministic_fanout_empty_input():
    assert run_deterministic_fanout([], lambda x: x, max_workers=4) == []
