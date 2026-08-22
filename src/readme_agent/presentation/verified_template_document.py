"""Build the final verified README document and its accountability plan."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.allocation import code_sha256
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.contextual_selection import select_contextual_links
from readme_agent.links.contextual_validation import validate_contextual_link_candidate
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.presentation.verified_preservation_sections import effective_correction_ranges
from readme_agent.presentation.verified_source_assurance_projection import (
    project_source_assurance_for_candidate,
)
from readme_agent.presentation.verified_template_link_budget import documentation_link_limit
from readme_agent.presentation.verified_template_provenance import build_source_claim_resolutions
from readme_agent.presentation.verified_template_runtime import build_verified_template_compilation
from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import PresentationSpanAdoptionV1, ReadmeDocumentPlanV1
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.header_visual import (
    has_marker_free_presentation_contract,
    render_readme_header_visual,
)
from readme_agent.readme.markers import find_presentation_span
from readme_agent.readme.source_claim_assurance import build_source_claim_assurance
from readme_agent.registry.models import LinkAllocationPolicyV1
from readme_agent.specialists.section_authoring_contracts import SectionAuthoringDocumentV1


def build_verified_template_document_candidate(
    facts: ProductFactsV2,
    source_text: str,
    source_revision: str,
    agentic_plan: ReadmeAgenticCompositionPlanV1,
    *,
    link_catalogs: AsposeLinkCatalogSetV1 | None = None,
    link_allocation_policy: LinkAllocationPolicyV1 | None = None,
    llm_disposition_client: ForcedToolClient | None = None,
    repository_root: Path | None = None,
    disposition_ratchet_path: Path | None = None,
    section_authoring_document: SectionAuthoringDocumentV1 | None = None,
) -> tuple[str, ReadmeDocumentPlanV1]:
    """Wrap the compiled fact-slot candidate in the plan/accountability contract.

    `llm_disposition_client`/`repository_root` are forwarded, unchanged, to
    `build_readme_claim_accountability_map()` -- see that function's own
    docstring. Omitting either (the default) reproduces today's exact
    existing behavior."""

    if (link_catalogs is None) != (link_allocation_policy is None):
        raise ValueError("README link catalogs and allocation policy must be supplied together")
    contextual_links: ContextualLinkPlanV1 | None = None
    compiled = build_verified_template_compilation(
        facts,
        source_text,
        source_revision,
        agentic_plan,
        section_authoring_document=section_authoring_document,
    )
    if link_catalogs is not None and link_allocation_policy is not None:
        example = facts.selected_fact("example.minimal")
        example_value = example.value if isinstance(example.value, dict) else {}
        example_code = str(example_value.get("code") or "").strip()
        verified_codes = {code_sha256(example_code)} if example_code else set()
        documentation_limit = documentation_link_limit(
            compiled.candidate,
            facts,
            link_catalogs,
            link_allocation_policy,
            verified_code_sha256s=verified_codes,
        )
        compiled = build_verified_template_compilation(
            facts,
            source_text,
            source_revision,
            agentic_plan,
            documentation_link_limit=documentation_limit,
            section_authoring_document=section_authoring_document,
        )
        contextual_links = select_contextual_links(
            facts,
            compiled.candidate,
            link_catalogs,
            link_allocation_policy,
            verified_code_sha256s=verified_codes,
        )
        compiled = build_verified_template_compilation(
            facts,
            source_text,
            source_revision,
            agentic_plan,
            contextual_links,
            documentation_link_limit=documentation_limit,
            section_authoring_document=section_authoring_document,
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
    source_assurance = project_source_assurance_for_candidate(
        inner_text,
        assessment,
        build_source_claim_assurance(inner_text, facts, assessment),
        persisted_provenance,
        facts,
        candidate,
    )
    source_claim_resolutions = build_source_claim_resolutions(
        inner_text,
        candidate,
        facts,
        persisted_provenance,
        preserved_source_ranges=source_assurance.preserve_ranges,
        authoritative_correction_ranges=[
            *effective_correction_ranges(assessment),
            *source_assurance.correction_ranges,
        ],
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
    composition_ledger = build_composition_ledger(
        inner_text,
        candidate,
        operations,
        complete_provenance,
        compiled.source_placements,
    )
    plan = ReadmeDocumentPlanV1(
        org_repo=facts.org_repo,
        immutable_base_revision=source_revision,
        facts_hash=facts.canonical_hash(),
        section_authoring_document_sha256=(
            section_authoring_document.canonical_hash()
            if section_authoring_document is not None
            else None
        ),
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
        composition_ledger=composition_ledger,
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
        compiled_slot_blocks=compiled.compiled_slot_blocks,
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
        llm_disposition_client=llm_disposition_client,
        repository_root=repository_root,
        disposition_ratchet_path=disposition_ratchet_path,
        composition_ledger=composition_ledger,
    )
    return candidate, plan.model_copy(update={"claim_accountability": accountability})


__all__ = ["build_verified_template_document_candidate"]
