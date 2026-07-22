"""Baseline (read-only reference) and work (mutable, disposable) clones.

Only read-only git verbs (clone, fetch) are ever issued against a real remote
here -- push is neutered separately in neuter.py before any write is possible.
"""

import os
import shutil
import stat
import time
from pathlib import Path

from readme_agent import env
from readme_agent.errors import GitSafetyError
from readme_agent.gitsafety._git import run_git
from readme_agent.registry.models import ProductEntry

# SCL-009 (2026-07-22): a single `supervise` run dispatches clone_baseline()
# from ~7-9 independent, stateless capabilities with no shared per-run repo
# view (decision #26(b)) -- without memoization, the identical repo was
# re-cloned over the network roughly 9-17 times per run, each an independent
# roll against SCL-004's own measured 158s-1004s clone-time variance for the
# SAME real repo.
#
# Keyed by baseline_path -> the SHA that's currently checked out there (NOT
# by clone_url/process lifetime, and NOT invalidated by a caller-remembered
# call before each "logical run"). An earlier version of this cache trusted
# the memo for an entire process's lifetime, relying on callers like
# `supervise_repo()` to explicitly invalidate before their own top-level
# clone -- found live to be the wrong invariant: "one run" in this codebase
# is not "one process," it's one call to ANY top-level entry point
# (`supervise_repo()`, each specialist's own `run()`, `orchestrator.py`'s
# `inspect_repo()`/`generate_repo()`, ...), and this project's own tests
# call several of those more than once per process to exercise
# consecutive-run semantics -- an invalidate-at-every-entry-point design
# requires finding and touching every one (two were found broken by exactly
# this before this cache was corrected: `test_supervisor_loop.py`'s and
# `test_specialists.py`'s own consecutive-run tests). Validating via a cheap
# `remote_head_sha()` probe (a `git ls-remote`, already this project's own
# decision #40/ORC-006 freshness-probe pattern) instead makes every caller
# correct automatically, with zero invalidation bookkeeping anywhere: reuse
# only costs ~1-15s (one ls-remote) instead of zero, but that is a small,
# honest price for never needing to reason about entry-point coverage again.
_baseline_clone_memo: dict[Path, str] = {}

# Bounded retry, distinct from the HTTP `_MAX_RETRIES`/`_BACKOFF_SECONDS`
# convention used elsewhwere (llm/*_client.py, github_api/client.py,
# registry/discovery.py) -- clone attempts are minutes-scale, not
# milliseconds, so the backoff is seconds, not milliseconds, and only a
# transient failure is retried at all; a real error (repo not found, auth
# failure) fails fast rather than wasting 2x the time before failing anyway.
_CLONE_RETRY_BACKOFF_SECONDS = [5, 15]
_MAX_CLONE_ATTEMPTS = 1 + len(_CLONE_RETRY_BACKOFF_SECONDS)

_TRANSIENT_CLONE_STDERR_MARKERS = (
    "Connection reset",
    "Connection timed out",
    "Connection refused",
    "Could not resolve host",
    "The remote end hung up unexpectedly",
    "early EOF",
    "unexpected disconnect",
    "RPC failed",
    "Recv failure",
    "Empty reply from server",
)


def reset_clone_memo() -> None:
    """Test-only convenience (a blunter, cheaper-to-call alternative to
    monkeypatching `remote_head_sha` for a test that just wants to force a
    real re-clone). Production code never needs this: a new process starts
    with an empty memo, and every existing entry is independently
    self-validating anyway (see `_baseline_clone_memo`'s own docstring)."""
    _baseline_clone_memo.clear()


def _is_transient_clone_failure(result) -> bool:
    """returncode 124 is run_git()'s own synthetic timeout marker (_git.py)
    -- always worth a fresh attempt, since SCL-004 measured wide clone-time
    variance for the identical repo across separate real attempts. Anything
    else is retried only for known-transient network stderr text."""
    if result.returncode == 124:
        return True
    return any(marker in result.stderr for marker in _TRANSIENT_CLONE_STDERR_MARKERS)


def force_rmtree(path: Path) -> None:
    """git writes objects read-only; plain shutil.rmtree chokes on that on
    Windows. Clear the read-only bit on access-denied and retry. Public (not
    module-private) since `orchestrator.py::run_registry()` reuses this same
    primitive for post-profile baseline cleanup (decision #40/Part B) rather
    than a fourth duplicate of this exact function. Caller must check
    `path.exists()` first -- `shutil.rmtree` raises if the top-level path is
    already gone, and that's a normal, expected case for callers here."""

    def _on_error(func, target_path, exc_info):
        os.chmod(target_path, stat.S_IWRITE)
        func(target_path)

    shutil.rmtree(path, onerror=_on_error)


def _local_head_sha(repo_path: Path) -> str | None:
    result = run_git(["rev-parse", "HEAD"], cwd=repo_path, timeout=10)
    return result.stdout.strip() if result.returncode == 0 else None


def clone_baseline(entry: ProductEntry, baseline_path: Path) -> Path:
    """Read-only reference clone, memoized against a cheap freshness probe
    rather than blind process-lifetime trust: if this path already holds a
    clone and a `remote_head_sha()` check (a `git ls-remote`, ~1-15s) still
    matches the SHA that was checked out, reuse it instead of paying a full
    `--depth 1` clone again. See `_baseline_clone_memo`'s own module
    docstring for the redundancy this eliminates and why probe-validated
    reuse, not caller-remembered invalidation, is the correct design. A
    failed probe (unreachable remote, timeout) is treated the same as a
    stale one -- "clone anyway" is always the safe fallback."""
    memoized_sha = _baseline_clone_memo.get(baseline_path)
    if memoized_sha is not None and baseline_path.is_dir() and any(baseline_path.iterdir()):
        probed_sha = remote_head_sha(entry.clone_url)
        if probed_sha is not None and probed_sha == memoized_sha:
            return baseline_path

    if baseline_path.exists():
        force_rmtree(baseline_path)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    timeout = env.git_clone_timeout_seconds()
    last_result = None
    for attempt in range(_MAX_CLONE_ATTEMPTS):
        # No explicit --branch: --depth 1 alone clones the HEAD of the remote's
        # default branch, which is exactly what we want without needing a
        # separate preflight lookup baked into the clone call itself.
        result = run_git(
            ["clone", "--depth", "1", entry.clone_url, str(baseline_path)],
            timeout=timeout,
        )
        if result.returncode == 0:
            # A None SHA (rev-parse somehow failing right after a successful
            # clone -- not expected, but not impossible) must not be trusted
            # as a memo entry: drop any stale one instead, so the NEXT call
            # always re-clones rather than risk comparing against a SHA that
            # was never real.
            sha = _local_head_sha(baseline_path)
            if sha is not None:
                _baseline_clone_memo[baseline_path] = sha
            else:
                _baseline_clone_memo.pop(baseline_path, None)
            return baseline_path
        last_result = result
        if attempt < _MAX_CLONE_ATTEMPTS - 1 and _is_transient_clone_failure(result):
            time.sleep(_CLONE_RETRY_BACKOFF_SECONDS[attempt])
            if baseline_path.exists():
                force_rmtree(baseline_path)
            continue
        break

    # _MAX_CLONE_ATTEMPTS is 1 + len(_CLONE_RETRY_BACKOFF_SECONDS) >= 1, so the loop
    # above always runs at least once and last_result is never actually None here --
    # mypy can't prove range()'s non-emptiness statically.
    assert last_result is not None
    raise GitSafetyError(f"baseline clone of {entry.org_repo} failed: {last_result.stderr}")


_COMMIT_AUTHOR_NAME = "readme-agent"
_COMMIT_AUTHOR_EMAIL = "readme-agent@users.noreply.github.com"


def create_work_clone(entry: ProductEntry, baseline_path: Path, work_path: Path) -> Path:
    """Fast local-to-local clone from the baseline, then origin is restored to
    the real GitHub URL for realism/evidence (cloning from a local baseline
    path would otherwise leave `origin` pointing at a local path).

    Also sets a `--local` git identity on the work clone itself (never
    `--global` -- this must never touch the actual runner's/developer's own
    git configuration). Found during an external-review triage (2026-07-21):
    neither shipped CI workflow (`readme-agent-run.yml`/`readme-agent-
    supervise.yml`) configures `user.name`/`user.email` anywhere, and every
    real-commit proof recorded in this project's history so far ran either on
    a locally-configured dev machine or via local `act` emulation -- never
    confirmed against a genuinely fresh, hosted GitHub Actions runner, which
    has no default git identity. Without this, `commit_generated_readme()`/
    `commit_readme_write` would very likely fail there with a real commit
    attempt, on every run, since git refuses to commit with no identity
    configured anywhere in scope."""
    if work_path.exists():
        force_rmtree(work_path)
    work_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_git(
        ["clone", "--no-tags", str(baseline_path), str(work_path)],
        timeout=120,
    )
    if result.returncode != 0:
        raise GitSafetyError(f"work clone of {entry.org_repo} failed: {result.stderr}")

    result = run_git(["remote", "set-url", "origin", entry.repo_url + ".git"], cwd=work_path)
    if result.returncode != 0:
        raise GitSafetyError(f"restoring origin URL for {entry.org_repo} failed: {result.stderr}")

    for key, value in (("user.name", _COMMIT_AUTHOR_NAME), ("user.email", _COMMIT_AUTHOR_EMAIL)):
        result = run_git(["config", "--local", key, value], cwd=work_path)
        if result.returncode != 0:
            raise GitSafetyError(
                f"setting local git identity ({key}) for {entry.org_repo} failed: {result.stderr}"
            )

    return work_path


def create_pr_clone(entry: ProductEntry, baseline_path: Path, pr_work_path: Path) -> Path:
    """TC-08/`PRL-007`: the one clone in this codebase that is deliberately
    NEVER neutered -- structurally separate from `create_work_clone()`
    (a different root, `paths.pr_work_dir()`, never `paths.work_dir()`) so
    the `remote_write` capability that uses it can never be confused with,
    or substituted for, any capability that assumes `verify_push_blocked()`
    would pass on its own clone. This function itself does not push
    anything -- it only clones and sets a local git identity, exactly like
    `create_work_clone()`'s own first two steps. The actual authenticated
    push happens in `push_branch()` below, called separately by the one
    capability permitted to use this path."""
    if pr_work_path.exists():
        force_rmtree(pr_work_path)
    pr_work_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_git(
        ["clone", "--no-tags", str(baseline_path), str(pr_work_path)],
        timeout=120,
    )
    if result.returncode != 0:
        raise GitSafetyError(f"pr clone of {entry.org_repo} failed: {result.stderr}")

    result = run_git(["remote", "set-url", "origin", entry.repo_url + ".git"], cwd=pr_work_path)
    if result.returncode != 0:
        raise GitSafetyError(f"restoring origin URL for {entry.org_repo} failed: {result.stderr}")

    for key, value in (("user.name", _COMMIT_AUTHOR_NAME), ("user.email", _COMMIT_AUTHOR_EMAIL)):
        result = run_git(["config", "--local", key, value], cwd=pr_work_path)
        if result.returncode != 0:
            raise GitSafetyError(
                f"setting local git identity ({key}) for {entry.org_repo} failed: {result.stderr}"
            )

    return pr_work_path


def push_branch(repo_path: Path, branch_name: str, token: str, *, timeout: float = 60):
    """The one function in this codebase that performs a real, authenticated
    push. The token travels via a per-invocation `http.extraheader` --
    scoped to this single `run_git()` call only, never written to the
    remote URL (which would leak it into `git remote -v`/evidence output)
    and never merged into `_git.py::GIT_SAFETY_ENV` (that only ever adds
    `GIT_TERMINAL_PROMPT=0`, already composed in by `run_git()` itself for
    every call, including this one -- a hung credential prompt here fails
    fast exactly like every other `run_git()` call site). Pushes `HEAD` to
    `branch_name` explicitly rather than relying on any configured upstream,
    since `repo_path` never has one for a not-yet-existing remote branch."""
    return run_git(
        [
            "-c",
            f"http.extraheader=AUTHORIZATION: bearer {token}",
            "push",
            "origin",
            f"HEAD:refs/heads/{branch_name}",
        ],
        cwd=repo_path,
        timeout=timeout,
    )


def remote_head_sha(clone_url: str, timeout: float = 15) -> str | None:
    """Cheap freshness probe (decision #40/Part B): `git ls-remote` reports
    the remote's default-branch HEAD commit SHA without cloning anything --
    one tiny network round-trip, not the ~1GB+ transfer `clone_baseline()`
    can cost on a large registry repo. `None` on any failure (unreachable
    remote, timeout, unexpected output) -- callers must treat that as "no
    freshness signal available," never as a cache-invalidation error, since
    this is an optimization, not a correctness dependency: falling back to a
    real clone is always safe."""
    try:
        result = run_git(["ls-remote", clone_url, "HEAD"], timeout=timeout)
    except Exception:  # noqa: BLE001 -- a failed probe just means "clone anyway"
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    first_line = result.stdout.strip().splitlines()[0]
    sha = first_line.split()[0] if first_line.split() else ""
    return sha or None


def diff_changed_paths(baseline_path: Path, from_sha: str, to_sha: str) -> list[str] | None:
    """Wave 8.6 (`ORC-003` reversal, `supervisor/specialist_selection.py`):
    which paths changed between two revisions, against a `clone_baseline()`
    clone that is `--depth 1` (zero retained history) -- `from_sha` almost
    never being locally present. `git fetch --depth 1 origin <from_sha>`
    fetches exactly that one historical commit's tree (GitHub.com supports
    fetching an arbitrary reachable commit by SHA for public repos) without a
    full unshallow; a two-dot `git diff <a> <b>` only needs both commits'
    trees present locally, not a connected history/merge-base, so this works
    even though `to_sha` and the newly-fetched `from_sha` came from two
    disjoint shallow operations.

    Fails closed by construction: any failure (unreachable/rewritten
    history, unsupported remote, network hiccup) returns `None`, never an
    empty list -- callers MUST treat `None` as "cannot determine, assume
    changed," never as a false "nothing changed." The worst case of this
    mechanism failing entirely is identical to not having built it at all
    (always falls through to a real run) -- it can never itself cause a
    false skip."""
    if from_sha == to_sha:
        return []
    try:
        fetch = run_git(
            ["fetch", "--depth", "1", "origin", from_sha], cwd=baseline_path, timeout=60
        )
    except Exception:  # noqa: BLE001 -- any failure here just means "cannot determine"
        return None
    if fetch.returncode != 0:
        return None
    try:
        diff = run_git(["diff", "--name-only", from_sha, to_sha], cwd=baseline_path, timeout=30)
    except Exception:  # noqa: BLE001
        return None
    if diff.returncode != 0:
        return None
    return [line for line in diff.stdout.splitlines() if line.strip()]


def toplevel_matches(repo_path: Path) -> bool:
    """Safety guard adapted from aspose.org's clone_cache.py: before any
    destructive operation, confirm git will actually operate on repo_path and
    not a parent/wrong repo."""
    result = run_git(["rev-parse", "--show-toplevel"], cwd=repo_path, timeout=5)
    if result.returncode != 0:
        return False
    resolved = Path(result.stdout.strip()).resolve()
    return resolved == repo_path.resolve()
