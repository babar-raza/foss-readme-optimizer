"""Orchestrate bounded, fact-backed README section operations."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.allocation import code_sha256
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.contextual_selection import select_contextual_links
from readme_agent.links.contextual_validation import validate_contextual_link_candidate
from readme_agent.links.terminology import find_enterprise_terminology_findings
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
from readme_agent.readme.document_header_visual import (
    build_badge_header_operations,
    build_comment_removal_operations,
    build_existing_overview_diagram_operations,
)
from readme_agent.readme.document_limitations import build_limitation_operations
from readme_agent.readme.document_link_hygiene import build_source_link_hygiene_operations
from readme_agent.readme.document_links import apply_contextual_link_bindings
from readme_agent.readme.document_opening import (
    build_opening_operations,
    build_promotional_callout_operations,
)
from readme_agent.readme.document_operations import (
    apply_document_operations,
    prune_noop_operations,
)
from readme_agent.readme.document_plan import (
    PresentationSpanAdoptionV1,
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_release import build_release_operations
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.document_terminology import (
    build_enterprise_terminology_operations,
    canonicalize_operation_terminology,
    enterprise_product_name,
)
from readme_agent.readme.header_visual import (
    has_marker_free_presentation_contract,
    render_readme_header_visual,
)
from readme_agent.readme.markers import find_presentation_span
from readme_agent.registry.models import LinkAllocationPolicyV1

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
    link_catalogs: AsposeLinkCatalogSetV1 | None = None,
    link_allocation_policy: LinkAllocationPolicyV1 | None = None,
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
    header_visuals = render_readme_header_visual(facts)
    operations: list[ReadmeDocumentOperationV1] = []
    operations.extend(build_opening_operations(context, validated_agentic_plan, header_visuals))
    operations.extend(build_existing_overview_diagram_operations(context, header_visuals))
    operations.extend(build_limitation_operations(context))
    operations.extend(build_acquisition_correction_operations(context))
    operations.extend(build_example_operations(context))
    operations.extend(build_promotional_callout_operations(context))
    operations.extend(build_registry_badge_operations(context))
    operations.extend(build_release_operations(context))
    # Equal-offset insertions appear in reverse plan order in the candidate.
    # Append the header operation last so badges remain immediately below H1.
    operations.extend(build_badge_header_operations(context, header_visuals))
    for comment_operation in build_comment_removal_operations(context):
        if not any(
            operation.source_byte_start < comment_operation.source_byte_end
            and comment_operation.source_byte_start < operation.source_byte_end
            for operation in operations
        ):
            operations.append(comment_operation)
    product_name = enterprise_product_name(facts)
    if (link_catalogs is None) != (link_allocation_policy is None):
        raise ValueError("README link catalogs and allocation policy must be supplied together")
    if link_catalogs is not None and link_allocation_policy is not None:
        operations.extend(
            build_source_link_hygiene_operations(
                context,
                operations,
                link_catalogs,
                link_allocation_policy,
            )
        )
    operations = canonicalize_operation_terminology(
        operations,
        product_name=product_name,
        identity_fact_id=facts.selected_fact("product.identity").fact_id,
    )
    terminology_operations, terminology_corrections = build_enterprise_terminology_operations(
        context,
        operations,
        product_name=product_name,
    )
    operations.extend(terminology_operations)
    contextual_links: ContextualLinkPlanV1 | None = None
    if link_catalogs is not None and link_allocation_policy is not None:
        pre_link_candidate = apply_document_operations(source, operations).decode("utf-8")
        example = facts.selected_fact("example.minimal")
        example_value = example.value if isinstance(example.value, dict) else {}
        example_code = str(example_value.get("code") or "").strip()
        contextual_links = select_contextual_links(
            facts,
            pre_link_candidate,
            link_catalogs,
            link_allocation_policy,
            verified_code_sha256s={code_sha256(example_code)} if example_code else set(),
        )
        operations = apply_contextual_link_bindings(context, operations, contextual_links)
        operations = prune_noop_operations(source, operations)
    if validated_agentic_plan is not None:
        validate_agentic_operation_coverage(
            assessment,
            validated_agentic_plan.section_decisions,
            operations,
        )
    rendered_inner = apply_document_operations(source, operations).decode("utf-8")
    terminology_findings = find_enterprise_terminology_findings(
        rendered_inner,
        enterprise_product_name=product_name,
    )
    if terminology_findings:
        raise ValueError("README candidate retains prohibited Enterprise Edition terminology")
    if contextual_links is not None and link_catalogs is not None:
        link_validation = validate_contextual_link_candidate(
            contextual_links,
            link_catalogs,
            rendered_inner,
            facts,
        )
        if not link_validation.valid:
            raise ValueError(
                "invalid contextual README links: " + "; ".join(link_validation.errors)
            )
    facts_hash = facts.canonical_hash()
    candidate = rendered_inner
    plan = ReadmeDocumentPlanV1(
        org_repo=org_repo,
        immutable_base_revision=base_revision,
        facts_hash=facts_hash,
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
        header_visuals=header_visuals,
        contextual_links=contextual_links,
        enterprise_terminology_corrections=terminology_corrections,
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
    )
    return candidate, plan
