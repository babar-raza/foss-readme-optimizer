"""Isolated durable-state fetch-ref behavior under concurrent readers."""

from __future__ import annotations

import subprocess

import pytest

from readme_agent.errors import StateBackendError
from readme_agent.state import git_backend


def _completed(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_fetch_remote_sha_uses_and_cleans_an_isolated_ref(monkeypatch):
    calls: list[list[str]] = []
    fetched_sha = "a" * 40

    def fake_run_git(args: list[str]):
        calls.append(args)
        if args[0] == "fetch":
            return _completed()
        if args[0] == "rev-parse":
            return _completed(stdout=f"{fetched_sha}\n")
        return _completed()

    monkeypatch.setattr(git_backend, "run_git", fake_run_git)

    assert git_backend._fetch_remote_sha("refs/readme-agent-state/example") == fetched_sha
    fetch_refspec = calls[0][-1]
    local_ref = fetch_refspec.split(":", 1)[1]
    assert calls[0][:4] == ["fetch", "--no-write-fetch-head", "origin", fetch_refspec]
    assert local_ref.startswith("refs/readme-agent-fetch/")
    assert calls[1] == ["rev-parse", "--verify", local_ref]
    assert calls[2] == ["update-ref", "-d", local_ref]
    assert all("FETCH_HEAD" not in argument for call in calls for argument in call)


def test_fetch_remote_sha_preserves_missing_remote_semantics(monkeypatch):
    calls: list[list[str]] = []

    def fake_run_git(args: list[str]):
        calls.append(args)
        return _completed(returncode=128, stderr="fatal: couldn't find remote ref missing")

    monkeypatch.setattr(git_backend, "run_git", fake_run_git)

    assert git_backend._fetch_remote_sha("refs/readme-agent-state/missing") is None
    assert len(calls) == 1


def test_fetch_remote_sha_cleans_ref_when_resolution_fails(monkeypatch):
    calls: list[list[str]] = []

    def fake_run_git(args: list[str]):
        calls.append(args)
        if args[0] == "rev-parse":
            return _completed(returncode=128, stderr="missing object")
        return _completed()

    monkeypatch.setattr(git_backend, "run_git", fake_run_git)

    with pytest.raises(StateBackendError, match="isolated fetch ref"):
        git_backend._fetch_remote_sha("refs/readme-agent-state/example")
    assert calls[-1][0:2] == ["update-ref", "-d"]
