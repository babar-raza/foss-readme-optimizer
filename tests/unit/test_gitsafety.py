"""No network required -- everything here runs against local, disposable git repos."""

from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline, create_work_clone, toplevel_matches
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


class TestCloneBaselineAndWork:
    def _fake_entry(self, clone_url: str) -> ProductEntry:
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

    def test_clone_baseline_and_work_clone_from_local_source(self, tmp_path):
        source = _init_repo(tmp_path / "source")
        entry = self._fake_entry(str(source))

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
        entry = self._fake_entry(str(source))
        baseline_path = tmp_path / "baseline"

        clone_baseline(entry, baseline_path)
        (baseline_path / "stray.txt").write_text("should not survive a re-clone", encoding="utf-8")

        clone_baseline(entry, baseline_path)
        assert not (baseline_path / "stray.txt").exists()
