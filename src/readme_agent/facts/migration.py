"""Explicit ProductFactsV1-to-V2 migration with honest missing-field records."""

from __future__ import annotations

from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceType,
    FactSourceV2,
    FactVerificationState,
    ProductFactsV2,
    descriptive_fact_id,
)

_SURFACE_DEPENDENCIES = {
    "product.identity": ["readme.opening", "metadata.description"],
    "product.audience": ["readme.opening", "metadata.description"],
    "product.problems_solved": ["readme.opening", "metadata.description"],
    "product.capabilities": ["readme.capabilities", "metadata.description", "metadata.topics"],
    "product.formats": ["readme.capabilities", "metadata.topics"],
    "product.platforms": ["readme.capabilities", "metadata.topics"],
    "installation.coordinates": ["readme.installation"],
    "installation.verified_acquisition": ["readme.installation", "readme.example"],
    "example.minimal": ["readme.example"],
    "documentation.links": ["readme.resources", "metadata.homepage"],
    "release.state": ["readme.release"],
    "product.limitations": ["readme.limitations"],
    "product.compatibility": ["readme.capabilities", "readme.installation"],
    "product.license": ["readme.license", "community.license"],
    "support.routes": ["readme.resources", "community.support"],
    "relationship.commercial_foss": ["readme.relationship"],
}


def _source(
    source_type: FactSourceType,
    location: str,
    *,
    source_revision: str | None,
    observed_at: str | None,
) -> FactSourceV2:
    return FactSourceV2(
        source_type=source_type,
        location=location,
        source_revision=source_revision,
        retrieved_at=observed_at,
    )


def _known_fact(
    field_name: str,
    value,
    *,
    source: FactSourceV2,
    state: FactVerificationState,
    owner: str,
    confidence: float,
    qualifier: str = "primary",
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, qualifier),
        field=field_name,
        value=value,
        source=source,
        verification_state=state,
        authoritative_owner=owner,
        confidence=confidence,
        affected_surfaces=_SURFACE_DEPENDENCIES[field_name],
    )


def migrate_product_facts_v1(
    facts_v1: ProductFactsV1,
    *,
    source_revision: str | None = None,
    observed_at: str | None = None,
) -> ProductFactsV2:
    """Migrate without inventing fields V1 never represented.

    At least one immutable revision or retrieval time is mandatory so a migration
    cannot emit provenance-free facts.
    """

    if source_revision is None and observed_at is None:
        raise ValueError("V1 migration requires source_revision or observed_at")

    policy_source = _source(
        "approved_policy",
        f"registry-policy://{facts_v1.org_repo}",
        source_revision=source_revision,
        observed_at=observed_at,
    )
    repository_source = _source(
        "mechanical_repository",
        f"repository://{facts_v1.org_repo}",
        source_revision=source_revision,
        observed_at=observed_at,
    )
    known: dict[str, FactRecordV2] = {}

    identity = {
        key: value
        for key, value in {
            "family": facts_v1.family,
            "platform": facts_v1.platform,
            "ecosystem": facts_v1.ecosystem,
        }.items()
        if value is not None
    }
    if identity:
        known["product.identity"] = _known_fact(
            "product.identity",
            identity,
            source=policy_source,
            state="policy_approved",
            owner="portfolio-policy-owner",
            confidence=0.9,
        )
    if facts_v1.platform or facts_v1.ecosystem:
        known["product.platforms"] = _known_fact(
            "product.platforms",
            [value for value in (facts_v1.platform, facts_v1.ecosystem) if value],
            source=policy_source,
            state="policy_approved",
            owner="portfolio-policy-owner",
            confidence=0.9,
        )
    if facts_v1.declared_license:
        known["product.license"] = _known_fact(
            "product.license",
            facts_v1.declared_license,
            source=policy_source,
            state="policy_approved",
            owner="legal-policy-owner",
            confidence=0.85,
        )
    if facts_v1.relationship_talking_points:
        known["relationship.commercial_foss"] = _known_fact(
            "relationship.commercial_foss",
            facts_v1.relationship_talking_points,
            source=policy_source,
            state="policy_approved",
            owner="portfolio-policy-owner",
            confidence=0.9,
        )
    documentation_links = [
        link
        for link in (
            facts_v1.products_org_link,
            facts_v1.products_com_link,
            *facts_v1.secondary_links,
        )
        if link
    ]
    if documentation_links:
        known["documentation.links"] = _known_fact(
            "documentation.links",
            documentation_links,
            source=policy_source,
            state="policy_approved",
            owner="documentation-policy-owner",
            confidence=0.75,
        )
    if facts_v1.secondary_links:
        known["support.routes"] = _known_fact(
            "support.routes",
            facts_v1.secondary_links,
            source=policy_source,
            state="policy_approved",
            owner="support-policy-owner",
            confidence=0.75,
        )
    if facts_v1.package_coordinates:
        coordinate_value = [
            {
                "path": item.path,
                "ecosystem": item.ecosystem,
                "manifest_path": item.manifest_path,
            }
            for item in facts_v1.package_coordinates
        ]
        known["installation.coordinates"] = _known_fact(
            "installation.coordinates",
            coordinate_value,
            source=_source(
                "mechanical_manifest",
                f"repository://{facts_v1.org_repo}/manifests",
                source_revision=source_revision,
                observed_at=observed_at,
            ),
            state="verified",
            owner="repository-owner",
            confidence=1.0,
        )
        outcomes = [
            {
                "path": item.path,
                "ecosystem": item.ecosystem,
                "outcome": item.verification_outcome,
                "detail": item.verification_detail,
            }
            for item in facts_v1.package_coordinates
        ]
        conclusive_outcomes = {"REGISTRY_VERIFIED", "NOT_PUBLISHED", "NOT_APPLICABLE"}
        acquisition_verified = all(item["outcome"] in conclusive_outcomes for item in outcomes)
        acquisition_blocked = any(
            item["outcome"] in {"BLOCKED_NETWORK", "CAPABILITY_GAP"} for item in outcomes
        )
        known["installation.verified_acquisition"] = _known_fact(
            "installation.verified_acquisition",
            outcomes,
            source=_source(
                "external_registry" if acquisition_verified else "mechanical_repository",
                f"package-registry-check://{facts_v1.org_repo}",
                source_revision=source_revision,
                observed_at=observed_at,
            ),
            state=(
                "verified"
                if acquisition_verified
                else "blocked"
                if acquisition_blocked
                else "unverified"
            ),
            owner="repository-owner",
            confidence=1.0 if acquisition_verified else 0.0,
        )

    records: list[FactRecordV2] = []
    selections: dict[str, str] = {}
    for field_name in REQUIRED_PRODUCT_FIELDS:
        fact = known.get(field_name)
        if fact is None:
            fact = _known_fact(
                field_name,
                None,
                source=repository_source,
                state="missing",
                owner="repository-owner",
                confidence=0.0,
            )
        records.append(fact)
        selections[field_name] = fact.fact_id

    return ProductFactsV2(
        org_repo=facts_v1.org_repo,
        facts=records,
        selected_fact_ids=selections,
    )
