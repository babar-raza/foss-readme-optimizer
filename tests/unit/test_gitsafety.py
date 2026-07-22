"""No network required -- everything here runs against local, disposable git repos."""

from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import (
    clone_baseline,
    create_work_clone,
    diff_changed_paths,
    remote_head_sha,
    toplevel_matches,
)
from readme_agent.gitsafety.hooks import BLOCK_MARKER, install_pre_push_hook
from readme_agent.gitsafety.neuter import DISABLED_PUSH_URL, neuter_push
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.registry.models import ProductEntry


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

    def test_clone_baseline_is_re_cloned_fresh_each_time(self, tmp_path):
        source = _init_repo(tmp_path / "source")
        entry = _fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        clone_baseline(entry, baseline_path)
        (baseline_path / "stray.txt").write_text("should not survive a re-clone", encoding="utf-8")

        clone_baseline(entry, baseline_path)
        assert not (baseline_path / "stray.txt").exists()


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
