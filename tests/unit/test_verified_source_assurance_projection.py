"""Prove inherited detail is suppressed only by exact canonical coordinate coverage."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_source_assurance_projection import (
    project_source_assurance_for_candidate,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_assurance import SourceClaimAssurance
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding


def _projection_inputs():
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    capabilities = facts.selected_fact("product.capabilities")
    capabilities = capabilities.model_copy(
        update={"verification_state": "verified", "value": ["Render verified widgets"]}
    )
    facts = facts.model_copy(
        update={
            "facts": [
                capabilities if fact.fact_id == capabilities.fact_id else fact
                for fact in facts.facts
            ]
        }
    )
    source = "# Product\n\n## Key Capabilities\n\n- Render verified widgets\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    source_bytes = source.encode("utf-8")
    claim = next(
        item
        for item in assessment.material_claims
        if "Render verified widgets"
        in source_bytes[item.source_byte_start : item.source_byte_end].decode("utf-8")
    )
    binding = complete_source_claim_fact_binding(source, claim, facts)
    assert binding is not None
    assurance = SourceClaimAssurance(
        preserve_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        correction_ranges=[],
        fact_authorized_claim_count=1,
        correction_candidate_count=0,
    )
    return facts, source, assessment, claim, binding, assurance


def test_exact_canonical_coordinates_replace_inherited_detail_without_duplication() -> None:
    facts, source, assessment, claim, binding, assurance = _projection_inputs()
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.key_capabilities.claim:render-widgets",
            candidate_byte_start=0,
            candidate_byte_end=25,
            fact_ids=sorted(binding.fact_ids),
            fact_coordinates=list(binding.fact_coordinates),
            rationale="Render the exact accepted capability once in the canonical section.",
        )
    ]

    projected = project_source_assurance_for_candidate(
        source,
        assessment,
        assurance,
        provenance,
        facts,
    )

    span = (claim.source_byte_start, claim.source_byte_end)
    assert projected.preserve_ranges == []
    assert projected.correction_ranges == [span]
    assert projected.fact_authorized_claim_count == 0
    assert projected.correction_candidate_count == 1


def test_fact_id_without_exact_coordinates_cannot_suppress_inherited_detail() -> None:
    facts, source, assessment, claim, binding, assurance = _projection_inputs()
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.key_capabilities.claim:render-widgets",
            candidate_byte_start=0,
            candidate_byte_end=25,
            fact_ids=sorted(binding.fact_ids),
            rationale="A broad fact citation is not exact semantic coverage.",
        )
    ]

    projected = project_source_assurance_for_candidate(
        source,
        assessment,
        assurance,
        provenance,
        facts,
    )

    span = (claim.source_byte_start, claim.source_byte_end)
    assert projected.preserve_ranges == [span]
    assert projected.correction_ranges == []
