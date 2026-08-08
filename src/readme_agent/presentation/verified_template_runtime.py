"""Orchestrate verified fact-slot compilation through existing document contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.presentation.template_adapters import bind_product_facts
from readme_agent.presentation.template_compiler import compile_repository_presentation
from readme_agent.presentation.template_schema import PresentationTemplateInputV1
from readme_agent.presentation.verified_preservation_sections import (
    build_verified_source_preservation_selection,
    effective_correction_ranges,
    effective_preserve_ranges,
)
from readme_agent.presentation.verified_source_assurance_projection import (
    project_source_assurance_for_candidate,
)
from readme_agent.presentation.verified_source_policy import build_verified_source_policy_edits
from readme_agent.presentation.verified_source_preservation import (
    compose_verified_source_preservation,
)
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_provenance import (
    build_template_provenance,
    probe_source_claim_resolutions_for_composition,
)
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import ReadmeAssessmentV1, assess_readme_document
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
)
from readme_agent.readme.source_claim_assurance import build_source_claim_assurance
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1
from readme_agent.validation.presentation_template import validate_repository_presentation


class VerifiedTemplateCompilationV1(BaseModel):
    """Compiled bytes plus exact fact/standard spans used by claim accountability."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: str
    template_input: PresentationTemplateInputV1
    provenance: list[CandidateContentProvenanceV1]
    source_placements: list[ExactSourcePlacementV1]
    source_policy_corrections: list[SourceClaimPolicyCorrectionV1]


def declared_preserve_ranges(
    assessment: ReadmeAssessmentV1,
) -> list[tuple[int, int]]:
    """Return leaf-owned preserve ranges without container/child authority overlap."""

    return effective_preserve_ranges(assessment)


def build_verified_template_compilation(
    facts: ProductFactsV2,
    source_text: str,
    source_revision: str,
    agentic_plan: ReadmeAgenticCompositionPlanV1,
    contextual_links: ContextualLinkPlanV1 | None = None,
    documentation_link_limit: int | None = None,
) -> VerifiedTemplateCompilationV1:
    """Return a compiled, validated, product-neutral verified presentation."""

    draft = build_verified_template_draft(
        facts,
        source_text,
        source_revision,
        agentic_plan,
        contextual_links,
        documentation_link_limit,
    )
    template_input = bind_product_facts(facts, draft)
    candidate = compile_repository_presentation(template_input)
    errors = validate_repository_presentation(candidate, template_input)
    if errors:
        raise ValueError("compiled verified presentation is invalid: " + "; ".join(errors))
    provenance = build_template_provenance(candidate, template_input, facts)
    assessment = assess_readme_document(
        facts.org_repo,
        source_text,
        facts,
        base_revision=source_revision,
    )
    if assessment.canonical_hash() != agentic_plan.assessment_hash:
        raise ValueError("verified template composition assessment binding changed")
    source_assurance = project_source_assurance_for_candidate(
        source_text,
        assessment,
        build_source_claim_assurance(source_text, facts, assessment),
        provenance,
        candidate,
    )
    preserved_source_ranges = source_assurance.preserve_ranges
    correction_source_ranges = [
        *effective_correction_ranges(assessment),
        *source_assurance.correction_ranges,
    ]
    preliminary_resolutions = probe_source_claim_resolutions_for_composition(
        source_text,
        candidate,
        facts,
        provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=correction_source_ranges,
    )
    resolved_claim_ids = {
        resolution.claim_id
        for resolution in preliminary_resolutions
        if resolution.resolution
        in {
            "deferred_verification",
            "verified_equivalence",
            "verified_omission",
            "verified_obligation_replacement",
        }
    }
    preservation_selection = build_verified_source_preservation_selection(
        source_text,
        assessment,
        fact_authorized_ranges=source_assurance.preserve_ranges,
        correction_candidate_ranges=source_assurance.correction_ranges,
        resolved_claim_ids=resolved_claim_ids,
    )
    composition = compose_verified_source_preservation(
        candidate,
        source_text,
        facts,
        assessment,
        resolved_claim_ids,
        provenance,
        build_verified_source_policy_edits(source_text, facts),
        preservation_selection=preservation_selection,
    )
    candidate = composition.candidate
    return VerifiedTemplateCompilationV1(
        candidate=candidate,
        template_input=template_input,
        provenance=composition.provenance,
        source_placements=composition.source_placements,
        source_policy_corrections=composition.source_policy_corrections,
    )
