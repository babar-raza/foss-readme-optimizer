"""Finalize a legacy document candidate into its plan and accountability evidence."""

from __future__ import annotations

from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.terminology import EnterpriseTerminologyCorrectionV1
from readme_agent.presentation.verified_template_provenance import build_source_claim_resolutions
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import (
    PresentationSpanAdoptionV1,
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.header_visual import has_marker_free_presentation_contract
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1
from readme_agent.readme.markers import find_presentation_span


def finalize_legacy_document_candidate(
    context: DocumentRenderContext,
    candidate: str,
    operations: list[ReadmeDocumentOperationV1],
    header_visuals: ReadmeHeaderVisualV1,
    contextual_links: ContextualLinkPlanV1 | None,
    terminology_corrections: list[EnterpriseTerminologyCorrectionV1],
) -> tuple[str, ReadmeDocumentPlanV1]:
    """Bind exact operations, source loss, claims, and adoption to one candidate."""

    existing = find_presentation_span(context.source_text)
    source_claim_resolutions = build_source_claim_resolutions(
        context.inner_text,
        candidate,
        context.facts,
    )
    plan = ReadmeDocumentPlanV1(
        content_assurance=context.facts.content_assurance,
        org_repo=context.org_repo,
        immutable_base_revision=context.base_revision,
        facts_hash=context.facts.canonical_hash(),
        template_sha256=document_template_hash(),
        source_sha256=sha256_hex(context.source_text),
        adoption=PresentationSpanAdoptionV1(
            already_adopted=(
                existing is not None or has_marker_free_presentation_contract(context.source_text)
            ),
            marker_schema_version=3 if existing is not None and existing.facts_hash else None,
            source_document_sha256=sha256_hex(context.source_text),
            source_inner_sha256=sha256_hex(context.source),
            source_inner_bytes=len(context.source),
            preservation_check="byte_identical",
        ),
        header_visuals=header_visuals,
        contextual_links=contextual_links,
        enterprise_terminology_corrections=terminology_corrections,
        source_claim_resolutions=source_claim_resolutions,
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
    )
    generated_claim_map = build_readme_claim_map(
        plan,
        context.facts,
        source_text=context.source_text,
        candidate_text=candidate,
    )
    claim_accountability = build_readme_claim_accountability_map(
        org_repo=context.org_repo,
        source_text=context.inner_text,
        candidate_text=candidate,
        facts=context.facts,
        generated_claim_map=generated_claim_map,
        source_claim_resolutions=source_claim_resolutions,
    )
    return candidate, plan.model_copy(update={"claim_accountability": claim_accountability})
