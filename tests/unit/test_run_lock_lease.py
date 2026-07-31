"""Run-lock renewal and fencing."""

from __future__ import annotations

from time import monotonic, sleep

import pytest

from readme_agent.errors import StateBackendError
from readme_agent.state.run_lock_lease import RunLockLeaseGuard
from tests.unit.test_state_backend import FakeStateBackend


def test_guard_renews_same_holder_and_stops_cleanly() -> None:
    backend = FakeStateBackend()
    acquired = backend.acquire_run_lock("org/repo")
    assert acquired is not None
    initial_expiry = acquired.leased_until

    with RunLockLeaseGuard(backend, acquired, renew_interval_seconds=0.01) as guard:
        deadline = monotonic() + 1
        while guard.lock.leased_until == initial_expiry and monotonic() < deadline:
            sleep(0.005)
        guard.assert_held()

    assert guard.lock.holder_id == acquired.holder_id
    assert guard.lock.leased_until != initial_expiry


def test_guard_fails_closed_after_another_holder_replaces_the_lease() -> None:
    backend = FakeStateBackend()
    acquired = backend.acquire_run_lock("org/repo")
    assert acquired is not None

    with RunLockLeaseGuard(backend, acquired, renew_interval_seconds=60) as guard:
        backend._run_locks["org/repo"] = ("other-holder", backend._run_locks["org/repo"][1])
        with pytest.raises(StateBackendError, match="ownership was lost"):
            guard.assert_held()
