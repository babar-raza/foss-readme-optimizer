"""Facts-only README-section readiness: section sufficiency, not corpus
completeness -- a repository does not need every claim to verify, only
enough accepted facts to cover each required section."""

from __future__ import annotations

from readme_agent.facts.readme_facts_readiness import (
    REQUIRED_README_SECTIONS,
    build_repository_facts_readiness,
)
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2

_ORG_REPO = "acme/widget"
_SOURCE = FactSourceV2(
    source_type="mechanical_repository",
    location="repository://acme/widget",
    source_revision="a" * 40,
)


def _facts(records: list[FactRecordV2]):
    return resolve_product_facts(
        _ORG_REPO, records, missing_source=_SOURCE, missing_field_surfaces={}
    )


def _fact(
    field: str,
    value: object,
    *,
    surfaces: list[str],
    verification_state: str = "verified",
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:test",
        field=field,
        value=value,
        source=_SOURCE,
        verification_state=verification_state,  # type: ignore[arg-type]
        authoritative_owner="repository",
        confidence=1.0 if verification_state == "verified" else 0.4,
        affected_surfaces=surfaces,
    )


def test_all_nine_required_sections_are_declared():
    assert len(REQUIRED_README_SECTIONS) == 9


def test_section_with_no_accepted_fact_is_blocked():
    facts = _facts([])

    readiness = build_repository_facts_readiness(
        facts,
        family="widget",
        platform="python",
        source_revision="a" * 40,
        knowledge_revision=None,
        freshness="current",
    )

    for section in readiness.sections:
        assert section.status == "BLOCKED_FACTS"
    assert readiness.overall_status == "BLOCKED_FACTS"


def test_section_with_an_accepted_fact_is_ready():
    facts = _facts(
        [_fact("product.capabilities", ["Exports widgets"], surfaces=["readme.capabilities"])]
    )

    readiness = build_repository_facts_readiness(
        facts,
        family="widget",
        platform="python",
        source_revision="a" * 40,
        knowledge_revision=None,
        freshness="current",
    )

    capabilities = readiness.section("key_capabilities_formats")
    assert capabilities.status == "READY"
    assert capabilities.accepted_fact_ids


def test_section_with_a_conflicting_fact_alongside_accepted_evidence_is_degraded():
    facts = _facts(
        [
            _fact("product.formats", ["OBJ"], surfaces=["readme.capabilities"]),
            _fact(
                "aspose.format_support_claims",
                "conflicting",
                surfaces=["readme.capabilities"],
                verification_state="conflicting",
            ),
        ]
    )

    readiness = build_repository_facts_readiness(
        facts,
        family="widget",
        platform="python",
        source_revision="a" * 40,
        knowledge_revision=None,
        freshness="current",
    )

    capabilities = readiness.section("key_capabilities_formats")
    assert capabilities.status == "DEGRADED_PRESERVE_SOURCE"
    assert capabilities.conflicting_fact_ids


def test_section_sufficiency_not_corpus_completeness():
    """A repository is READY for a section from a small number of accepted
    facts -- it does not need every possible claim in that section's
    surface to verify, only enough to be useful."""

    facts = _facts(
        [
            _fact("product.identity", "Widget", surfaces=["readme.opening"]),
            _fact("installation.coordinates", {"name": "widget"}, surfaces=["readme.installation"]),
            _fact("example.minimal", {"code": "widget.export()"}, surfaces=["readme.example"]),
            _fact("product.license", "MIT", surfaces=["readme.license"]),
        ]
    )

    readiness = build_repository_facts_readiness(
        facts,
        family="widget",
        platform="python",
        source_revision="a" * 40,
        knowledge_revision="b" * 40,
        freshness="current",
    )

    assert readiness.section("identity_and_purpose").status == "READY"
    assert readiness.section("installation_coordinates").status == "READY"
    assert readiness.section("verified_example_availability").status == "READY"
    assert readiness.section("mit_policy_statement").status == "READY"
    # Sections with genuinely no accepted evidence still block honestly.
    assert readiness.section("public_api_reference").status == "BLOCKED_FACTS"
    assert readiness.overall_status == "BLOCKED_FACTS"


def test_verified_limitations_are_tracked_separately_from_generic_acceptance():
    facts = _facts(
        [
            _fact(
                "product.limitations",
                ["Does not support gadgets"],
                surfaces=["readme.limitations"],
            )
        ]
    )

    readiness = build_repository_facts_readiness(
        facts,
        family="widget",
        platform="python",
        source_revision="a" * 40,
        knowledge_revision=None,
        freshness="current",
    )

    limitations = readiness.section("scope_and_limitations")
    assert limitations.status == "READY"
    assert limitations.verified_limitation_fact_ids
