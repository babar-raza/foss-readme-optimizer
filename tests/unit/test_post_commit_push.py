"""No network required -- everything here runs against local, disposable git repos.

Covers `governance.post_commit_push` (the mechanism half of Decision #107's control-repo
auto-push) and `governance.install_hooks`'s new `post-commit` installation. Mirrors
`test_gitsafety.py`'s own "prove it against a real bare repo, never mock git" philosophy: the
positive case actually pushes to a real local remote and reads the content back; the negative case
actually provokes a real non-fast-forward rejection and asserts the remote is untouched, not just
that some exception was raised.
"""

import shutil
from pathlib import Path

import pytest
from governance import install_hooks, post_commit_push

from readme_agent.gitsafety._git import run_git


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


def _commit_file(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    run_git(["add", name], cwd=repo)
    run_git(["commit", "-m", message], cwd=repo)


class TestCurrentBranch:
    def test_returns_the_checked_out_branch_name(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        assert post_commit_push.current_branch(repo) == "main"

    def test_returns_none_on_detached_head(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        sha = run_git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
        run_git(["checkout", sha], cwd=repo)
        assert post_commit_push.current_branch(repo) is None


class TestPushCurrentBranch:
    def test_pushes_a_real_commit_to_a_real_remote(self, tmp_path):
        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work = _init_repo(tmp_path / "work")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)
        _commit_file(work, "new.txt", "content\n", "add new.txt")

        result = post_commit_push.push_current_branch(work)

        assert result.ok
        assert result.branch == "main"

        check = tmp_path / "check"
        run_git(["clone", str(bare_remote), str(check)])
        assert (check / "new.txt").read_text(encoding="utf-8") == "content\n"

    def test_detached_head_is_skipped_not_attempted(self, tmp_path):
        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work = _init_repo(tmp_path / "work")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)
        sha = run_git(["rev-parse", "HEAD"], cwd=work).stdout.strip()
        run_git(["checkout", sha], cwd=work)

        result = post_commit_push.push_current_branch(work)

        assert result.ok
        assert result.branch is None
        assert "detached" in result.detail

        # Nothing was ever pushed -- the bare remote's main still has no commits.
        show_ref = run_git(["show-ref", "--verify", "refs/heads/main"], cwd=bare_remote)
        assert show_ref.returncode != 0

    def test_neutered_remote_is_refused_not_pushed(self, tmp_path):
        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work = _init_repo(tmp_path / "work")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)
        run_git(
            ["remote", "set-url", "--push", "origin", post_commit_push.DISABLED_PUSH_URL],
            cwd=work,
        )

        result = post_commit_push.push_current_branch(work)

        assert not result.ok
        assert "DISABLED" in result.detail or "neuter" in result.detail

        show_ref = run_git(["show-ref", "--verify", "refs/heads/main"], cwd=bare_remote)
        assert show_ref.returncode != 0

    def test_non_fast_forward_is_reported_and_never_force_pushed(self, tmp_path):
        """The real concurrent-session case: a second clone already pushed a commit this clone
        doesn't have. The push must be rejected, with a rebase remedy, and the remote's real
        commit must survive completely untouched -- proving no force-push occurred, not just that
        an error was returned."""

        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work_a = _init_repo(tmp_path / "work_a")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work_a)
        assert post_commit_push.push_current_branch(work_a).ok

        work_b = tmp_path / "work_b"
        run_git(["clone", str(bare_remote), str(work_b)])
        run_git(["config", "user.email", "test@example.com"], cwd=work_b)
        run_git(["config", "user.name", "Test"], cwd=work_b)

        # work_a advances and pushes -- origin/main is now ahead of what work_b knows about.
        _commit_file(work_a, "from_a.txt", "a\n", "from work_a")
        assert post_commit_push.push_current_branch(work_a).ok
        remote_head_after_a = run_git(["rev-parse", "main"], cwd=bare_remote).stdout.strip()

        # work_b, unaware, commits its own diverging change.
        _commit_file(work_b, "from_b.txt", "b\n", "from work_b")

        result = post_commit_push.push_current_branch(work_b)

        assert not result.ok
        assert "rebase" in result.detail
        assert "pull --rebase" in result.detail

        remote_head_now = run_git(["rev-parse", "main"], cwd=bare_remote).stdout.strip()
        assert remote_head_now == remote_head_after_a, (
            "origin/main must be completely untouched by the rejected push -- any change here "
            "would mean a force-push (or equivalent) silently overwrote work_a's real commit"
        )


class TestInstallPostCommitHook:
    def test_writes_a_hook_carrying_the_decision_marker(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")
        hook_path = install_hooks.install_post_commit_hook(repo)

        assert hook_path == repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text(encoding="utf-8")
        assert "Decision #107" in content
        assert "post_commit_push.py" in content

    def test_installing_both_hooks_is_idempotent(self, tmp_path):
        repo = _init_repo(tmp_path / "repo")

        first_pre = install_hooks.install_pre_commit_hook(repo).read_text(encoding="utf-8")
        first_post = install_hooks.install_post_commit_hook(repo).read_text(encoding="utf-8")
        second_pre = install_hooks.install_pre_commit_hook(repo).read_text(encoding="utf-8")
        second_post = install_hooks.install_post_commit_hook(repo).read_text(encoding="utf-8")

        assert first_pre == second_pre
        assert first_post == second_post


class TestPostCommitHookActuallyPushesOnRealCommit:
    """The automated version of "manually confirm the hook fires and pushes on a real commit" --
    a real `git commit` invocation, letting git itself invoke the installed hook, not a direct
    call to `push_current_branch()`."""

    def test_a_real_commit_triggers_a_real_push(self, tmp_path):
        bare_remote = tmp_path / "remote.git"
        run_git(["init", "--bare", "-b", "main", str(bare_remote)])

        work = _init_repo(tmp_path / "work")
        run_git(["remote", "add", "origin", str(bare_remote)], cwd=work)

        # The generated hook invokes `scripts/governance/post_commit_push.py` via a path relative
        # to the repo root (matching this project's own real checkout layout, and the existing
        # pre-commit hook's identical convention) -- so the scratch repo needs that same relative
        # layout for the hook to find the script when git runs it.
        script_dest = work / "scripts" / "governance" / "post_commit_push.py"
        script_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(post_commit_push.__file__), script_dest)

        install_hooks.install_post_commit_hook(work)

        _commit_file(work, "triggered.txt", "hi\n", "trigger the post-commit hook")

        check = tmp_path / "check"
        run_git(["clone", str(bare_remote), str(check)])
        assert (check / "triggered.txt").read_text(encoding="utf-8") == "hi\n"


@pytest.fixture(autouse=True)
def _isolate_from_ambient_credential_helpers(monkeypatch):
    """Belt-and-suspenders alongside `post_commit_push._GIT_SAFETY_ENV` (already applied inside
    the module under test): keeps every local, credential-less push in this file from ever having
    a chance to hang on an interactive prompt, regardless of the runner's own git config."""

    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("GCM_INTERACTIVE", "never")
