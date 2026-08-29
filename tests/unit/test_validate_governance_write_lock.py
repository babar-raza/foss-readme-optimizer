"""The pre-commit governance-write-lock gate: path matching, and that it never
blocks (Phase 1), never touches the network for an untouched tree, and degrades
cleanly when the backend is unavailable."""

from __future__ import annotations

import pytest

from scripts.governance import validate_governance_write_lock as gate


def test_no_staged_files_do_not_touch_protected_paths() -> None:
    assert gate.touches_protected_path([]) is False


def test_ordinary_code_paths_are_not_protected() -> None:
    staged = ["src/readme_agent/cli.py", "tests/unit/test_cli.py", "README.md"]
    assert gate.touches_protected_path(staged) is False


@pytest.mark.parametrize(
    "path",
    [
        "plans/master.md",
        "plans/requirements/catalog.jsonl",
        "logs/2026-08-28.md",
        "AGENTS.md",
        "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
    ],
)
def test_known_governance_paths_are_protected(path: str) -> None:
    assert gate.touches_protected_path([path]) is True


def test_a_protected_path_among_unrelated_ones_is_still_detected() -> None:
    staged = ["src/readme_agent/cli.py", "plans/master.md"]
    assert gate.touches_protected_path(staged) is True


class _FakeLock:
    def __init__(self, holder_id: str, leased_until: str) -> None:
        self.org_repo = "shared-governance-write"
        self.holder_id = holder_id
        self.leased_until = leased_until


class _FakeBackendFree:
    def __enter__(self) -> _FakeBackendFree:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        return None

    def acquire_governance_lock(self, key: str) -> _FakeLock:
        assert key == gate.GOVERNANCE_LOCK_KEY
        return _FakeLock("me", "2099-01-01T00:00:00+00:00")

    def peek_governance_lock(self, key: str) -> None:
        raise AssertionError("peek should not be called when acquisition succeeds")


class _FakeBackendHeld:
    def __enter__(self) -> _FakeBackendHeld:
        return self

    def __exit__(self, *_exc_info: object) -> None:
        return None

    def acquire_governance_lock(self, key: str) -> None:
        return None

    def peek_governance_lock(self, key: str) -> dict[str, str]:
        assert key == gate.GOVERNANCE_LOCK_KEY
        return {"holder_id": "peer-session", "leased_until": "2099-01-01T00:00:00+00:00"}


class _FakeBackendUnreachable:
    def __enter__(self) -> _FakeBackendUnreachable:
        raise ConnectionError("simulated network failure")

    def __exit__(self, *_exc_info: object) -> None:
        return None


def test_main_never_touches_backend_when_nothing_protected_is_staged(monkeypatch) -> None:
    monkeypatch.setattr(gate, "staged_files", lambda: ["src/readme_agent/cli.py"])

    def _fail_if_constructed(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("GitStateBackend must not be constructed for an untouched tree")

    monkeypatch.setattr("readme_agent.state.git_backend.GitStateBackend", _fail_if_constructed)
    assert gate.main() == 0


def test_main_acquires_and_returns_zero_when_lock_is_free(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "staged_files", lambda: ["plans/master.md"])
    monkeypatch.setattr(
        "readme_agent.state.git_backend.GitStateBackend", lambda *a, **k: _FakeBackendFree()
    )
    assert gate.main() == 0
    assert "acquired shared-governance-write presence" in capsys.readouterr().out


def test_main_warns_but_returns_zero_when_lock_is_held_by_a_peer(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "staged_files", lambda: ["logs/2026-08-28.md"])
    monkeypatch.setattr(
        "readme_agent.state.git_backend.GitStateBackend", lambda *a, **k: _FakeBackendHeld()
    )
    assert gate.main() == 0
    out = capsys.readouterr().out
    assert "peer-session" in out
    assert "Phase 1: advisory only" in out


def test_main_degrades_cleanly_when_backend_is_unreachable(monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate, "staged_files", lambda: ["plans/master.md"])
    monkeypatch.setattr(
        "readme_agent.state.git_backend.GitStateBackend",
        lambda *a, **k: _FakeBackendUnreachable(),
    )
    assert gate.main() == 0
    assert "skipped" in capsys.readouterr().err
