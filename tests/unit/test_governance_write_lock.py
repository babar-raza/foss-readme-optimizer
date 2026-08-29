"""GitStateBackend's third lock family (governance-write), used to leave a
short-lived, self-expiring trace of "a governance write happened here" for a
concurrent agent's own commit-time check to observe -- see
scripts/governance/validate_governance_write_lock.py."""

from __future__ import annotations

from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.state import git_backend
from readme_agent.state.git_backend import GitStateBackend


def _bare_remote(tmp_path: Path) -> str:
    remote = tmp_path / "state.git"
    initialized = run_git(["init", "--bare", str(remote)], cwd=tmp_path)
    assert initialized.returncode == 0
    return str(remote)


def test_acquire_governance_lock_succeeds_when_free(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path)
    with GitStateBackend(remote=remote) as backend:
        lock = backend.acquire_governance_lock("shared-governance-write")
        assert lock is not None
        assert lock.org_repo == "shared-governance-write"
        assert lock.holder_id


def test_acquire_governance_lock_fails_while_another_holder_is_unexpired(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path)
    with GitStateBackend(remote=remote) as first, GitStateBackend(remote=remote) as second:
        held = first.acquire_governance_lock("shared-governance-write")
        assert held is not None
        contended = second.acquire_governance_lock("shared-governance-write")
        assert contended is None


def test_peek_governance_lock_returns_holder_details_without_acquiring(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path)
    with GitStateBackend(remote=remote) as first, GitStateBackend(remote=remote) as second:
        held = first.acquire_governance_lock("shared-governance-write")
        assert held is not None

        peeked = second.peek_governance_lock("shared-governance-write")
        assert peeked is not None
        assert peeked["holder_id"] == held.holder_id
        assert peeked["leased_until"] == held.leased_until

        # peeking never acquires -- a second acquire attempt still sees it held
        assert second.acquire_governance_lock("shared-governance-write") is None


def test_peek_governance_lock_is_none_when_absent(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path)
    with GitStateBackend(remote=remote) as backend:
        assert backend.peek_governance_lock("shared-governance-write") is None


def test_acquire_governance_lock_succeeds_after_lease_expires(tmp_path: Path, monkeypatch) -> None:
    remote = _bare_remote(tmp_path)
    monkeypatch.setattr(git_backend, "GOVERNANCE_LOCK_LEASE_SECONDS", 0)
    with GitStateBackend(remote=remote) as first, GitStateBackend(remote=remote) as second:
        held = first.acquire_governance_lock("shared-governance-write")
        assert held is not None
        reclaimed = second.acquire_governance_lock("shared-governance-write")
        assert reclaimed is not None
        assert reclaimed.holder_id != held.holder_id


def test_release_governance_lock_then_peek_shows_absent(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path)
    with GitStateBackend(remote=remote) as backend:
        lock = backend.acquire_governance_lock("shared-governance-write")
        assert lock is not None
        backend.release_governance_lock(lock)
        assert backend.peek_governance_lock("shared-governance-write") is None


def test_governance_lock_is_a_distinct_family_from_run_and_write_locks(tmp_path: Path) -> None:
    remote = _bare_remote(tmp_path)
    key = "same-key-different-family"
    with GitStateBackend(remote=remote) as backend:
        write_lock = backend.acquire_lock(key)
        run_lock = backend.acquire_run_lock(key)
        governance_lock = backend.acquire_governance_lock(key)
        assert write_lock is not None
        assert run_lock is not None
        assert governance_lock is not None
