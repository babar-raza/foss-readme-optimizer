"""Fact precedence, conflicts, dependent-surface gates, and claim citations."""

from readme_agent.facts.gating import (
    SurfaceFactRequirementV1,
    TechnicalClaimV1,
    evaluate_surface_facts,
    validate_claim_citations,
)
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2


def _source(source_type, location):
    return FactSourceV2(
        source_type=source_type,
        location=location,
        source_revision="abc123",
    )


def _candidate(fact_id, field, value, source_type, location, surfaces):
    return FactRecordV2(
        fact_id=fact_id,
        field=field,
        value=value,
        source=_source(source_type, location),
        verification_state="verified" if source_type != "readme_claim" else "unverified",
        authoritative_owner="repository-owner",
        confidence=1.0 if source_type != "readme_claim" else 0.2,
        affected_surfaces=surfaces,
    )


def _resolve(candidates):
    return resolve_product_facts(
        "acme/widget",
        candidates,
        missing_source=_source("mechanical_repository", "repository://acme/widget"),
        missing_field_surfaces={
            "product.audience": ["readme.opening"],
            "product.limitations": ["readme.limitations"],
        },
    )


def test_mechanical_fact_outranks_conflicting_readme_claim_without_guessing():
    mechanical = _candidate(
        "installation.coordinates:manifest",
        "installation.coordinates",
        ["org.acme:widget"],
        "mechanical_manifest",
        "repository://acme/widget/pom.xml",
        ["readme.installation"],
    )
    readme = _candidate(
        "installation.coordinates:readme",
        "installation.coordinates",
        ["org.acme:made-up"],
        "readme_claim",
        "repository://acme/widget/README.md",
        ["readme.installation"],
    )

    facts = _resolve([readme, mechanical])
    selected = facts.selected_fact("installation.coordinates")

    assert selected.fact_id == mechanical.fact_id
    assert selected.verification_state == "verified"
    assert selected.conflicts[0].status == "resolved_by_precedence"


def test_same_precedence_disagreement_blocks_only_affected_surface():
    first = _candidate(
        "product.license:license-file",
        "product.license",
        "MIT",
        "mechanical_repository",
        "repository://acme/widget/LICENSE",
        ["readme.license"],
    )
    second = _candidate(
        "product.license:manifest",
        "product.license",
        "Apache-2.0",
        "mechanical_repository",
        "repository://acme/widget/pom.xml",
        ["readme.license"],
    )
    facts = _resolve([first, second])

    decisions = evaluate_surface_facts(
        facts,
        [
            SurfaceFactRequirementV1(
                surface_id="readme.license", required_fields=["product.license"]
            ),
            SurfaceFactRequirementV1(
                surface_id="readme.limitations", required_fields=["product.limitations"]
            ),
        ],
    )

    assert decisions[0].eligible is False
    assert facts.selected_fact("product.license").verification_state == "conflicting"
    assert decisions[1].blocking_fact_ids == ["product.limitations:missing"]


def test_missing_fact_does_not_block_unrelated_surface():
    identity = _candidate(
        "product.identity:repository",
        "product.identity",
        {"name": "Widget"},
        "mechanical_repository",
        "repository://acme/widget",
        ["readme.opening"],
    )
    facts = _resolve([identity])

    decisions = evaluate_surface_facts(
        facts,
        [
            SurfaceFactRequirementV1(
                surface_id="readme.opening", required_fields=["product.identity"]
            ),
            SurfaceFactRequirementV1(
                surface_id="readme.limitations", required_fields=["product.limitations"]
            ),
        ],
    )

    assert decisions[0].eligible is True
    assert decisions[1].eligible is False


def test_changed_technical_claim_requires_eligible_fact_for_same_surface():
    identity = _candidate(
        "product.identity:repository",
        "product.identity",
        {"name": "Widget"},
        "mechanical_repository",
        "repository://acme/widget",
        ["readme.opening"],
    )
    facts = _resolve([identity])
    valid = TechnicalClaimV1(
        claim_id="readme-opening-product-name",
        surface_id="readme.opening",
        text="Widget processes documents.",
        fact_ids=[identity.fact_id],
    )
    invalid = TechnicalClaimV1(
        claim_id="metadata-description-product-name",
        surface_id="metadata.description",
        text="Widget processes documents.",
        fact_ids=[identity.fact_id],
    )

    decision = validate_claim_citations(facts, [valid, invalid])

    assert decision.valid is False
    assert decision.invalid_claim_ids == ["metadata-description-product-name"]


def test_lower_precedence_losing_fact_cannot_be_cited_as_truth():
    mechanical = _candidate(
        "product.license:license-file",
        "product.license",
        "MIT",
        "mechanical_repository",
        "repository://acme/widget/LICENSE",
        ["readme.license"],
    )
    documentation = _candidate(
        "product.license:documentation",
        "product.license",
        "Proprietary",
        "approved_documentation",
        "https://docs.example.test/license",
        ["readme.license"],
    )
    facts = _resolve([documentation, mechanical])

    decision = validate_claim_citations(
        facts,
        [
            TechnicalClaimV1(
                claim_id="losing-license-claim",
                surface_id="readme.license",
                text="Proprietary",
                fact_ids=[documentation.fact_id],
            )
        ],
    )

    assert facts.selected_fact("product.license").fact_id == mechanical.fact_id
    assert decision.valid is False
    assert decision.invalid_claim_ids == ["losing-license-claim"]
    assert "is not selected" in decision.reasons[0]


def test_same_rank_losing_fact_cannot_bypass_unresolved_conflict():
    first = _candidate(
        "product.license:license-file",
        "product.license",
        "MIT",
        "mechanical_repository",
        "repository://acme/widget/LICENSE",
        ["readme.license"],
    )
    second = _candidate(
        "product.license:manifest",
        "product.license",
        "Apache-2.0",
        "mechanical_manifest",
        "repository://acme/widget/pom.xml",
        ["readme.license"],
    )
    facts = _resolve([first, second])
    losing = next(
        fact
        for fact in facts.facts_for_field("product.license")
        if fact.fact_id != facts.selected_fact_ids["product.license"]
    )

    decision = validate_claim_citations(
        facts,
        [
            TechnicalClaimV1(
                claim_id="same-rank-loser",
                surface_id="readme.license",
                text=str(losing.value),
                fact_ids=[losing.fact_id],
            )
        ],
    )

    assert facts.selected_fact("product.license").verification_state == "conflicting"
    assert decision.valid is False
    assert decision.invalid_claim_ids == ["same-rank-loser"]
