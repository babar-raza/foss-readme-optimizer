"""Explicit, provenance-bearing ProductFactsV1-to-V2 migration."""

import pytest

from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import PackageCoordinateFactV1, ProductFactsV1
from readme_agent.facts.schema_v2 import REQUIRED_PRODUCT_FIELDS


def test_migration_preserves_known_v1_facts_and_marks_unknown_fields_missing():
    v1 = ProductFactsV1(
        org_repo="acme/widget",
        family="widget",
        platform="java",
        ecosystem="java",
        declared_license="MIT",
        relationship_talking_points=["open_source_scope"],
        secondary_links=[{"url": "https://docs.example.test/widget"}],
        package_coordinates=[
            PackageCoordinateFactV1(
                path=".",
                ecosystem="java",
                manifest_path="pom.xml",
                verification_outcome="REGISTRY_VERIFIED",
                verification_detail="found",
            )
        ],
    )

    v2 = migrate_product_facts_v1(v1, source_revision="abc123")

    assert set(v2.selected_fact_ids) == set(REQUIRED_PRODUCT_FIELDS)
    assert v2.selected_fact("product.identity").value["family"] == "widget"
    assert v2.selected_fact("product.license").verification_state == "policy_approved"
    assert v2.selected_fact("installation.coordinates").verification_state == "verified"
    assert v2.selected_fact("installation.verified_acquisition").value[0]["outcome"] == (
        "REGISTRY_VERIFIED"
    )
    assert v2.selected_fact("product.limitations").verification_state == "missing"


def test_migration_never_invents_absent_v1_fields():
    v2 = migrate_product_facts_v1(
        ProductFactsV1(org_repo="acme/widget"),
        observed_at="2026-07-23T00:00:00+00:00",
    )

    assert all(fact.verification_state == "missing" for fact in v2.facts)
    assert all(fact.value is None for fact in v2.facts)


def test_documentation_links_do_not_invent_empty_support_routes():
    v1 = ProductFactsV1(
        org_repo="acme/widget",
        products_org_link={"url": "https://products.example.test/widget"},
        secondary_links=[],
    )

    v2 = migrate_product_facts_v1(v1, source_revision="abc123")

    assert v2.selected_fact("documentation.links").verification_state == "policy_approved"
    assert v2.selected_fact("support.routes").verification_state == "missing"
    assert v2.selected_fact("support.routes").value is None


def test_migration_requires_provenance_boundary():
    with pytest.raises(ValueError, match="source_revision or observed_at"):
        migrate_product_facts_v1(ProductFactsV1(org_repo="acme/widget"))


def test_old_serialized_v1_remains_readable_before_migration():
    serialized_v1 = {
        "org_repo": "acme/widget",
        "family": "widget",
        "declared_license": "MIT",
        "package_coordinates": [],
    }
    v1 = ProductFactsV1.model_validate(serialized_v1)

    assert migrate_product_facts_v1(v1, source_revision="abc123").schema_version == 2
