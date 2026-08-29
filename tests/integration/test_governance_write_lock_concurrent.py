"""Real multiprocess proof that Phase 2 governance-write-lock enforcement
mechanically blocks a genuine peer, not just logs it -- the concurrent-process
integration test the plan enabling it required before considering it proven."""

from __future__ import annotations

import multiprocessing
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from readme_agent.gitsafety._git import run_git
from scripts.governance import validate_governance_write_lock as gate


def _init_worktree(root: Path) -> Path:
    """A real, separate git directory stands in for one session's own
    worktree -- distinct `.git` per simulated session, exactly like two real
    worktrees of one clone never share `_worktree_git_dir()`'s resolution."""

    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _run_session(remote: str, worktree: str, protected_path: str) -> int:
    import os

    os.environ[gate.ENFORCE_ENV_VAR] = "1"
    gate.staged_files = lambda: [protected_path]  # type: ignore[method-assign]
    from readme_agent.state.git_backend import GitStateBackend

    original_backend = GitStateBackend
    gate_module_backend = original_backend

    class _BoundBackend(gate_module_backend):  # type: ignore[misc, valid-type]
        def __init__(self) -> None:
            super().__init__(remote=remote)

    import readme_agent.state.git_backend as git_backend_module

    git_backend_module.GitStateBackend = _BoundBackend  # type: ignore[misc]
    try:
        return gate.main(Path(worktree))
    finally:
        git_backend_module.GitStateBackend = original_backend  # type: ignore[misc]


def test_a_second_real_session_is_mechanically_blocked_by_the_first(tmp_path: Path):
    remote = tmp_path / "state.git"
    initialized = run_git(["init", "--bare", str(remote)], cwd=tmp_path)
    assert initialized.returncode == 0

    worktree_a = _init_worktree(tmp_path / "session-a")
    worktree_b = _init_worktree(tmp_path / "session-b")

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        # Session A acquires first and completes -- its own local record of
        # the holder it acquired lives only in worktree_a.
        exit_a = pool.submit(_run_session, str(remote), str(worktree_a), "plans/master.md").result()
    assert exit_a == 0

    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        # Session B has never seen this lock -- its own local record (in
        # worktree_b) is empty, so the still-active lock A just took is a
        # genuine peer, and must mechanically block, not just warn.
        exit_b = pool.submit(_run_session, str(remote), str(worktree_b), "plans/master.md").result()
    assert exit_b == 1


def test_the_same_session_reacquiring_is_never_blocked_by_its_own_lock(tmp_path: Path):
    remote = tmp_path / "state.git"
    initialized = run_git(["init", "--bare", str(remote)], cwd=tmp_path)
    assert initialized.returncode == 0
    worktree = _init_worktree(tmp_path / "session-a")

    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        first = pool.submit(_run_session, str(remote), str(worktree), "plans/master.md").result()
    assert first == 0

    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        # Same worktree (same local holder record) checking again while its
        # own lease is still active must never block itself.
        second = pool.submit(_run_session, str(remote), str(worktree), "plans/master.md").result()
    assert second == 0
