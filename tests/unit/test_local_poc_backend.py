"""Prove rapid local POC state remains durable without writing control-remote refs."""

from pathlib import Path

from readme_agent.state.local_poc_backend import local_poc_state_remote


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
