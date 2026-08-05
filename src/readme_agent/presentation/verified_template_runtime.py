"""Orchestrate verified fact-slot compilation through existing document contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.allocation import code_sha256
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.contextual_selection import select_contextual_links
from readme_agent.links.contextual_validation import validate_contextual_link_candidate
from readme_agent.presentation.template_adapters import bind_product_facts
from readme_agent.presentation.template_compiler import compile_repository_presentation
from readme_agent.presentation.template_schema import PresentationTemplateInputV1
from readme_agent.presentation.verified_preservation_sections import (
    effective_correction_ranges,
    effective_preserve_ranges,
)
from readme_agent.presentation.verified_source_policy import build_verified_source_policy_edits
from readme_agent.presentation.verified_source_preservation import (
    compose_verified_source_preservation,
)
from readme_agent.presentation.verified_template_draft import build_verified_template_draft
from readme_agent.presentation.verified_template_provenance import (
    build_source_claim_resolutions,
    build_template_provenance,
    probe_source_claim_resolutions_for_composition,
)
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import ReadmeAssessmentV1, assess_readme_document
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    PresentationSpanAdoptionV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.header_visual import (
    has_marker_free_presentation_contract,
    render_readme_header_visual,
)
from readme_agent.readme.markers import find_presentation_span
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1
from readme_agent.registry.models import LinkAllocationPolicyV1
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
) -> VerifiedTemplateCompilationV1:
    """Return a compiled, validated, product-neutral verified presentation."""

    draft = build_verified_template_draft(
        facts,
        source_text,
        source_revision,
        agentic_plan,
        contextual_links,
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
    preserved_source_ranges = declared_preserve_ranges(assessment)
    correction_source_ranges = effective_correction_ranges(assessment)
    preliminary_resolutions = probe_source_claim_resolutions_for_composition(
        source_text,
        candidate,
        facts,
        provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=correction_source_ranges,
    )
    replaceable_claim_ids = {
        resolution.claim_id
        for resolution in preliminary_resolutions
        if resolution.resolution != "deferred_verification"
    }
    composition = compose_verified_source_preservation(
        candidate,
        source_text,
        assessment,
        replaceable_claim_ids,
        provenance,
        build_verified_source_policy_edits(source_text, facts),
    )
    candidate = composition.candidate
    return VerifiedTemplateCompilationV1(
        candidate=candidate,
        template_input=template_input,
        provenance=composition.provenance,
        source_placements=composition.source_placements,
        source_policy_corrections=composition.source_policy_corrections,
    )


def build_verified_template_document_candidate(
    facts: ProductFactsV2,
    source_text: str,
    source_revision: str,
    agentic_plan: ReadmeAgenticCompositionPlanV1,
    *,
    link_catalogs: AsposeLinkCatalogSetV1 | None = None,
    link_allocation_policy: LinkAllocationPolicyV1 | None = None,
) -> tuple[str, ReadmeDocumentPlanV1]:
    """Wrap the compiled fact-slot candidate in the existing plan/accountability contract."""

    if (link_catalogs is None) != (link_allocation_policy is None):
        raise ValueError("README link catalogs and allocation policy must be supplied together")
    contextual_links: ContextualLinkPlanV1 | None = None
    compiled = build_verified_template_compilation(
        facts, source_text, source_revision, agentic_plan
    )
    if link_catalogs is not None and link_allocation_policy is not None:
        example = facts.selected_fact("example.minimal")
        example_value = example.value if isinstance(example.value, dict) else {}
        example_code = str(example_value.get("code") or "").strip()
        contextual_links = select_contextual_links(
            facts,
            compiled.candidate,
            link_catalogs,
            link_allocation_policy,
            verified_code_sha256s={code_sha256(example_code)} if example_code else set(),
        )
        compiled = build_verified_template_compilation(
            facts,
            source_text,
            source_revision,
            agentic_plan,
            contextual_links,
        )
        link_validation = validate_contextual_link_candidate(
            contextual_links,
            link_catalogs,
            compiled.candidate,
            facts,
        )
        if not link_validation.valid:
            raise ValueError(
                "invalid contextual README links: " + "; ".join(link_validation.errors)
            )
    existing = find_presentation_span(source_text)
    inner_text = existing.content if existing is not None else source_text
    source = inner_text.encode("utf-8")
    candidate = compiled.candidate
    persisted_provenance = compiled.provenance if inner_text != candidate else []
    assessment = assess_readme_document(
        facts.org_repo,
        inner_text,
        facts,
        base_revision=source_revision,
    )
    if assessment.canonical_hash() != agentic_plan.assessment_hash:
        raise ValueError("verified template composition assessment binding changed")
    preserved_source_ranges = declared_preserve_ranges(assessment)
    source_claim_resolutions = build_source_claim_resolutions(
        inner_text,
        candidate,
        facts,
        persisted_provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=effective_correction_ranges(assessment),
        presentation_policy_corrections=compiled.source_policy_corrections,
    )
    operations = []
    if inner_text != candidate:
        operations.append(
            build_operation(
                operation_id="readme.verified-template.compile",
                operation="replace",
                source=source,
                start=0,
                end=len(source),
                replacement=candidate,
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    "Compile the accepted fact-slot presentation contract; exact candidate "
                    "provenance and source-claim resolutions remain independently fail-closed."
                ),
            )
        )
    operation_provenance = legacy_operation_provenance(replay_operation_origins(source, operations))
    complete_provenance = [*persisted_provenance, *operation_provenance]
    plan = ReadmeDocumentPlanV1(
        org_repo=facts.org_repo,
        immutable_base_revision=source_revision,
        facts_hash=facts.canonical_hash(),
        template_sha256=document_template_hash(),
        source_sha256=sha256_hex(source_text),
        adoption=PresentationSpanAdoptionV1(
            already_adopted=(
                existing is not None or has_marker_free_presentation_contract(source_text)
            ),
            marker_schema_version=3 if existing is not None and existing.facts_hash else None,
            source_document_sha256=sha256_hex(source_text),
            source_inner_sha256=sha256_hex(source),
            source_inner_bytes=len(source),
            preservation_check="byte_identical",
        ),
        header_visuals=render_readme_header_visual(facts, agentic_plan),
        contextual_links=contextual_links,
        candidate_content_provenance=complete_provenance,
        source_claim_resolutions=source_claim_resolutions,
        composition_ledger=build_composition_ledger(
            inner_text,
            candidate,
            operations,
            complete_provenance,
            compiled.source_placements,
        ),
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
    )
    claim_map = build_readme_claim_map(
        plan,
        facts,
        source_text=source_text,
        candidate_text=candidate,
    )
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=inner_text,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=claim_map,
        candidate_content_provenance=complete_provenance,
        source_claim_resolutions=plan.source_claim_resolutions,
    )
    return candidate, plan.model_copy(update={"claim_accountability": accountability})
