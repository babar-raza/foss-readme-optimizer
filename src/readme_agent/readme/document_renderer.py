"""Orchestrate bounded, fact-backed README section operations."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_validation import validate_readme_composition_plan
from readme_agent.readme.agentic_operation_coverage import (
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_acquisition import (
    build_acquisition_correction_operations,
    build_registry_badge_operations,
)
from readme_agent.readme.document_examples import build_example_operations
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_limitations import build_limitation_operations
from readme_agent.readme.document_opening import (
    build_opening_operations,
    build_promotional_callout_operations,
)
from readme_agent.readme.document_operations import apply_document_operations
from readme_agent.readme.document_plan import (
    PresentationSpanAdoptionV1,
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_release import build_release_operations
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.markers import find_presentation_span, render_presentation_span

__all__ = [
    "apply_document_operations",
    "build_readme_document_candidate",
    "document_template_hash",
]


def build_readme_document_candidate(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    *,
    base_revision: str,
    agentic_composition_plan: dict | None = None,
) -> tuple[str, ReadmeDocumentPlanV1]:
    """Return one reproducible candidate and its fine-grained source operations."""

    existing = find_presentation_span(source_text)
    inner_text = existing.content if existing is not None else source_text
    source = inner_text.encode("utf-8")
    context = DocumentRenderContext(
        org_repo=org_repo,
        source_text=source_text,
        inner_text=inner_text,
        source=source,
        facts=facts,
        base_revision=base_revision,
        headings=parse_headings(inner_text),
    )
    assessment = assess_readme_document(
        org_repo,
        source_text,
        facts,
        base_revision=base_revision,
    )
    validated_agentic_plan = (
        validate_readme_composition_plan(
            agentic_composition_plan,
            org_repo=org_repo,
            source_text=source_text,
            facts=facts,
            assessment=assessment,
        )
        if agentic_composition_plan
        else None
    )
    operations: list[ReadmeDocumentOperationV1] = []
    operations.extend(build_opening_operations(context, validated_agentic_plan))
    operations.extend(build_limitation_operations(context))
    operations.extend(build_acquisition_correction_operations(context))
    operations.extend(build_example_operations(context))
    operations.extend(build_promotional_callout_operations(context))
    operations.extend(build_registry_badge_operations(context))
    operations.extend(build_release_operations(context))
    if validated_agentic_plan is not None:
        validate_agentic_operation_coverage(
            assessment,
            validated_agentic_plan.section_decisions,
            operations,
        )
    rendered_inner = apply_document_operations(source, operations).decode("utf-8")
    facts_hash = facts.canonical_hash()
    candidate = render_presentation_span(rendered_inner, facts_hash)
    plan = ReadmeDocumentPlanV1(
        org_repo=org_repo,
        immutable_base_revision=base_revision,
        facts_hash=facts_hash,
        template_sha256=document_template_hash(),
        source_sha256=sha256_hex(source_text),
        adoption=PresentationSpanAdoptionV1(
            already_adopted=existing is not None,
            source_document_sha256=sha256_hex(source_text),
            source_inner_sha256=sha256_hex(source),
            source_inner_bytes=len(source),
            preservation_check="byte_identical",
        ),
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
    )
    return candidate, plan
