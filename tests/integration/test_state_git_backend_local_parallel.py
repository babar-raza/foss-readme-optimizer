"""Real multiprocess proof for isolated local state-Git plumbing workspaces."""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.state.git_backend import GitStateBackend
from readme_agent.state.schema import RunStateV1


def _state_worker(remote: str, org_repo: str) -> tuple[str, int, bool, bool]:
    backend = GitStateBackend(remote=remote)
    current = backend.load(org_repo)
    assert current is not None
    version = current.state_version
    for _attempt in range(3):
        result = backend.save(
            org_repo,
            RunStateV1(org_repo=org_repo, accepted_status="GENERATED"),
            expected_version=version,
        )
        assert result.outcome == "saved"
        assert result.new_version is not None
        version = result.new_version
    lock = backend.acquire_lock(org_repo)
    assert lock is not None
    backend.release_lock(lock)
    loaded = backend.load(org_repo)
    assert loaded is not None
    bare = run_git(["rev-parse", "--is-bare-repository"], cwd=backend._git_cwd)
    workspace_root = backend._git_cwd.parent
    backend.close()
    return (
        org_repo,
        loaded.state_version,
        bare.stdout.strip() == "true",
        not workspace_root.exists(),
    )


def _cas_worker(remote: str, org_repo: str, expected_version: int) -> str:
    with GitStateBackend(remote=remote) as backend:
        return backend.save(
            org_repo,
            RunStateV1(org_repo=org_repo, accepted_status="GENERATED"),
            expected_version=expected_version,
        ).outcome


def _local_fetch_refs() -> list[str]:
    listed = run_git(["for-each-ref", "--format=%(refname)", "refs/readme-agent-fetch"])
    assert listed.returncode == 0
    return listed.stdout.splitlines()


def test_three_processes_use_isolated_plumbing_while_remote_refs_are_packed(tmp_path: Path):
    remote = tmp_path / "state.git"
    initialized = run_git(["init", "--bare", str(remote)], cwd=tmp_path)
    assert initialized.returncode == 0
    repositories = [f"fixture/parallel-{index}" for index in range(3)]
    with GitStateBackend(remote=str(remote)) as seed:
        for org_repo in repositories:
            saved = seed.save(
                org_repo,
                RunStateV1(org_repo=org_repo, accepted_status="GENERATED"),
                expected_version=None,
            )
            assert saved.outcome == "saved"
    packed = run_git(["pack-refs", "--all"], cwd=remote)
    assert packed.returncode == 0
    control_refs_before = _local_fetch_refs()

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=3, mp_context=context) as pool:
        results = list(pool.map(_state_worker, [str(remote)] * 3, repositories))

    assert sorted(results) == sorted((org_repo, 4, True, True) for org_repo in repositories)
    assert _local_fetch_refs() == control_refs_before
    with GitStateBackend(remote=str(remote)) as verifier:
        loaded = verifier.load_many(repositories)
        assert all(state is not None and state.state_version == 4 for state in loaded.values())


def test_separate_process_workspaces_preserve_same_ref_cas(tmp_path: Path):
    remote = tmp_path / "state.git"
    initialized = run_git(["init", "--bare", str(remote)], cwd=tmp_path)
    assert initialized.returncode == 0
    org_repo = "fixture/same-ref-cas"
    with GitStateBackend(remote=str(remote)) as seed:
        saved = seed.save(
            org_repo,
            RunStateV1(org_repo=org_repo, accepted_status="GENERATED"),
            expected_version=None,
        )
        assert saved.new_version == 1

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=2, mp_context=context) as pool:
        outcomes = list(
            pool.map(
                _cas_worker,
                [str(remote), str(remote)],
                [org_repo, org_repo],
                [1, 1],
            )
        )

    assert sorted(outcomes) == ["saved", "stale"]
    with GitStateBackend(remote=str(remote)) as verifier:
        loaded = verifier.load(org_repo)
        assert loaded is not None
        assert loaded.state_version == 2
