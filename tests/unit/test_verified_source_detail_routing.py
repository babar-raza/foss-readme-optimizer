"""Verify valuable source detail is routed by meaning, never dumped generically."""

from __future__ import annotations

from unittest.mock import patch

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_preservation_sections import PreservedBlock
from readme_agent.presentation.verified_source_detail_routing import (
    route_source_detail_blocks,
    source_section_routes_to_canonical_contract,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_coordinates import structured_list_item_coordinate
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import parse_headings
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


def test_multiple_source_details_share_one_parsed_heading_context() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = (
        "# Aspose.Widget FOSS for Python\n\n"
        "## Currently Available Features\n\n"
        "- Convert PS and EPS files to PDF while retaining page geometry.\n"
        "- Extract text from text-based PDF pages.\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    source_bytes = source.encode("utf-8")
    blocks = [
        PreservedBlock(
            markdown=source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8"),
            source_owner_id=claim.claim_id,
            source_byte_start=claim.source_byte_start,
            source_byte_end=claim.source_byte_end,
        )
        for claim in assessment.material_claims
    ]

    with patch(
        "readme_agent.readme.source_claim_risk.parse_headings",
        wraps=parse_headings,
    ) as heading_parser:
        routed = route_source_detail_blocks(source, assessment, facts, blocks, "", [])

    assert sum(call.args == (source,) for call in heading_parser.call_args_list) == 1
    assert routed == {("Key Capabilities", "View Detailed Capabilities"): blocks}


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
        fact_coordinates=list(source_binding.fact_coordinates),
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


def test_directional_format_capability_is_not_repeated_as_source_detail() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["Render pages to PNG or TIFF"]})
                if fact.fact_id == capability.fact_id
                else fact.model_copy(
                    update={
                        "value": [
                            "Input format: PDF",
                            "Output format: PDF",
                            "Output format: PNG",
                            "Output format: TIFF",
                        ]
                    }
                )
                if fact.fact_id == formats.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n\n## Features\n\n- Render pages to PNG or TIFF\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    source_claim = assessment.material_claims[0]
    block = PreservedBlock(
        markdown="- Render pages to PNG or TIFF\n",
        source_owner_id=source_claim.claim_id,
        source_byte_start=source_claim.source_byte_start,
        source_byte_end=source_claim.source_byte_end,
    )
    candidate = (
        "# Product\n\n## Key Capabilities\n\n"
        "- **Render pages to PNG or TIFF** - Produce PNG and TIFF image output.\n"
    )
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:render",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[capability.fact_id, formats.fact_id],
        fact_coordinates=[
            structured_list_item_coordinate(
                capability.fact_id,
                capability.field,
                "Render pages to PNG or TIFF",
            ),
            *[
                structured_list_item_coordinate(formats.fact_id, formats.field, value)
                for value in ("Output format: PNG", "Output format: TIFF")
            ],
        ],
        rationale="Bind one canonical directional capability to exact fact items.",
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


def test_component_identical_capability_detail_is_not_repeated() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    identity = facts.selected_fact("product.identity")
    label = "Read Word 97-2003 DOC binary documents with olefile"
    capability = capability.model_copy(update={"value": [label]})
    implementation = FactRecordV2(
        fact_id="repository.implementation_components:python-test",
        field="repository.implementation_components",
        value={
            "components": [],
            "capability_groups": [
                {
                    "label": label,
                    "format": "DOC",
                    "roles": ["read"],
                    "component_indexes": [0],
                    "stdlib_imports": [],
                    "runtime_imports": ["olefile"],
                    "source_summary": "Core reader for Word 97-2003 DOC binary files.",
                }
            ],
        },
        source=identity.source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.capabilities"],
    )
    facts = facts.model_copy(
        update={
            "facts": [
                *[
                    capability if fact.fact_id == capability.fact_id else fact
                    for fact in facts.facts
                ],
                implementation,
            ],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                implementation.field: implementation.fact_id,
            },
        }
    )
    source = (
        "# Product\n\n## Features\n\n- **DOC Support**: Word 97-2003 binary reader via `olefile`\n"
    )
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    source_claim = assessment.material_claims[0]
    source_bytes = source.encode("utf-8")
    block = PreservedBlock(
        markdown=source_bytes[source_claim.source_byte_start : source_claim.source_byte_end].decode(
            "utf-8"
        ),
        source_owner_id=source_claim.claim_id,
        source_byte_start=source_claim.source_byte_start,
        source_byte_end=source_claim.source_byte_end,
    )
    candidate = (
        "# Product\n\n## Key Capabilities\n\n"
        "- **Read Word 97-2003 DOC binary documents with olefile** - "
        "Parse legacy Word binary files through the repository's olefile-backed reader.\n"
    )
    candidate_claim = assess_material_claims(candidate)[0]
    candidate_binding = complete_source_claim_fact_binding(candidate, candidate_claim, facts)
    assert candidate_binding is not None
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.key_capabilities.claim:doc",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=sorted(candidate_binding.fact_ids),
        fact_coordinates=list(candidate_binding.fact_coordinates),
        rationale="Bind the canonical capability row to exact implementation evidence.",
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


def test_verified_public_guidance_routes_by_enclosing_source_section() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    identity = facts.selected_fact("product.identity")
    guidance = FactRecordV2(
        fact_id="repository.public_guidance:unicode-fonts",
        field="repository.public_guidance",
        value=[
            "For Unicode outside the Standard-14 encodings, provide an embeddable "
            "TrueType/OpenType font as bytes, a path, or a `FontDescriptor`:"
        ],
        source=identity.source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.examples"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, guidance],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                guidance.field: guidance.fact_id,
            },
        }
    )
    source = (
        "# AcmePDF Python\n\n"
        "## Quick Start\n\n"
        "### Unicode Text\n\n"
        "For Unicode outside the Standard-14 encodings, provide an embeddable "
        "TrueType/OpenType font as bytes, a path, or a `FontDescriptor`:\n"
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

    assert routed == {("Quick Start", "View Additional Quick Start Details"): [block]}
