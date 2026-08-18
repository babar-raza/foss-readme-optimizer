"""Prove rapid local POC state remains durable without writing control-remote refs."""

from pathlib import Path

from readme_agent.state.local_poc_backend import (
    default_local_poc_state_backend,
    local_poc_state_remote,
)


def test_local_poc_state_remote_initializes_one_bare_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("README_AGENT_STATE_REMOTE", raising=False)

    first = Path(local_poc_state_remote())
    second = Path(local_poc_state_remote())

    assert first == second
    assert first == (tmp_path / "runs" / "local-poc-state" / "state.git").resolve()
    assert (first / "HEAD").is_file()


def test_local_poc_state_remote_honors_explicit_override_without_initializing_local(
    tmp_path, monkeypatch
) -> None:
    override = tmp_path / "provided-state.git"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("README_AGENT_STATE_REMOTE", str(override))

    assert local_poc_state_remote() == str(override)
    assert not (tmp_path / "runs" / "local-poc-state").exists()


def test_default_local_poc_state_backend_never_targets_origin(tmp_path, monkeypatch) -> None:
    """2026-08-18: the concrete regression the state-backend-uses-origin-not-
    local evidence doc recommended -- proves every real git invocation a
    `local_poc` backend makes targets the isolated local bare remote, never
    this repository's own `origin` (`commands_supervision.py::
    _state_backend_for_profile` routes `local_poc` here specifically so it
    never depends on `git push`/`fetch` against the real remote)."""

    import readme_agent.state.git_backend as git_backend_module

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("README_AGENT_STATE_REMOTE", raising=False)

    calls: list[list[str]] = []
    real_run_git = git_backend_module.run_git

    def _spy_run_git(args, **kwargs):
        calls.append(args)
        return real_run_git(args, **kwargs)

    monkeypatch.setattr(git_backend_module, "run_git", _spy_run_git)

    backend = default_local_poc_state_backend()
    backend.load("org/repo")
    lock = backend.acquire_lock("org/repo")
    assert lock is not None
    backend.release_lock(lock)

    assert calls, "expected at least one real git invocation to prove the assertion is live"
    expected_remote = (tmp_path / "runs" / "local-poc-state" / "state.git").resolve()
    for args in calls:
        assert "origin" not in args, f"git invocation touched origin: {args}"
        if "push" in args or "fetch" in args:
            assert str(expected_remote) in args, (
                f"push/fetch did not target the isolated local remote: {args}"
            )
