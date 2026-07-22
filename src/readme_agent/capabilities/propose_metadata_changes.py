"""Wraps `github_api/client.py::repo_summary()` -- the metadata specialist's
(Wave 7d) one capability. Class B per `docs/github-surface-control.md`/
`repository-presentation-surface-model.md` (description, homepage, topics):
`OWN-006` permits proposal only through a dry-run-first, explicitly gated
workflow -- **no GitHub API PATCH is ever attempted here or anywhere else
this wave**; the real apply gate (needing write-scoped credentials) is a
later phase's job.

Deliberately stateless (decision #26(b)): the product facts a sensible
proposal needs (family/platform/ecosystem/products-org-URL) are supplied by
the caller as plain arguments, not fetched by this capability itself --
`specialists/metadata_presentation.py` dispatches the existing, unscoped
`get_product_facts` first and threads its result in here, rather than one
capability reaching into another's dispatch path."""

from readme_agent import env
from readme_agent.capabilities.domains import METADATA_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.github_api.client import repo_summary
from readme_agent.registry.loader import require_listed

CAPABILITY_ID = "propose_metadata_changes"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Propose metadata changes",
    purpose="Read-only: fetch the repository's current description/homepage/topics via the "
    "real GitHub API and propose (never apply) improvements only where a field is currently "
    "missing -- an existing, non-empty value is never second-guessed or overwritten.",
    category="metadata_presentation",
    owner="readme_agent.github_api.client",
    execution_type="read_only_audit",
    required_inputs={"org_repo": "string"},
    optional_inputs={
        "family": "string",
        "platform": "string",
        "ecosystem": "string",
        "products_org_url": "string",
    },
    produced_outputs={
        "current_description": "string",
        "current_homepage": "string",
        "current_topics": "array",
        "proposed_description": "string",
        "proposed_homepage": "string",
        "proposed_topics": "array",
        "has_proposal": "boolean",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)",
        "a proposal is only ever a dry-run evidence record -- no PATCH is ever issued",
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[METADATA_PRESENTATION],
    tools_used=["github_api.client.repo_summary"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back, no write ever attempted",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(
    org_repo: str,
    family: str | None = None,
    platform: str | None = None,
    ecosystem: str | None = None,
    products_org_url: str | None = None,
) -> dict:
    require_listed(org_repo)
    token = env.gh_token()
    summary = repo_summary(org_repo, token)

    current_description = summary.get("description")
    current_homepage = summary.get("homepage")
    current_topics = summary.get("topics") or []

    proposed_description = None
    if not current_description and family and platform:
        proposed_description = f"{family} FOSS library for {platform}"

    proposed_homepage = None
    if not current_homepage and products_org_url:
        proposed_homepage = products_org_url

    desired_topics = {t.lower() for t in (ecosystem, platform) if t}
    missing_topics = desired_topics - {t.lower() for t in current_topics}
    proposed_topics = sorted({*current_topics, *missing_topics}) if missing_topics else None

    return {
        "current_description": current_description,
        "current_homepage": current_homepage,
        "current_topics": current_topics,
        "proposed_description": proposed_description,
        "proposed_homepage": proposed_homepage,
        "proposed_topics": proposed_topics,
        "has_proposal": any([proposed_description, proposed_homepage, proposed_topics]),
    }
