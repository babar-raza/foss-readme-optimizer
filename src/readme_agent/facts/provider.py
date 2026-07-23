"""Collect repository and policy evidence into one ProductFactsV2 result."""

from __future__ import annotations

from datetime import UTC, datetime

from readme_agent.errors import NotAllowlistedError
from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.registry.loader import load_policy, require_listed


def collect_product_facts(
    org_repo: str,
    *,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
) -> dict:
    """Re-derive facts through the allow-list, policy, and repository seams."""

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
    result = {
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
        "detected_ecosystems": [
            ecosystem.model_dump() for ecosystem in profile.detected_ecosystems
        ],
        "unresolved_manifests": profile.unresolved_manifests,
        "package_roots": [root.model_dump() for root in profile.package_roots],
        "surface_ownership": policy.surface_ownership.model_dump(mode="json"),
        "source": {
            "identity_and_policy": (
                f"data/products.json + config/policies/{entry.policy_profile}.yml"
            ),
            "detected_ecosystems": "live repository clone (repository inspection)",
            "unresolved_manifests": "live repository clone (repository inspection)",
            "package_roots": "live repository clone (repository inspection)",
        },
    }
    product_facts_v1 = ProductFactsV1.from_capability_results(result)
    product_facts_v2 = migrate_product_facts_v1(
        product_facts_v1,
        source_revision=profile.source_revision,
        observed_at=(
            None if profile.source_revision is not None else datetime.now(UTC).isoformat()
        ),
    )
    result["product_facts_v2"] = product_facts_v2.model_dump(mode="json")
    return result
