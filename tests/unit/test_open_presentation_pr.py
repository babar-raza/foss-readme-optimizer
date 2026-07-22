"""TC-08: the one real `remote_write` capability this project registers.

GitHub API calls (`github_api/write_client.py`) are mocked -- no network.
`gitsafety/clone.py`'s new `create_pr_clone()`/`push_branch()` are exercised
for real against a local bare repo playing the role of the GitHub remote --
proving the actual clone/branch/push git mechanics work, not just that they
were called. `capabilities/open_presentation_pr.py::execute()`'s own
orchestration logic (mode gate, dedup short-circuit, argument threading) is
tested with those two layers monkeypatched, since both are proven
separately."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from readme_agent.capabilities import open_presentation_pr
from readme_agent.errors import GitSafetyError, NotAllowlistedError
from readme_agent.github_api import write_client
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import create_pr_clone, push_branch
from readme_agent.verification.checks import compute_verification_token


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)
    run_git(["config", "user.name", "Test"], cwd=path)


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


class TestFindOpenPr:
    def test_returns_none_when_no_open_pr_exists(self, monkeypatch):
        monkeypatch.setattr(
            write_client.requests, "get", lambda *a, **k: _FakeResponse(json_data=[])
        )
        assert write_client.find_open_pr("acme/widget", "branch", "tok") is None

    def test_returns_the_first_matching_open_pr(self, monkeypatch):
        pr = {"number": 7, "html_url": "https://github.com/acme/widget/pull/7"}
        monkeypatch.setattr(
            write_client.requests, "get", lambda *a, **k: _FakeResponse(json_data=[pr])
        )
        assert write_client.find_open_pr("acme/widget", "branch", "tok") == pr

    def test_queries_by_owner_qualified_head_and_open_state(self, monkeypatch):
        captured = {}

        def _fake_get(url, params, headers, timeout):
            captured["url"] = url
            captured["params"] = params
            return _FakeResponse(json_data=[])

        monkeypatch.setattr(write_client.requests, "get", _fake_get)
        write_client.find_open_pr("acme/widget", "readme-agent/x", "tok")

        assert captured["url"] == "https://api.github.com/repos/acme/widget/pulls"
        assert captured["params"] == {"head": "acme:readme-agent/x", "state": "open"}


class TestCreatePullRequest:
    def test_posts_the_expected_payload_and_returns_the_new_pr(self, monkeypatch):
        captured = {}

        def _fake_post(url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse(
                json_data={"number": 9, "html_url": "https://github.com/acme/widget/pull/9"}
            )

        monkeypatch.setattr(write_client.requests, "post", _fake_post)
        result = write_client.create_pull_request(
            "acme/widget", head="branch", base="main", title="t", body="b", token="tok"
        )

        assert result == {"number": 9, "html_url": "https://github.com/acme/widget/pull/9"}
        assert captured["url"] == "https://api.github.com/repos/acme/widget/pulls"
        assert captured["json"] == {"head": "branch", "base": "main", "title": "t", "body": "b"}

    def test_raises_on_a_real_error_response(self, monkeypatch):
        monkeypatch.setattr(
            write_client.requests, "post", lambda *a, **k: _FakeResponse(status_code=422)
        )
        with pytest.raises(requests.HTTPError):
            write_client.create_pull_request(
                "acme/widget", head="b", base="main", title="t", body="b", token="tok"
            )


class TestCreatePrCloneAndPushBranch:
    """Real local git throughout -- a bare repo stands in for the real
    GitHub remote. Proves create_pr_clone() never neuters push (the exact
    opposite of create_work_clone()) and that push_branch() actually lands
    a new branch on the remote, independent of any GitHub API mocking."""

    def test_clone_is_never_neutered_and_push_lands_a_real_branch(self, tmp_path):
        bare = tmp_path / "remote.git"
        bare.mkdir()
        run_git(["init", "--bare", "-b", "main"], cwd=bare)

        seed = tmp_path / "seed"
        _init_repo(seed)
        (seed / "README.md").write_text("# Widget\n", encoding="utf-8")
        run_git(["add", "."], cwd=seed)
        run_git(["commit", "-m", "initial"], cwd=seed)
        run_git(["remote", "add", "origin", str(bare)], cwd=seed)
        push = run_git(["push", "origin", "main"], cwd=seed)
        assert push.returncode == 0

        baseline = tmp_path / "baseline"
        clone = run_git(["clone", str(bare), str(baseline)])
        assert clone.returncode == 0

        # repo_url + ".git" must resolve back to the real bare path -- exactly
        # what create_pr_clone()'s own "restore origin" step relies on.
        entry = SimpleNamespace(org_repo="acme/widget", repo_url=str(bare)[:-4])
        pr_work = tmp_path / "pr_work"

        create_pr_clone(entry, baseline, pr_work)

        assert (pr_work / "README.md").read_text(encoding="utf-8") == "# Widget\n"
        remote_v = run_git(["remote", "-v"], cwd=pr_work).stdout
        assert "DISABLED" not in remote_v  # never neutered, unlike create_work_clone()

        (pr_work / "README.md").write_text("# Widget\n\nUpdated.\n", encoding="utf-8")
        branch_name = "readme-agent/presentation-update-test1234"
        checkout = run_git(["checkout", "-b", branch_name], cwd=pr_work)
        assert checkout.returncode == 0
        run_git(["add", "-A"], cwd=pr_work)
        commit = run_git(["commit", "-m", "test commit"], cwd=pr_work)
        assert commit.returncode == 0

        # http.extraheader is HTTP-only -- a bogus token is a harmless no-op
        # against this local, file-transport remote.
        push_result = push_branch(pr_work, branch_name, "unused-fake-token-for-local-remote")
        assert push_result.returncode == 0, push_result.stderr

        verify = tmp_path / "verify"
        verify_clone = run_git(["clone", "--branch", branch_name, str(bare), str(verify)])
        assert verify_clone.returncode == 0
        assert (verify / "README.md").read_text(encoding="utf-8") == "# Widget\n\nUpdated.\n"


class TestPrecheck:
    def test_accepts_the_real_verification_token(self):
        arguments = {
            "org_repo": "acme/widget",
            "facts_hash": "deadbeef1234",
            "fresh_fingerprint": "cafef00d",
            "verification_nonce": "run-nonce-1",
        }
        token = compute_verification_token(
            arguments["org_repo"],
            arguments["facts_hash"],
            arguments["fresh_fingerprint"],
            arguments["verification_nonce"],
        )
        assert open_presentation_pr.precheck({**arguments, "verification_verdict": token}) is None

    def test_rejects_a_hardcoded_accept_literal(self):
        reason = open_presentation_pr.precheck(
            {
                "org_repo": "acme/widget",
                "facts_hash": "deadbeef1234",
                "fresh_fingerprint": "cafef00d",
                "verification_nonce": "run-nonce-1",
                "verification_verdict": "accept",
            }
        )
        assert reason is not None
        assert "does not match" in reason

    def test_rejects_a_token_computed_with_a_different_nonce(self):
        replayed = compute_verification_token(
            "acme/widget", "deadbeef1234", "cafef00d", "a-previous-runs-nonce"
        )
        reason = open_presentation_pr.precheck(
            {
                "org_repo": "acme/widget",
                "facts_hash": "deadbeef1234",
                "fresh_fingerprint": "cafef00d",
                "verification_nonce": "this-runs-nonce",
                "verification_verdict": replayed,
            }
        )
        assert reason is not None


class TestReconciliationCheck:
    def test_returns_none_without_a_gh_token(self, monkeypatch):
        monkeypatch.setattr(open_presentation_pr.env, "gh_token", lambda: None)
        result = open_presentation_pr.reconciliation_check(
            {"org_repo": "acme/widget", "facts_hash": "deadbeef1234"}
        )
        assert result is None

    def test_returns_none_when_missing_required_arguments(self):
        assert open_presentation_pr.reconciliation_check({}) is None

    def test_backfills_from_a_real_open_pr(self, monkeypatch):
        monkeypatch.setattr(open_presentation_pr.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            open_presentation_pr,
            "find_open_pr",
            lambda org_repo, branch, token: {
                "number": 3,
                "html_url": "https://github.com/acme/widget/pull/3",
            },
        )
        result = open_presentation_pr.reconciliation_check(
            {"org_repo": "acme/widget", "facts_hash": "deadbeef1234"}
        )
        assert result == {
            "opened": True,
            "already_open": True,
            "pr_number": 3,
            "pr_url": "https://github.com/acme/widget/pull/3",
            "branch_name": "readme-agent/presentation-update-deadbeef1234",
        }


class TestManifest:
    def test_is_scoped_remote_write_with_idempotency_declared(self):
        manifest = open_presentation_pr.MANIFEST
        assert manifest.side_effect_class == "remote_write"
        assert manifest.allowed_domains == ["readme_presentation"]
        assert manifest.idempotency_inputs == ["org_repo", "facts_hash", "fresh_fingerprint"]
        assert manifest.retry_policy == "idempotent_only"


class TestExecuteOrchestration:
    """Git/GitHub mechanics proven real above -- these tests exercise
    execute()'s OWN orchestration: the mode gate, the existing-PR dedup
    short-circuit (never even clones when one is found), and the exact
    values threaded from inputs through to the PR-creation call."""

    def _fake_entry(self, *, mode="full"):
        return SimpleNamespace(org="acme", repo_name="widget", org_repo="acme/widget", mode=mode)

    def test_rejects_a_non_full_mode_entry(self, monkeypatch):
        monkeypatch.setattr(
            open_presentation_pr,
            "require_permitted",
            lambda org_repo: self._fake_entry(mode="dry_run"),
        )
        with pytest.raises(NotAllowlistedError):
            open_presentation_pr.execute(
                "acme/widget", "hash1", "fp1", "# Widget\n", "verdict", "nonce"
            )

    def test_raises_when_no_gh_token_is_configured(self, monkeypatch):
        monkeypatch.setattr(
            open_presentation_pr, "require_permitted", lambda org_repo: self._fake_entry()
        )
        monkeypatch.setattr(open_presentation_pr.env, "gh_token", lambda: None)
        with pytest.raises(GitSafetyError):
            open_presentation_pr.execute(
                "acme/widget", "hash1", "fp1", "# Widget\n", "verdict", "nonce"
            )

    def test_short_circuits_when_a_pr_already_exists(self, monkeypatch):
        monkeypatch.setattr(
            open_presentation_pr, "require_permitted", lambda org_repo: self._fake_entry()
        )
        monkeypatch.setattr(open_presentation_pr.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            open_presentation_pr,
            "find_open_pr",
            lambda org_repo, branch, token: {
                "number": 5,
                "html_url": "https://github.com/acme/widget/pull/5",
            },
        )
        cloned = {"called": False}
        monkeypatch.setattr(
            open_presentation_pr,
            "clone_baseline",
            lambda *a, **k: cloned.update(called=True),
        )

        result = open_presentation_pr.execute(
            "acme/widget", "hash1", "fp1", "# Widget\n", "verdict", "nonce"
        )

        assert result == {
            "opened": False,
            "already_open": True,
            "pr_number": 5,
            "pr_url": "https://github.com/acme/widget/pull/5",
            "branch_name": "readme-agent/presentation-update-hash1",
        }
        assert cloned["called"] is False

    def test_opens_a_new_pr_end_to_end_with_clone_push_mocked(self, tmp_path, monkeypatch):
        pr_work_path = tmp_path / "pr_work"

        monkeypatch.setattr(
            open_presentation_pr, "require_permitted", lambda org_repo: self._fake_entry()
        )
        monkeypatch.setattr(open_presentation_pr.env, "gh_token", lambda: "fake-token")
        monkeypatch.setattr(
            open_presentation_pr, "find_open_pr", lambda org_repo, branch, token: None
        )
        monkeypatch.setattr(
            open_presentation_pr,
            "paths",
            SimpleNamespace(
                baseline_dir=lambda org, repo: tmp_path / "baseline",
                pr_work_dir=lambda org, repo: pr_work_path,
            ),
        )
        monkeypatch.setattr(
            open_presentation_pr, "clone_baseline", lambda entry, baseline_path: None
        )

        def _fake_create_pr_clone(entry, baseline_path, target):
            _init_repo(target)
            (target / "README.md").write_text("# Widget\n", encoding="utf-8")
            run_git(["add", "."], cwd=target)
            run_git(["commit", "-m", "initial"], cwd=target)
            return target

        monkeypatch.setattr(open_presentation_pr, "create_pr_clone", _fake_create_pr_clone)

        pushed = {}

        def _fake_push_branch(repo_path, branch_name, token):
            pushed["branch"] = branch_name
            pushed["path"] = repo_path
            return SimpleNamespace(returncode=0, stderr="")

        monkeypatch.setattr(open_presentation_pr, "push_branch", _fake_push_branch)
        monkeypatch.setattr(
            open_presentation_pr,
            "repo_summary",
            lambda org_repo, token: {"default_branch": "main"},
        )

        created_pr = {}

        def _fake_create_pull_request(org_repo, *, head, base, title, body, token):
            created_pr.update(org_repo=org_repo, head=head, base=base, title=title, body=body)
            return {"number": 11, "html_url": "https://github.com/acme/widget/pull/11"}

        monkeypatch.setattr(open_presentation_pr, "create_pull_request", _fake_create_pull_request)

        result = open_presentation_pr.execute(
            "acme/widget", "deadbeef1234", "fp1", "# Widget\n\nUpdated.\n", "verdict", "nonce"
        )

        assert result == {
            "opened": True,
            "already_open": False,
            "pr_number": 11,
            "pr_url": "https://github.com/acme/widget/pull/11",
            "branch_name": "readme-agent/presentation-update-deadbeef1234",
        }
        assert pushed["branch"] == "readme-agent/presentation-update-deadbeef1234"
        assert created_pr["head"] == "readme-agent/presentation-update-deadbeef1234"
        assert created_pr["base"] == "main"
        assert "deadbeef1234" in created_pr["body"]  # PRL-002 facts_hash marker
        assert (pr_work_path / "README.md").read_text(encoding="utf-8") == "# Widget\n\nUpdated.\n"
        branch_result = run_git(["branch", "--show-current"], cwd=pr_work_path)
        assert branch_result.stdout.strip() == "readme-agent/presentation-update-deadbeef1234"
