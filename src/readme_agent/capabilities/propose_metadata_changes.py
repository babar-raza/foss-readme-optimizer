"""Wraps `github_api/client.py::repo_summary()` -- the metadata specialist's
(Wave 7d) one capability. Class B per `docs/github-surface-control.md`/
`repository-presentation-surface-model.md` (description, homepage, topics):
`OWN-006` permits proposal only through a dry-run-first, explicitly gated
workflow -- **no GitHub API PATCH is ever attempted here or anywhere else
this wave**; the real apply gate (needing write-scoped credentials) is a
later phase's job.

The registered boundary accepts only `org_repo`. It independently re-derives
ProductFactsV2 through the shared `facts.provider.collect_product_facts`
service and computes surface eligibility/citations inside this module.
`get_product_facts` uses the same lower-level provider, so neither capability
calls or dispatches the other and caller-supplied facts cannot bypass the
gate."""

from readme_agent import env
from readme_agent.capabilities.domains import METADATA_PRESENTATION
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.facts.gating import SurfaceFactRequirementV1, evaluate_surface_facts
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.github_api.client import repo_summary

CAPABILITY_ID = "propose_metadata_changes"
_FACT_REQUIREMENTS = (
    SurfaceFactRequirementV1(
        surface_id="metadata.description",
        required_fields=[
            "product.identity",
            "product.audience",
            "product.problems_solved",
        ],
    ),
    SurfaceFactRequirementV1(
        surface_id="metadata.homepage",
        required_fields=["documentation.links"],
    ),
    SurfaceFactRequirementV1(
        surface_id="metadata.topics",
        required_fields=[
            "product.capabilities",
            "product.formats",
            "product.platforms",
        ],
    ),
)

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="2",
    name="Propose metadata changes",
    purpose="Read-only: fetch the repository's current description/homepage/topics via the "
    "real GitHub API and propose (never apply) improvements only where a field is currently "
    "missing and independently re-derived ProductFactsV2 permits the surface -- caller-supplied "
    "facts, eligibility, and citations are not accepted.",
    category="metadata_presentation",
    owner="readme_agent.github_api.client",
    execution_type="read_only_audit",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "current_description": "string",
        "current_homepage": "string",
        "current_topics": "array",
        "proposed_description": "string",
        "proposed_homepage": "string",
        "proposed_topics": "array",
        "has_proposal": "boolean",
        "blocked_findings": "array",
        "fact_citations": "object",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only)",
        "facts and eligibility are re-derived inside the capability from governed sources",
        "a proposal is only ever a dry-run evidence record -- no PATCH is ever issued",
    ],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[METADATA_PRESENTATION],
    tools_used=["facts.provider.collect_product_facts", "github_api.client.repo_summary"],
    failure_modes=["NotAllowlistedError if org_repo is not listed in data/products.json"],
    rollback_behavior="not applicable -- read-only, nothing to roll back, no write ever attempted",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(org_repo: str) -> dict:
    facts_result = collect_product_facts(org_repo)
    product_facts = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
    decisions = evaluate_surface_facts(product_facts, list(_FACT_REQUIREMENTS))
    eligibility = {decision.surface_id: decision.eligible for decision in decisions}
    citations = {
        requirement.surface_id: [
            product_facts.selected_fact(field_name).fact_id
            for field_name in requirement.required_fields
        ]
        for requirement, decision in zip(_FACT_REQUIREMENTS, decisions, strict=True)
        if decision.eligible
    }
    family = facts_result.get("family")
    platform = facts_result.get("platform")
    ecosystem = facts_result.get("ecosystem")
    products_org_url = (facts_result.get("products_org_link") or {}).get("url")

    token = env.gh_token()
    summary = repo_summary(org_repo, token)

    current_description = summary.get("description")
    current_homepage = summary.get("homepage")
    current_topics = summary.get("topics") or []
    blocked_findings = [
        {
            "surface_id": surface_id,
            "reason": "missing or conflicting ProductFactsV2 dependencies",
        }
        for surface_id in ("metadata.description", "metadata.homepage", "metadata.topics")
        if not eligibility.get(surface_id, False)
    ]

    proposed_description = None
    if (
        eligibility.get("metadata.description", False)
        and not current_description
        and family
        and platform
    ):
        proposed_description = f"{family} FOSS library for {platform}"

    proposed_homepage = None
    if eligibility.get("metadata.homepage", False) and not current_homepage and products_org_url:
        proposed_homepage = products_org_url

    desired_topics = (
        {t.lower() for t in (ecosystem, platform) if t}
        if eligibility.get("metadata.topics", False)
        else set()
    )
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
        "blocked_findings": blocked_findings,
        "fact_citations": citations,
    }
