"""No network required -- everything here runs against local, disposable git repos."""

from pathlib import Path

import pytest

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import (
    clone_baseline,
    create_work_clone,
    diff_changed_paths,
    force_rmtree,
    remote_head_sha,
    reset_clone_memo,
    toplevel_matches,
)
from readme_agent.gitsafety.hooks import BLOCK_MARKER, install_pre_push_hook
from readme_agent.gitsafety.neuter import DISABLED_PUSH_URL, neuter_push
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.registry.models import ProductEntry


@pytest.fixture(autouse=True)
def _clean_clone_memo():
    """Every test gets a fresh in-process clone memo -- each test uses its
    own `tmp_path`-scoped baseline path anyway (no key collision risk), this
    just keeps the module-level dict from growing across a whole test
    session and keeps each test's intent explicit."""
    reset_clone_memo()
    yield
    reset_clone_memo()


def _init_repo(path: Path, with_commit: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)
    if with_commit:
        (path / "README.md").write_text("# test\n", encoding="utf-8")
        run_git(["add", "."], cwd=path)
        run_git(["commit", "-m", "initial"], cwd=path)
    return path


class TestNeuterAndVerify:
    def test_neuter_then_verify_ok(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        run_git(["remote", "add", "origin", "https://github.com/example/example.git"], cwd=repo)

        neuter_push(repo)
        install_pre_push_hook(repo)
        proof = verify_push_blocked(repo)

        assert proof.ok
        assert proof.push_url == DISABLED_PUSH_URL
        assert proof.fetch_url == "https://github.com/example/example.git"
        assert proof.hook_installed
        assert proof.hook_contains_marker

    def test_verify_fails_without_neutering(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        run_git(["remote", "add", "origin", "https://github.com/example/example.git"], cwd=repo)

        proof = verify_push_blocked(repo)

        assert not proof.ok
        assert proof.push_url != DISABLED_PUSH_URL

    def test_verify_fails_without_hook(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        run_git(["remote", "add", "origin", "https://github.com/example/example.git"], cwd=repo)
        neuter_push(repo)

        proof = verify_push_blocked(repo)

        assert not proof.ok
        assert not proof.hook_installed


class TestHookActuallyBlocksARealPush:
    """The automated version of the plan's 'manually confirm the hook blocks a
    real push' step -- a real git push against a real (local, disposable)
    remote, not a mock."""

    def test_pre_push_hook_blocks_real_push_attempt(self, tmp_path):
        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work = _init_repo(tmp_path / "work")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)
        install_pre_push_hook(work)

        result = run_git(["push", "origin", "main"], cwd=work)

        assert result.returncode != 0
        assert BLOCK_MARKER in result.stderr

    def test_without_the_hook_the_same_push_would_succeed(self, tmp_path):
        """Sanity check that the block is the hook, not some other accident of
        the test setup -- without it, the identical push succeeds."""
        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work = _init_repo(tmp_path / "work")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)

        result = run_git(["push", "origin", "main"], cwd=work)

        assert result.returncode == 0


class TestToplevelMatches:
    def test_true_for_the_repo_itself(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        assert toplevel_matches(repo)

    def test_false_for_a_path_that_is_not_a_repo(self, tmp_path):
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        assert not toplevel_matches(not_a_repo)


def _fake_entry(clone_url: str) -> ProductEntry:
    return ProductEntry(
        family="test",
        platform="java",
        repo_name="Example",
        repo_url="https://github.com/example-org/Example",
        clone_url=clone_url,
        active=True,
        discovered_via="manual",
        mode="dry_run",
        ecosystem="maven",
        policy_profile=None,
    )


class TestCloneBaselineAndWork:
    def test_clone_baseline_and_work_clone_from_local_source(self, tmp_path):
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))

        baseline_path = tmp_path / "baseline"
        clone_baseline(entry, baseline_path)
        assert (baseline_path / "README.md").exists()

        work_path = tmp_path / "work"
        create_work_clone(entry, baseline_path, work_path)
        assert (work_path / "README.md").exists()

        # origin is restored to the real GitHub URL, not the local baseline path
        remote = run_git(["remote", "get-url", "origin"], cwd=work_path)
        assert remote.stdout.strip() == entry.repo_url + ".git"

    def test_clone_baseline_is_re_cloned_fresh_across_runs(self, tmp_path):
        """SCL-004 extension (2026-07-22): `clone_baseline()` is now memoized
        WITHIN a process (see the sibling test below) -- this test asserts
        the property that must still hold ACROSS runs, i.e. across a new
        process (simulated here via `reset_clone_memo()`, exactly what a
        fresh CLI invocation or CI job always starts with)."""
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        reset_clone_memo()
        clone_baseline(entry, baseline_path)
        (baseline_path / "stray.txt").write_text("should not survive a re-clone", encoding="utf-8")

        reset_clone_memo()
        clone_baseline(entry, baseline_path)
        assert not (baseline_path / "stray.txt").exists()

    def test_clone_baseline_reuses_within_the_same_process(self, tmp_path):
        """The redesigned contract this sprint adds: a single `supervise` run
        dispatches clone_baseline() from ~7-9 independent capabilities with
        no shared repo view -- memoizing within one process turns that into
        one real clone instead of 7-9, without weakening the cross-run
        freshness guarantee the sibling test above still proves."""
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        reset_clone_memo()
        clone_baseline(entry, baseline_path)
        (baseline_path / "stray.txt").write_text("should survive a memoized call", encoding="utf-8")

        clone_baseline(entry, baseline_path)  # same process, no reset -- must reuse
        assert (baseline_path / "stray.txt").exists()

    def test_clone_baseline_memo_self_heals_if_directory_vanishes(self, tmp_path):
        """Defensive: if something external removed the memoized baseline
        directory mid-process (e.g. orchestrator.py's own `force_rmtree`
        reuse for post-profile cleanup), the memo must not lie about a
        directory that no longer exists."""
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        reset_clone_memo()
        clone_baseline(entry, baseline_path)
        # Plain shutil.rmtree chokes on git's read-only objects on Windows --
        # force_rmtree (this module's own helper) is what any real external
        # caller (e.g. orchestrator.py's post-profile cleanup reuse) would
        # actually call too.
        force_rmtree(baseline_path)

        clone_baseline(entry, baseline_path)
        assert (baseline_path / "README.md").exists()

    def test_a_real_upstream_commit_invalidates_the_memo_via_the_sha_probe(self, tmp_path):
        """The mechanism every caller relies on, with zero invalidation
        bookkeeping needed anywhere: a "run" is one call, not one process
        (this project's own tests call `clone_baseline()`'s various callers
        -- `supervise_repo()`, specialist `run()` functions -- more than
        once per process to test consecutive-run semantics), so the memo
        must not trust its own age; it must re-verify against a real
        `remote_head_sha()` probe every time. A genuine new commit on the
        "remote" between two calls, same process, no `reset_clone_memo()`,
        must produce a real re-clone."""
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        clone_baseline(entry, baseline_path)
        (source / "CHANGELOG.md").write_text("v2\n", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "v2"], cwd=source)

        # Same process, no reset_clone_memo() call -- the probe must still
        # detect the SHA moved and reclone rather than trust the stale memo.
        clone_baseline(entry, baseline_path)
        assert (baseline_path / "CHANGELOG.md").exists()

    def test_probe_failure_falls_back_to_a_real_clone_not_a_stale_reuse(
        self, tmp_path, monkeypatch
    ):
        """`remote_head_sha()` returning `None` (unreachable remote, timeout)
        must never be read as "unchanged" -- the safe default is always to
        reclone, matching this project's own "a failed probe just means
        clone anyway" convention (`remote_head_sha()`'s own docstring)."""
        from readme_agent.gitsafety import clone as clone_module

        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        clone_baseline(entry, baseline_path)
        (baseline_path / "stray.txt").write_text(
            "must not survive a failed-probe reclone", encoding="utf-8"
        )
        monkeypatch.setattr(clone_module, "remote_head_sha", lambda clone_url, timeout=15: None)

        clone_baseline(entry, baseline_path)
        assert not (baseline_path / "stray.txt").exists()


class TestCloneBaselineRetryAndTimeout:
    """Monkeypatches `clone.run_git` directly -- a real network timeout/
    transient failure can't be reproduced against a local disposable repo,
    so these test the retry/timeout decision logic in isolation from actual
    git subprocess behavior (already covered by `_git.py`'s own tests)."""

    def test_retries_once_on_synthetic_timeout_then_succeeds(self, monkeypatch, tmp_path):
        import subprocess

        from readme_agent.gitsafety import clone as clone_module

        entry = _fake_entry("https://example.invalid/does-not-matter.git")
        baseline_path = tmp_path / "baseline"
        calls = []
        sleeps = []

        def _fake_run_git(args, cwd=None, timeout=None, **kwargs):
            if args[0] == "rev-parse":
                # clone_baseline() reads the checked-out SHA right after a
                # successful clone, to seed the memo -- not the call under test.
                return subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="deadbeef", stderr=""
                )
            calls.append(timeout)
            if len(calls) == 1:
                return subprocess.CompletedProcess(
                    args=args, returncode=124, stdout="", stderr="git ... timed out after 600s"
                )
            baseline_path.mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(clone_module, "run_git", _fake_run_git)
        monkeypatch.setattr(clone_module.time, "sleep", lambda s: sleeps.append(s))

        result = clone_module.clone_baseline(entry, baseline_path)

        assert result == baseline_path
        assert len(calls) == 2
        assert sleeps == [clone_module._CLONE_RETRY_BACKOFF_SECONDS[0]]

    def test_does_not_retry_a_real_not_found_error(self, monkeypatch, tmp_path):
        import subprocess

        from readme_agent.errors import GitSafetyError
        from readme_agent.gitsafety import clone as clone_module

        entry = _fake_entry("https://example.invalid/does-not-matter.git")
        baseline_path = tmp_path / "baseline"
        calls = []

        def _fake_run_git(args, cwd=None, timeout=None, **kwargs):
            calls.append(1)
            return subprocess.CompletedProcess(
                args=args,
                returncode=128,
                stdout="",
                stderr="fatal: repository 'https://example.invalid/does-not-matter.git/' not found",
            )

        monkeypatch.setattr(clone_module, "run_git", _fake_run_git)
        monkeypatch.setattr(
            clone_module.time, "sleep", lambda s: pytest.fail("must not sleep/retry a real error")
        )

        with pytest.raises(GitSafetyError, match="not found"):
            clone_module.clone_baseline(entry, baseline_path)
        assert len(calls) == 1

    def test_gives_up_after_max_attempts_of_repeated_timeouts(self, monkeypatch, tmp_path):
        import subprocess

        from readme_agent.errors import GitSafetyError
        from readme_agent.gitsafety import clone as clone_module

        entry = _fake_entry("https://example.invalid/does-not-matter.git")
        baseline_path = tmp_path / "baseline"
        calls = []

        def _fake_run_git(args, cwd=None, timeout=None, **kwargs):
            calls.append(1)
            return subprocess.CompletedProcess(
                args=args, returncode=124, stdout="", stderr="timed out after 600s"
            )

        monkeypatch.setattr(clone_module, "run_git", _fake_run_git)
        monkeypatch.setattr(clone_module.time, "sleep", lambda s: None)

        with pytest.raises(GitSafetyError):
            clone_module.clone_baseline(entry, baseline_path)
        assert len(calls) == clone_module._MAX_CLONE_ATTEMPTS

    def test_timeout_is_read_from_the_env_var(self, monkeypatch, tmp_path):
        import subprocess

        from readme_agent.gitsafety import clone as clone_module

        monkeypatch.setenv("GIT_CLONE_TIMEOUT_SECONDS", "42")
        entry = _fake_entry("https://example.invalid/does-not-matter.git")
        baseline_path = tmp_path / "baseline"
        seen_timeouts = []

        def _fake_run_git(args, cwd=None, timeout=None, **kwargs):
            if args[0] == "rev-parse":
                return subprocess.CompletedProcess(
                    args=args, returncode=0, stdout="deadbeef", stderr=""
                )
            seen_timeouts.append(timeout)
            baseline_path.mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        monkeypatch.setattr(clone_module, "run_git", _fake_run_git)
        clone_module.clone_baseline(entry, baseline_path)

        assert seen_timeouts == [42.0]


class TestWorkCloneGitIdentity:
    """External-review triage (2026-07-21): neither shipped CI workflow
    configures a git commit identity anywhere, and every prior real-commit
    proof in this project's history ran on a machine that already had one
    set globally -- never confirmed against a genuinely fresh, hosted runner.
    Proves `create_work_clone()`'s own `--local` identity is sufficient on
    its own, with zero ambient global/system git config visible at all."""

    def test_real_commit_succeeds_with_no_ambient_git_identity(self, tmp_path):
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))

        baseline_path = tmp_path / "baseline"
        clone_baseline(entry, baseline_path)
        work_path = tmp_path / "work"
        create_work_clone(entry, baseline_path, work_path)

        fake_home = tmp_path / "fake-home-no-gitconfig"
        fake_home.mkdir()
        no_ambient_identity_env = {
            "HOME": str(fake_home),
            "USERPROFILE": str(fake_home),
            "GIT_CONFIG_GLOBAL": str(fake_home / "does-not-exist"),
            "GIT_CONFIG_NOSYSTEM": "1",
        }

        (work_path / "CHANGED.txt").write_text("real change", encoding="utf-8")
        run_git(["add", "."], cwd=work_path, env=no_ambient_identity_env)
        result = run_git(
            ["commit", "-m", "real commit with no ambient identity"],
            cwd=work_path,
            env=no_ambient_identity_env,
        )

        assert result.returncode == 0, result.stderr


class TestRemoteHeadSha:
    """Decision #40/Part B: the pre-clone freshness probe -- no clone, just
    a HEAD SHA lookup. Local paths work identically to a real remote for
    `git ls-remote`'s purposes, matching this file's own no-network style."""

    def test_returns_the_repos_head_sha(self, tmp_path):
        source = _init_repo(tmp_path / "source")
        expected = run_git(["rev-parse", "HEAD"], cwd=source).stdout.strip()

        sha = remote_head_sha(str(source))

        assert sha == expected
        assert len(sha) == 40

    def test_returns_none_for_unreachable_remote(self, tmp_path):
        nonexistent = tmp_path / "does-not-exist"

        assert remote_head_sha(str(nonexistent)) is None

    def test_changes_after_a_new_commit(self, tmp_path):
        source = _init_repo(tmp_path / "source")
        first = remote_head_sha(str(source))

        (source / "CHANGED.txt").write_text("new commit", encoding="utf-8")
        run_git(["add", "."], cwd=source)
        run_git(["commit", "-m", "second"], cwd=source)
        second = remote_head_sha(str(source))

        assert first != second
        assert second == run_git(["rev-parse", "HEAD"], cwd=source).stdout.strip()


class TestDiffChangedPaths:
    """Wave 8.6 (`ORC-003` reversal, `supervisor/specialist_selection.py`):
    `clone_baseline()` is `--depth 1` with zero retained history, so this
    fetches the one historical `from_sha` on demand before diffing. Also
    doubles as the empirical feasibility proof for fetch-by-SHA (the design's
    own stated fallback -- widening clone depth -- is only needed if this
    mechanism doesn't actually work)."""

    def test_detects_a_real_changed_path_between_two_revisions(self, tmp_path):
        remote = _init_repo(tmp_path / "remote", with_commit=False)
        (remote / "README.md").write_text("v1\n", encoding="utf-8")
        run_git(["add", "."], cwd=remote)
        run_git(["commit", "-m", "v1"], cwd=remote)
        from_sha = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()

        (remote / "README.md").write_text("v2\n", encoding="utf-8")
        run_git(["add", "."], cwd=remote)
        run_git(["commit", "-m", "v2"], cwd=remote)
        to_sha = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()

        baseline = tmp_path / "baseline"
        run_git(["clone", "--depth", "1", str(remote), str(baseline)])

        changed = diff_changed_paths(baseline, from_sha, to_sha)

        assert changed == ["README.md"]

    def test_unrelated_path_change_does_not_appear(self, tmp_path):
        remote = _init_repo(tmp_path / "remote", with_commit=False)
        (remote / "README.md").write_text("v1\n", encoding="utf-8")
        (remote / "other.txt").write_text("v1\n", encoding="utf-8")
        run_git(["add", "."], cwd=remote)
        run_git(["commit", "-m", "v1"], cwd=remote)
        from_sha = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()

        (remote / "other.txt").write_text("v2\n", encoding="utf-8")
        run_git(["add", "."], cwd=remote)
        run_git(["commit", "-m", "v2"], cwd=remote)
        to_sha = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()

        baseline = tmp_path / "baseline"
        run_git(["clone", "--depth", "1", str(remote), str(baseline)])

        changed = diff_changed_paths(baseline, from_sha, to_sha)

        assert changed == ["other.txt"]
        assert "README.md" not in changed

    def test_identical_revisions_return_empty_list_not_none(self, tmp_path):
        remote = _init_repo(tmp_path / "remote")
        sha = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()
        baseline = tmp_path / "baseline"
        run_git(["clone", "--depth", "1", str(remote), str(baseline)])

        assert diff_changed_paths(baseline, sha, sha) == []

    def test_unreachable_from_sha_fails_closed_with_none(self, tmp_path):
        """The fail-closed contract: any failure (bogus/unreachable SHA)
        returns `None`, never an empty list -- callers must treat `None` as
        "cannot determine, assume changed," never as a false "nothing
        changed."""
        remote = _init_repo(tmp_path / "remote")
        to_sha = run_git(["rev-parse", "HEAD"], cwd=remote).stdout.strip()
        baseline = tmp_path / "baseline"
        run_git(["clone", "--depth", "1", str(remote), str(baseline)])

        bogus_sha = "0" * 40
        assert diff_changed_paths(baseline, bogus_sha, to_sha) is None


class TestRunGitTimeout:
    """Found live, 2026-07-22: a `git push` hanging on interactive
    credential-manager resolution raised `subprocess.TimeoutExpired`
    uncaught, crashing the whole CLI with a raw traceback (exit code 1)
    instead of the typed, clean failure every caller's own `if result.
    returncode != 0` branch already handles. Fixed once in `run_git()`
    itself, so every one of its ~20 call sites is covered without a
    per-caller patch."""

    def test_timeout_returns_a_failed_completed_process_not_an_exception(self, monkeypatch):
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        def _raise_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git", "push"], timeout=0.01)

        monkeypatch.setattr(git_module.subprocess, "run", _raise_timeout)

        result = run_git(["push", "origin", "HEAD:refs/x"], timeout=0.01)

        assert result.returncode != 0
        assert "timed out" in result.stderr

    def test_timeout_with_input_text_also_returns_a_failed_completed_process(self, monkeypatch):
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        def _raise_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["git", "commit-tree"], timeout=0.01)

        monkeypatch.setattr(git_module.subprocess, "run", _raise_timeout)

        result = run_git(["commit-tree", "deadbeef"], input_text="msg", timeout=0.01)

        assert result.returncode != 0
        assert "timed out" in result.stderr


class TestGitTerminalPromptDisabled:
    """OPS-009 (found 2026-07-19, `test_state_git_backend_live.py`'s own
    docstring): closes the hang at its source -- git must never attempt an
    interactive credential prompt/helper in the first place -- rather than
    trying to bound it after it starts, which CPython's own `subprocess.
    run()` cannot reliably do for this exact hazard (see `_git.py`'s own
    `GIT_SAFETY_ENV` docstring)."""

    def test_present_in_every_call_with_no_explicit_env(self, monkeypatch):
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        captured = {}

        def _spy(*args, **kwargs):
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(git_module.subprocess, "run", _spy)

        run_git(["status"])

        assert captured["env"] is not None
        assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert captured["env"]["GCM_INTERACTIVE"] == "never"

    def test_present_in_the_input_text_stdin_branch_too(self, monkeypatch):
        """mktree/hash-object/commit-tree (state/git_backend.py) go through
        run_git()'s separate input_text branch -- must not be missed."""
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        captured = {}

        def _spy(*args, **kwargs):
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"", stderr=b"")

        monkeypatch.setattr(git_module.subprocess, "run", _spy)

        run_git(["commit-tree", "deadbeef"], input_text="msg")

        assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert captured["env"]["GCM_INTERACTIVE"] == "never"

    def test_coexists_with_a_caller_supplied_env_dict(self, monkeypatch):
        """state/git_backend.py's _COMMIT_IDENTITY_ENV / clone.py's identity
        env must still pass through unchanged alongside the new safety var."""
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        captured = {}

        def _spy(*args, **kwargs):
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(git_module.subprocess, "run", _spy)

        run_git(["config", "--local", "user.name", "x"], env={"GIT_AUTHOR_NAME": "readme-agent"})

        assert captured["env"]["GIT_AUTHOR_NAME"] == "readme-agent"
        assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert captured["env"]["GCM_INTERACTIVE"] == "never"

    def test_cannot_be_overridden_by_a_caller_supplied_env(self, monkeypatch):
        """Defense in depth: even if some future call site's own env dict
        tried to set this differently, the safety value always wins."""
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        captured = {}

        def _spy(*args, **kwargs):
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(git_module.subprocess, "run", _spy)

        run_git(["status"], env={"GIT_TERMINAL_PROMPT": "1"})

        assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"

    def test_gcm_interactive_never_is_also_always_present(self, monkeypatch):
        """Found live, 2026-07-22: GIT_TERMINAL_PROMPT=0 alone proved
        insufficient -- a CONFIGURED credential helper (git-credential-
        manager) is invoked regardless of that setting, and its own
        interactive flow is what actually hung. GCM_INTERACTIVE=never closes
        that gap without disabling the helper entirely (which would break
        the legitimate cached-credential local-dev case)."""
        import subprocess

        from readme_agent.gitsafety import _git as git_module

        captured = {}

        def _spy(*args, **kwargs):
            captured["env"] = kwargs.get("env")
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

        monkeypatch.setattr(git_module.subprocess, "run", _spy)

        run_git(["status"], env={"GCM_INTERACTIVE": "auto"})

        assert captured["env"]["GCM_INTERACTIVE"] == "never"
