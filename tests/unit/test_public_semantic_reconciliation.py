"""Regress fact-bound capability and limitation reconciliation."""

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_preservation_sections import PreservedBlock
from readme_agent.presentation.verified_source_claim_matching import (
    equivalent_source_claim_resolution,
    index_equivalent_candidate_claims,
)
from readme_agent.presentation.verified_source_detail_routing import route_source_detail_blocks
from readme_agent.presentation.verified_template_capabilities import capability_highlights_markdown
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.capability_semantics import normalize_capability_phrases
from readme_agent.readme.claim_accountability_coordinates import structured_list_item_coordinate
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.limitation_semantics import public_limitations_equivalent
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.public_limitations import (
    public_limitation_fact_coordinates,
    public_limitation_phrases,
)


def _facts_with_limitations(values: list[str]) -> ProductFactsV2:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    limitation = facts.selected_fact("product.limitations")
    return facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": values})
                if fact.fact_id == limitation.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )


def test_capability_normalization_keeps_distinct_pdf_domains() -> None:
    values = [
        "Create, load, save, merge, split, and inspect PDF documents",
        "Create and inspect PDF signatures",
        "Extract text, images, attachments, metadata, and bookmarks",
        "XMP metadata handling",
        "Digital signature support",
    ]

    normalized = normalize_capability_phrases(values)

    assert normalized == values[:-1]


def test_capability_renderer_keeps_document_lifecycle_and_signatures_distinct() -> None:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capability = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": [
                            "Create, load, save, merge, split, and inspect PDF documents",
                            "Create and inspect PDF signatures",
                            "Digital signature support",
                        ]
                    }
                )
                if fact.fact_id == capability.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = "## Features\n\n- Create and inspect PDF signatures\n"

    rendered = capability_highlights_markdown(facts, source_text=source)

    assert rendered is not None
    assert "**Create and manage PDF documents**" in rendered
    assert "**Work with PDF digital signatures**" in rendered
    assert rendered.count("signatures") == 1


def test_fact_bound_canonical_limitation_suppresses_only_equivalent_source_detail() -> None:
    canonical = (
        "Page rendering supports common page content; it is not represented as complete "
        "PDF graphics coverage."
    )
    facts = _facts_with_limitations([canonical])
    limitation = facts.selected_fact("product.limitations")
    source = (
        "# Aspose.PDF FOSS for Python\n\n"
        "## Scope and Limitations\n\n"
        "- Page rendering is best effort and does not implement every PDF graphics feature.\n"
    )
    assessment = assess_readme_document(facts.org_repo, source, facts, base_revision="a" * 40)
    claim = assessment.material_claims[0]
    source_bytes = source.encode("utf-8")
    block = PreservedBlock(
        markdown=source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8"),
        source_owner_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
    )
    candidate = f"# Product\n\n## Scope and Limitations\n\n- {canonical}\n"
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.scope_and_limitations.claim:test",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[limitation.fact_id],
        fact_coordinates=[
            structured_list_item_coordinate(
                limitation.fact_id,
                limitation.field,
                canonical,
            )
        ],
        rationale="Bind the canonical public limitation to its exact fact item.",
    )

    routed = route_source_detail_blocks(
        source,
        assessment,
        facts,
        [block],
        candidate,
        [provenance],
    )
    resolution = equivalent_source_claim_resolution(
        claim,
        block.markdown,
        candidate.encode("utf-8"),
        index_equivalent_candidate_claims(candidate.encode("utf-8"), [candidate_claim]),
        facts,
        [provenance],
    )

    assert routed == {}
    assert resolution is not None
    assert resolution.resolution == "verified_equivalence"
    assert limitation.fact_id in resolution.fact_ids


def test_limitation_equivalence_rejects_distinct_constraints() -> None:
    assert not public_limitations_equivalent(
        "Page rendering is best effort and does not implement every PDF graphics feature.",
        "PDF/A validation is heuristic, not certification-grade.",
    )
    assert not public_limitations_equivalent(
        "OCR is not implemented.",
        "Layout reflow is not implemented.",
    )


def test_complementary_coverage_constraints_render_and_resolve_once() -> None:
    source_values = [
        "Compatibility surfaces may name features that are unavailable and must fail explicitly.",
        (
            "The documented feature set is bounded by the active test suite rather than every "
            "exposed compatibility name."
        ),
    ]
    facts = _facts_with_limitations(source_values)
    limitation = facts.selected_fact("product.limitations")
    public_text = "Unsupported operations fail explicitly, but coverage is not yet complete."

    assert public_limitation_phrases(facts) == [public_text]
    assert len(public_limitation_fact_coordinates(public_text, limitation.fact_id, facts)) == 2

    source = (
        "# Aspose.PDF FOSS for Python\n\n"
        "## Scope and Limitations\n\n"
        "This project aims to fail explicitly when an operation is unsupported, but PDF\n"
        "is a large format and coverage is not yet complete.\n"
    )
    assessment = assess_readme_document(facts.org_repo, source, facts, base_revision="a" * 40)
    claim = assessment.material_claims[0]
    source_bytes = source.encode("utf-8")
    block = PreservedBlock(
        markdown=source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8"),
        source_owner_id=claim.claim_id,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
    )
    candidate = f"# Product\n\n## Scope and Limitations\n\n- {public_text}\n"
    candidate_claim = assess_material_claims(candidate)[0]
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.scope_and_limitations.claim:coverage",
        candidate_byte_start=candidate_claim.source_byte_start,
        candidate_byte_end=candidate_claim.source_byte_end,
        fact_ids=[limitation.fact_id],
        fact_coordinates=public_limitation_fact_coordinates(
            public_text,
            limitation.fact_id,
            facts,
        ),
        rationale="Bind both accepted coverage constraints to one public limitation.",
    )

    routed = route_source_detail_blocks(
        source,
        assessment,
        facts,
        [block],
        candidate,
        [provenance],
    )
    resolution = equivalent_source_claim_resolution(
        claim,
        block.markdown,
        candidate.encode("utf-8"),
        index_equivalent_candidate_claims(candidate.encode("utf-8"), [candidate_claim]),
        facts,
        [provenance],
    )

    assert routed == {}
    assert resolution is not None
    assert resolution.resolution == "verified_equivalence"
    assert resolution.candidate_claim_id == candidate_claim.claim_id


def test_presentation_lint_rejects_semantically_repeated_limitations() -> None:
    candidate = (
        """# Aspose.PDF FOSS for Python

## Scope and Limitations

"""
        "- Page rendering supports common page content; it is not represented as complete "
        "PDF graphics coverage.\n"
        "- Page rendering is best effort and does not implement every PDF graphics feature.\n"
    )

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert any(finding.rule_id == "semantic_duplicate" for finding in result.findings)
