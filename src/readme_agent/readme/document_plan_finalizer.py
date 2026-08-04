"""Finalize a legacy document candidate into its plan and accountability evidence."""

from __future__ import annotations

from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.terminology import EnterpriseTerminologyCorrectionV1
from readme_agent.presentation.verified_template_provenance import build_source_claim_resolutions
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import build_readme_claim_map
from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    PresentationSpanAdoptionV1,
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.fact_grounding import find_literal_fact_match
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
    operation_replay = replay_operation_origins(context.source, operations)
    operation_provenance = legacy_operation_provenance(operation_replay)
    candidate_provenance = list(operation_provenance)
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
        candidate_content_provenance=candidate_provenance,
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
    )
    operation_claim_map = build_readme_claim_map(
        plan,
        context.facts,
        source_text=context.source_text,
        candidate_text=candidate,
    )
    candidate_bytes = candidate.encode("utf-8")
    fact_provenance: list[CandidateContentProvenanceV1] = []
    for claim in operation_claim_map.claims:
        if claim.coordinate_space != "candidate_utf8":
            continue
        claim_text = candidate_bytes[claim.byte_start : claim.byte_end].decode("utf-8")
        selected = context.facts.fact_by_id(claim.fact_id)
        literal = find_literal_fact_match(claim_text, selected.value)
        if literal is None:
            continue
        literal_start = claim.byte_start + len(
            claim_text[: literal.character_start].encode("utf-8")
        )
        literal_end = claim.byte_start + len(claim_text[: literal.character_end].encode("utf-8"))
        fact_provenance.append(
            CandidateContentProvenanceV1(
                provenance_id=f"document-fact-coordinate.{claim.claim_id}",
                candidate_byte_start=literal_start,
                candidate_byte_end=literal_end,
                fact_ids=[claim.fact_id],
                rationale="Bind only the exact literal coordinates of one accepted fact.",
            )
        )
    candidate_provenance.extend(fact_provenance)
    plan = plan.model_copy(
        update={
            "candidate_content_provenance": candidate_provenance,
            "composition_ledger": build_composition_ledger(
                context.inner_text,
                candidate,
                operations,
                candidate_provenance,
            ),
        }
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
        candidate_content_provenance=candidate_provenance,
        source_claim_resolutions=source_claim_resolutions,
    )
    return candidate, plan.model_copy(update={"claim_accountability": claim_accountability})
