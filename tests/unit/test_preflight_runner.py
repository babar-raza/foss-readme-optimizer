"""`_run_preflight_against`'s `ok` gate: identity is diagnostic-only, never blocking on its own.

Regression coverage for the 2026-08-17 fix (see runner.py's module docstring): a GitHub-wide
outage degraded `GET /user` specifically while every real per-repo check kept succeeding, and the
old `identity.ok and all(...) and llm.ok` gate stopped every local, no-push run for the duration
even though nothing that profile actually needs was broken.
"""

from __future__ import annotations

from readme_agent.preflight import runner
from readme_agent.preflight.github_check import GithubIdentity, GithubRepoCheck
from readme_agent.preflight.llm_check import LlmCheckResult


def _repo_ok(org_repo: str) -> GithubRepoCheck:
    return GithubRepoCheck(org_repo=org_repo, http_status=200, ok=True, default_branch="main")


def _repo_fail(org_repo: str) -> GithubRepoCheck:
    return GithubRepoCheck(org_repo=org_repo, http_status=503, ok=False, error="HTTP 503")


def _llm_ok() -> LlmCheckResult:
    return LlmCheckResult(ok=True, selected_model="qwen3-next", selection_reason="default")


def _llm_fail() -> LlmCheckResult:
    return LlmCheckResult(ok=False, error="HTTP 500")


class TestIdentityIsNonBlocking:
    def test_degraded_identity_with_all_repos_and_llm_ok_still_passes(self, monkeypatch):
        monkeypatch.setattr(runner.env, "gh_token", lambda: "tok")
        monkeypatch.setattr(
            runner,
            "check_identity",
            lambda token: GithubIdentity(ok=False, error="HTTP 503 from GET /user"),
        )
        monkeypatch.setattr(runner, "check_repo", lambda org_repo, token: _repo_ok(org_repo))
        monkeypatch.setattr(runner, "check_models", lambda base_url, api_key: _llm_ok())

        result = runner._run_preflight_against(["aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"])

        assert result.ok is True
        assert result.identity.ok is False

    def test_healthy_identity_does_not_mask_a_real_repo_failure(self, monkeypatch):
        monkeypatch.setattr(runner.env, "gh_token", lambda: "tok")
        monkeypatch.setattr(
            runner, "check_identity", lambda token: GithubIdentity(ok=True, login="babar-raza")
        )
        monkeypatch.setattr(runner, "check_repo", lambda org_repo, token: _repo_fail(org_repo))
        monkeypatch.setattr(runner, "check_models", lambda base_url, api_key: _llm_ok())

        result = runner._run_preflight_against(["some-org/unreachable"])

        assert result.ok is False

    def test_healthy_identity_does_not_mask_a_real_llm_failure(self, monkeypatch):
        monkeypatch.setattr(runner.env, "gh_token", lambda: "tok")
        monkeypatch.setattr(
            runner, "check_identity", lambda token: GithubIdentity(ok=True, login="babar-raza")
        )
        monkeypatch.setattr(runner, "check_repo", lambda org_repo, token: _repo_ok(org_repo))
        monkeypatch.setattr(runner, "check_models", lambda base_url, api_key: _llm_fail())

        result = runner._run_preflight_against(["aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"])

        assert result.ok is False

    def test_missing_token_still_fails_closed(self, monkeypatch):
        monkeypatch.setattr(runner.env, "gh_token", lambda: None)

        result = runner._run_preflight_against(["aspose-cells-foss/Aspose.Cells-FOSS-for-.NET"])

        assert result.ok is False
        assert result.identity.ok is False
        assert result.repos == []

    def test_format_summary_never_says_blocked_auth_for_identity_alone(self):
        result = runner.PreflightResult(
            ok=True,
            identity=GithubIdentity(ok=False, error="HTTP 503 from GET /user"),
            repos=[_repo_ok("aspose-cells-foss/Aspose.Cells-FOSS-for-.NET")],
            llm=_llm_ok(),
        )

        summary = runner.format_summary(result)

        assert "BLOCKED_AUTH" not in summary
        assert "Overall: PASS" in summary
