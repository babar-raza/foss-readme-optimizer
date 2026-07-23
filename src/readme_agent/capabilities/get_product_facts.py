"""Wave 6 (decision #37): since no external "product agent" handoff system
exists (FACT-001's "repository inspection, an owning product agent, or both"
is read here as "both, always" -- there is no cooperating counterparty to
integrate with), this capability combines this project's own already-built
product inventory (data/products.json + config/policies/*.yml) with live
repository profiling into one product-facts record. Both sources every call,
mandatory -- never offered as two alternative paths behind a flag.

Explicitly not the full decision #22 product-facts list: audience, a
verified example, release information, and known limitations remain unbuilt.
`DOC-006` (the schema that would freeze the complete list) stays
RESEARCH-GATED; this is a thin wrapper around today's real, narrower data.

No live `state_backend` object here (decision #26(b), matching
render_readme_candidate.py's own established convention) -- accepts the
same durable-skip signal as plain values (`prior_upstream_revision`/
`prior_profile_result`) instead; see profile_repository.py's matching
docstring for the full reasoning.
"""

from readme_agent.capabilities.schema import CapabilityManifest, OrgRepoOnlyInputV1
from readme_agent.errors import NotAllowlistedError
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.registry.loader import load_policy, require_listed

CAPABILITY_ID = "get_product_facts"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Get product facts",
    purpose="Read-only: combines the product inventory (data/products.json + its "
    "config/policies/*.yml profile -- identity, declared license, required-link specs, "
    "relationship talking points, secondary links, block policy) with live repository "
    "profiling (detected ecosystems, unresolved manifests) into one record. Both sources "
    "every call, never one or the other. NOT the full decision #22 schema (audience, "
    "verified example, release info, limitations remain unbuilt -- DOC-006 stays "
    "RESEARCH-GATED).",
    category="product_facts",
    owner="readme_agent.registry.loader",
    execution_type="deterministic_tool",
    required_inputs={"org_repo": "string"},
    produced_outputs={
        "org_repo": "string",
        "family": "string",
        "platform": "string",
        "ecosystem": "string",
        "policy_profile": "string",
        "declared_license": "string",
        "products_org_link": "object",
        "products_com_link": "object",
        "relationship_talking_points": "array",
        "secondary_links": "array",
        "word_limit": "object",
        "prohibited_terms": "array",
        "link_whitelist_domains": "array",
        "detected_ecosystems": "array",
        "unresolved_manifests": "array",
        "package_roots": "array",
        "source": "object",
    },
    preconditions=[
        "org_repo must be listed in data/products.json (mode is irrelevant -- read-only, "
        "same gate as profile_repository)",
    ],
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    # Wave 11.4 (`CAP-008`): real structural validation of the one
    # LLM-visible argument, `org_repo`.
    input_model=OrgRepoOnlyInputV1,
    tools_used=[
        "registry.loader.require_listed",
        "registry.loader.load_policy",
        "profile.cached.get_or_build_profile",
    ],
    failure_modes=[
        "NotAllowlistedError if org_repo is not listed in data/products.json",
        "NotAllowlistedError if the entry has no policy_profile configured",
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute(
    org_repo: str,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
) -> dict:
    """prior_upstream_revision/prior_profile_result: see
    profile_repository.execute()'s matching docstring -- same deliberately
    undeclared-in-schema plain-value convention, same wiring caller
    (profile_repo_with_cache())."""
    entry = require_listed(org_repo)
    if entry.policy_profile is None:
        raise NotAllowlistedError(f"{org_repo} has no policy_profile configured")
    policy = load_policy(entry.policy_profile)

    profile = get_or_build_profile(
        entry,
        prior_upstream_revision=prior_upstream_revision,
        prior_profile_result=prior_profile_result,
    )

    required = policy.required_elements
    return {
        "org_repo": org_repo,
        "family": entry.family,
        "platform": entry.platform,
        "ecosystem": entry.ecosystem,
        "policy_profile": entry.policy_profile,
        "declared_license": required.license_mentioned.detected_license,
        "products_org_link": required.products_org_link.model_dump(),
        "products_com_link": required.products_com_link.model_dump(),
        "relationship_talking_points": required.relationship_explained.talking_points,
        "secondary_links": policy.secondary_links,
        "word_limit": policy.block.word_limit.model_dump(),
        "prohibited_terms": policy.block.prohibited_terms,
        "link_whitelist_domains": policy.block.link_whitelist_domains,
        "detected_ecosystems": [e.model_dump() for e in profile.detected_ecosystems],
        "unresolved_manifests": profile.unresolved_manifests,
        # Wave 11.3 (`FACT-010`): additive -- Wave 11.1's multi-root package
        # graph (`ECO-004`) was already computed inside `profile` above (no
        # new clone/parse cost) but never exposed here until now.
        "package_roots": [r.model_dump() for r in profile.package_roots],
        "source": {
            "identity_and_policy": (
                f"data/products.json + config/policies/{entry.policy_profile}.yml"
            ),
            "detected_ecosystems": "live repository clone (repository inspection)",
            "unresolved_manifests": "live repository clone (repository inspection)",
            "package_roots": "live repository clone (repository inspection)",
        },
    }
