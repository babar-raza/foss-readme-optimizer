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


def test_github_cannot_lock_ref_expected_value_is_a_stale_cas():
    stderr = (
        "remote: error: cannot lock ref "
        "'refs/readme-agent-state/org__repo': is at "
        f"{'a' * 40} but expected {'b' * 40}"
    )

    assert git_backend._is_non_fast_forward(stderr)


def test_load_many_uses_one_bulk_fetch_and_cleans_all_isolated_refs(monkeypatch):
    calls: list[tuple[list[str], str | None]] = []
    first_sha = "a" * 40
    second_sha = "b" * 40

    def fake_run_git(args: list[str], input_text: str | None = None, **_kwargs):
        calls.append((args, input_text))
        if args[0] == "ls-remote":
            return _completed(
                stdout=(
                    f"{first_sha}\trefs/readme-agent-state/org__first\n"
                    f"{second_sha}\trefs/readme-agent-state/org__second\n"
                )
            )
        if args[0] == "fetch":
            return _completed()
        if args[0] == "for-each-ref":
            prefix = args[-1]
            return _completed(stdout=(f"{prefix}/0 {first_sha}\n{prefix}/1 {second_sha}\n"))
        return _completed()

    payloads = {
        first_sha: ('{"schema_version": 2, "org_repo": "org/first", "state_version": 1}'),
        second_sha: ('{"schema_version": 2, "org_repo": "org/second", "state_version": 2}'),
    }
    monkeypatch.setattr(git_backend, "run_git", fake_run_git)
    monkeypatch.setattr(
        git_backend,
        "_read_blob",
        lambda sha, _path: payloads[sha],
    )

    loaded = git_backend.GitStateBackend().load_many(["org/first", "org/second", "org/missing"])

    assert loaded["org/first"] is not None
    assert loaded["org/first"].state_version == 1
    assert loaded["org/second"] is not None
    assert loaded["org/second"].state_version == 2
    assert loaded["org/missing"] is None
    assert sum(call[0][0] == "ls-remote" for call in calls) == 1
    assert sum(call[0][0] == "fetch" for call in calls) == 1
    fetch_args = next(call[0] for call in calls if call[0][0] == "fetch")
    assert any("refs/readme-agent-state/org__first" in argument for argument in fetch_args)
    assert any("refs/readme-agent-state/org__second" in argument for argument in fetch_args)
    assert not any("org__missing" in argument for argument in fetch_args)
    cleanup_args, cleanup_input = calls[-1]
    assert cleanup_args == ["update-ref", "--stdin"]
    assert cleanup_input is not None
    assert cleanup_input.count("delete ") == 2


def test_load_many_preserves_exact_remote_case_on_case_insensitive_filesystems(monkeypatch):
    calls: list[tuple[list[str], str | None]] = []
    exact_sha = "a" * 40
    legacy_sha = "b" * 40

    def fake_run_git(args: list[str], input_text: str | None = None, **_kwargs):
        calls.append((args, input_text))
        if args[0] == "ls-remote":
            return _completed(
                stdout=(
                    f"{exact_sha}\trefs/readme-agent-state/org__Product-for-Go\n"
                    f"{legacy_sha}\trefs/readme-agent-state/org__product-for-go\n"
                )
            )
        if args[0] == "fetch":
            return _completed()
        if args[0] == "for-each-ref":
            prefix = args[-1]
            return _completed(stdout=f"{prefix}/0 {exact_sha}\n")
        return _completed()

    payloads = {
        exact_sha: ('{"schema_version": 2, "org_repo": "org/Product-for-Go", "state_version": 7}'),
        legacy_sha: ('{"schema_version": 2, "org_repo": "org/product-for-go", "state_version": 2}'),
    }
    monkeypatch.setattr(git_backend, "run_git", fake_run_git)
    monkeypatch.setattr(git_backend, "_read_blob", lambda sha, _path: payloads[sha])

    loaded = git_backend.GitStateBackend().load_many(["org/Product-for-Go"])

    assert loaded["org/Product-for-Go"] is not None
    assert loaded["org/Product-for-Go"].state_version == 7
    fetch_args = next(call[0] for call in calls if call[0][0] == "fetch")
    assert any("org__Product-for-Go" in argument for argument in fetch_args)
    assert not any("org__product-for-go" in argument for argument in fetch_args)
