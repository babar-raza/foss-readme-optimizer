"""Wraps `github_api/client.py::list_releases()` -- the release half of the
package/release auditor's (Wave 7c) audit. Class D per
`docs/github-surface-control.md`/`repository-presentation-surface-model.md`
(releases, packages): product-agent owned, audit/handoff only --
`OWN-004`/`OWN-013` forbid any renderer or write path here, and none exists.

Deliberately does NOT duplicate the package-resolution half: `check_install_
path` (Wave 2, unscoped) already wraps `ecosystems/resolver.py`'s live Maven
Central resolution -- the specialist (`specialists/package_release_audit.py`)
dispatches both capabilities rather than this one reimplementing resolver
logic a second time (GOVERNANCE.md "no silent duplicates")."""

from readme_agent import env
from readme_agent.capabilities.domains import PACKAGE_RELEASE_AUDIT
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.github_api.client import list_releases
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "audit_package_release_surfaces"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Audit package/release surfaces",
    purpose="Read-only audit of GitHub Releases (existence, count, latest tag/name) via the real "
    "GitHub API -- never a renderer or write path, since releases are product-agent owned.",
    category="package_release_audit",
    owner="readme_agent.github_api.client",
    execution_type="read_only_audit",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "releases_count": "integer",
        "latest_release_tag": "string",
        "latest_release_name": "string",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)"
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[PACKAGE_RELEASE_AUDIT],
    tools_used=["github_api.client.list_releases"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def _release_sort_key(release: dict) -> str:
    """`published_at` (falling back to `created_at` for a draft with no publish date) --
    `list_releases()`'s own pagination order is not guaranteed stable across calls
    (TC-16, Phase 13 §13.1: response-ordering noise alone could flip "latest" between
    two identical-content calls and falsely defeat the supervisor's convergence
    shortcut). Empty string sorts oldest-first for a release with neither field, so it
    never wins "latest" against any release that has a real timestamp."""
    return release.get("published_at") or release.get("created_at") or ""


def execute(org_repo: str) -> dict:
    require_listed(org_repo)
    token = env.gh_token()
    releases = list_releases(org_repo, token)
    ordered = sorted(releases, key=_release_sort_key, reverse=True)
    latest = ordered[0] if ordered else {}
    return {
        "releases_count": len(releases),
        "latest_release_tag": latest.get("tag_name"),
        "latest_release_name": latest.get("name"),
    }
