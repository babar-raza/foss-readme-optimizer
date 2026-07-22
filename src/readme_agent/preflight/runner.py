"""Preflight orchestration: GitHub read-check (all enabled repos) + LLM /models check.

Both checks are fail-closed and run before any clone/generation work. Called
automatically as the first step of `run`/`run-registry`, and standalone via
`readme-agent preflight`.
"""

from dataclasses import dataclass

from readme_agent import env
from readme_agent.preflight.github_check import (
    GithubIdentity,
    GithubRepoCheck,
    check_identity,
    check_repo,
)
from readme_agent.preflight.llm_check import LlmCheckResult, check_models
from readme_agent.registry.loader import enabled_entries


@dataclass
class PreflightResult:
    ok: bool
    identity: GithubIdentity
    repos: list[GithubRepoCheck]
    llm: LlmCheckResult


def _run_preflight_against(org_repos: list[str]) -> PreflightResult:
    token = env.gh_token()
    if not token:
        return PreflightResult(
            ok=False,
            identity=GithubIdentity(ok=False, error="no GH_TOKEN or GITHUB_PAT set"),
            repos=[],
            llm=LlmCheckResult(ok=False, error="skipped: no GitHub token available"),
        )

    identity = check_identity(token)
    repos = [check_repo(org_repo, token) for org_repo in org_repos]
    llm = check_models(env.llm_base_url(), env.llm_api_key())

    ok = identity.ok and all(r.ok for r in repos) and llm.ok
    return PreflightResult(ok=ok, identity=identity, repos=repos, llm=llm)


def run_preflight() -> PreflightResult:
    return _run_preflight_against([entry.org_repo for entry in enabled_entries()])


def run_preflight_for_repo(org_repo: str) -> PreflightResult:
    """Wave 8.5 (`ORC-006`/D2): a single-repo preflight, deliberately NOT
    reusing the portfolio-wide `run_preflight()` above -- that function
    checks *every* `enabled_entries()`, which grows as the registry does; an
    unrelated repo's transient failure would otherwise block a completely
    unrelated single-repo `supervise` call, a real correctness bug, not just
    wasted work. Used by `commands.py::cmd_supervise()`."""
    return _run_preflight_against([org_repo])


def format_summary(result: PreflightResult) -> str:
    lines = ["Preflight:"]
    if result.identity.ok:
        scopes = ", ".join(result.identity.scopes) or "none"
        lines.append(f"  GitHub identity: {result.identity.login} (scopes: {scopes})")
    else:
        lines.append(f"  GitHub identity: BLOCKED_AUTH ({result.identity.error})")
    for r in result.repos:
        if r.ok:
            lines.append(
                f"  {r.org_repo}: HTTP 200, default_branch={r.default_branch}, license={r.license}"
            )
        else:
            lines.append(f"  {r.org_repo}: BLOCKED_NETWORK ({r.error})")
    if result.llm.ok:
        lines.append(
            f"  LLM: selected_model={result.llm.selected_model} ({result.llm.selection_reason})"
        )
    else:
        lines.append(f"  LLM: BLOCKED_LLM ({result.llm.error})")
    lines.append(f"  Overall: {'PASS' if result.ok else 'FAIL'}")
    return "\n".join(lines)
