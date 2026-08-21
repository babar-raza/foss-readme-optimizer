"""Tests for conservative audience derivation from verified platforms."""

from readme_agent.facts.platform_audience import derive_platform_audience
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2


def _facts(platform: FactRecordV2) -> ProductFactsV2:
    return resolve_product_facts(
        "acme/widget",
        [platform],
        missing_source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://acme/widget",
            source_revision="a" * 40,
        ),
    )


def test_verified_platform_derives_governed_audience_label():
    platform = FactRecordV2(
        fact_id="product.platforms:manifest",
        field="product.platforms",
        value=["net"],
        source=FactSourceV2(
            source_type="mechanical_manifest",
            location="Widget.csproj",
            source_revision="a" * 40,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.compatibility"],
    )

    audience = derive_platform_audience(_facts(platform))

    assert audience is not None
    assert audience.value == ["Developers using .NET."]
    assert audience.verification_state == "verified"
    assert audience.supporting_fact_ids == [platform.fact_id]


def test_unverified_platform_cannot_derive_audience():
    platform = FactRecordV2(
        fact_id="product.platforms:claim",
        field="product.platforms",
        value=["typescript"],
        source=FactSourceV2(
            source_type="readme_claim",
            location="README.md",
            source_revision="a" * 40,
        ),
        verification_state="unverified",
        authoritative_owner="repository-owner",
        confidence=0.5,
        affected_surfaces=["readme.compatibility"],
    )

    assert derive_platform_audience(_facts(platform)) is None
