"""Wraps `github_api/client.py` -- the GitHub-generated-surface auditor's
(Wave 7b) one capability. Class E per `docs/github-surface-control.md`/
`repository-presentation-surface-model.md` (contributors, languages,
stars/forks/watchers/activity): audit-only, forever -- `OWN-005`/`OWN-012`
forbid any renderer or write path for a GitHub-generated surface, and none
exists here, deliberately. Scoped to its own domain
(`GITHUB_GENERATED_SURFACE_AUDIT`), mirroring `classify_upstream_change.py`'s
domain-scoping precedent -- the second domain-scoped capability in this
project, and the first to make `len(KNOWN_DOMAINS) > 1` real.

Deliberately stateless like every other capability (decision #26(b)): it
fetches from the GitHub API and returns a snapshot; the calling specialist
(`specialists/github_generated_surface_audit.py`) owns comparing this
snapshot against the prior accepted one and persisting the result."""

from readme_agent import env
from readme_agent.capabilities.domains import GITHUB_GENERATED_SURFACE_AUDIT
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.github_api.client import list_contributors, list_languages, repo_summary
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "audit_github_generated_surfaces"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Audit GitHub-generated surfaces",
    purpose="Read-only audit of contributors, languages, and stargazer/fork/watcher/open-issue "
    "counts via the real GitHub API -- never a renderer or write path, since these surfaces are "
    "GitHub-generated and this project must never treat them as directly editable metadata.",
    category="github_generated_surface_audit",
    owner="readme_agent.github_api.client",
    execution_type="read_only_audit",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "contributors_count": "integer",
        "primary_language": "string",
        "languages": "object",
        "stargazers_count": "integer",
        "forks_count": "integer",
        "watchers_count": "integer",
        "open_issues_count": "integer",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)"
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[GITHUB_GENERATED_SURFACE_AUDIT],
    tools_used=[
        "github_api.client.repo_summary",
        "github_api.client.list_contributors",
        "github_api.client.list_languages",
    ],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str) -> dict:
    require_listed(org_repo)
    token = env.gh_token()

    summary = repo_summary(org_repo, token)
    contributors = list_contributors(org_repo, token)
    languages = list_languages(org_repo, token)

    return {
        "contributors_count": len(contributors),
        "primary_language": summary.get("language"),
        "languages": languages,
        "stargazers_count": summary.get("stargazers_count", 0),
        "forks_count": summary.get("forks_count", 0),
        "watchers_count": summary.get("watchers_count", 0),
        "open_issues_count": summary.get("open_issues_count", 0),
    }
