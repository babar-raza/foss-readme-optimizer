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


def run_preflight() -> PreflightResult:
    token = env.gh_token()
    if not token:
        return PreflightResult(
            ok=False,
            identity=GithubIdentity(ok=False, error="no GH_TOKEN or GITHUB_PAT set"),
            repos=[],
            llm=LlmCheckResult(ok=False, error="skipped: no GitHub token available"),
        )

    identity = check_identity(token)
    repos = [check_repo(entry.org_repo, token) for entry in enabled_entries()]
    llm = check_models(env.llm_base_url(), env.llm_api_key())

    ok = identity.ok and all(r.ok for r in repos) and llm.ok
    return PreflightResult(ok=ok, identity=identity, repos=repos, llm=llm)


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
