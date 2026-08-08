"""Verify valuable source detail is routed by meaning, never dumped generically."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_preservation_sections import PreservedBlock
from readme_agent.presentation.verified_source_detail_routing import (
    route_source_detail_blocks,
    source_section_routes_to_canonical_contract,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding


def test_major_capability_detail_routes_to_key_capabilities() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = (
        "# Aspose.Widget FOSS for Python\n\n"
        "## Currently Available Features\n\n"
        "- Convert PS and EPS files to PDF while retaining page geometry.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    claim = assessment.material_claims[0]
    source_bytes = source.encode("utf-8")
    block = PreservedBlock(
        markdown=source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8"),
        source_owner_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
    )

    routed = route_source_detail_blocks(source, assessment, facts, [block], "", [])

    assert routed == {("Key Capabilities", "View Detailed Capabilities"): [block]}


def test_complete_capability_section_routes_into_canonical_contract() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = (
        "# AcmePDF Python\n\n## Why This Product\n\n- Extract text from text-based PDF pages.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    section = next(item for item in assessment.sections if item.level == 2)

    assert source_section_routes_to_canonical_contract(
        source,
        assessment,
        facts,
        section.source_byte_start,
        section.source_byte_end,
    )


def test_fact_identical_capability_detail_is_not_repeated() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = "# AcmePDF Python\n\n## Features\n\n- Extract text from text-based PDF pages\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    source_claim = assessment.material_claims[0]
    block = PreservedBlock(
        markdown=source.encode("utf-8")[
            source_claim.source_byte_start : source_claim.source_byte_end
        ].decode("utf-8"),
        source_owner_id=source_claim.claim_id,
        source_byte_start=source_claim.source_byte_start,
        source_byte_end=source_claim.source_byte_end,
    )
    candidate = (
        "# AcmePDF Python\n\n## Key Capabilities\n\n"
        "- **Extract text from text-based PDF pages with AcmePDF Python** - "
        "Supports extracting text from text-based PDF pages.\n"
    )
    candidate_claim = assess_material_claims(candidate)[0]
    source_binding = complete_source_claim_fact_binding(source, source_claim, facts)
    assert source_binding is not None
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:test",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=sorted(source_binding.fact_ids),
        rationale="Bind the canonical capability row to accepted repository facts.",
    )

    routed = route_source_detail_blocks(
        source,
        assessment,
        facts,
        [block],
        candidate,
        [provenance],
    )

    assert routed == {}
