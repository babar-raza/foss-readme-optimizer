"""Orchestrate bounded, fact-backed README section operations."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.allocation import code_sha256
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.links.contextual_selection import select_contextual_links
from readme_agent.links.contextual_validation import validate_contextual_link_candidate
from readme_agent.links.terminology import (
    EnterpriseTerminologyCorrectionV1,
    find_enterprise_terminology_findings,
)
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.presentation.runtime_repairs import build_density_collapse_operations
from readme_agent.presentation.verified_template_document import (
    build_verified_template_document_candidate,
)
from readme_agent.readme.agentic_composition_validation import validate_readme_composition_plan
from readme_agent.readme.agentic_operation_coverage import (
    validate_agentic_operation_coverage,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_acquisition import (
    build_acquisition_correction_operations,
    build_registry_badge_operations,
)
from readme_agent.readme.document_core_opening import build_core_opening_operations
from readme_agent.readme.document_examples import (
    build_additional_examples_collapse_operations,
    build_example_operations,
)
from readme_agent.readme.document_header_visual import (
    build_badge_header_operations,
    build_comment_removal_operations,
    build_existing_overview_diagram_operations,
)
from readme_agent.readme.document_legal import (
    build_license_operations,
    build_third_party_notice_operations,
)
from readme_agent.readme.document_limitations import build_limitation_operations
from readme_agent.readme.document_link_hygiene import build_source_link_hygiene_operations
from readme_agent.readme.document_links import apply_contextual_link_bindings
from readme_agent.readme.document_navigation import finalize_navigation_operations
from readme_agent.readme.document_opening import (
    build_promotional_callout_operations,
)
from readme_agent.readme.document_operations import (
    apply_document_operations,
    prune_noop_operations,
)
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_plan_finalizer import finalize_legacy_document_candidate
from readme_agent.readme.document_presentation_repairs import (
    build_presentation_policy_operations,
    canonicalize_operation_decorations,
    commercial_directory_spans,
)
from readme_agent.readme.document_reconciliation import (
    build_unresolved_section_operations,
    remove_operations_overlapping_withheld_sections,
)
from readme_agent.readme.document_release import build_release_operations
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_review_repairs import build_review_repair_operations
from readme_agent.readme.document_section_journey import build_core_section_journey_operations
from readme_agent.readme.document_section_order import enforce_canonical_section_order
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.readme.document_terminology import (
    build_enterprise_terminology_operations,
    canonicalize_operation_terminology,
    enterprise_product_name,
)
from readme_agent.readme.header_visual import render_readme_header_visual
from readme_agent.readme.markers import find_presentation_span
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.public_text import canonical_abbreviations_from_facts
from readme_agent.registry.models import LinkAllocationPolicyV1
from readme_agent.specialists.section_authoring_contracts import SectionAuthoringDocumentV1

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
    llm_disposition_client: ForcedToolClient | None = None,
    repository_root: Path | None = None,
    disposition_ratchet_path: Path | None = None,
    section_authoring_document: SectionAuthoringDocumentV1 | dict | None = None,
) -> tuple[str, ReadmeDocumentPlanV1]:
    """Return one reproducible candidate and its fine-grained source operations.

    `llm_disposition_client`/`repository_root` reach the verified-template
    path's claim-accountability build only -- see
    `verified_template_document.py::build_verified_template_document_
    candidate`'s own docstring. Omitting either (the default) reproduces
    today's exact existing behavior on every path."""

    existing = find_presentation_span(source_text)
    inner_text = existing.content if existing is not None else source_text
    source = inner_text.encode("utf-8")
    headings = [
        replace(heading, title=strip_emoji_decorations(heading.title))
        for heading in parse_headings(inner_text)
    ]
    context = DocumentRenderContext(
        org_repo=org_repo,
        source_text=source_text,
        inner_text=inner_text,
        source=source,
        facts=facts,
        base_revision=base_revision,
        headings=headings,
    )
    assessment = assess_readme_document(
        org_repo,
        inner_text,
        facts,
        base_revision=base_revision,
    )
    if (link_catalogs is None) != (link_allocation_policy is None):
        raise ValueError("README link catalogs and allocation policy must be supplied together")
    validated_agentic_plan = (
        validate_readme_composition_plan(
            agentic_composition_plan,
            org_repo=org_repo,
            source_text=inner_text,
            facts=facts,
            assessment=assessment,
        )
        if agentic_composition_plan
        else None
    )
    validated_section_authoring = (
        SectionAuthoringDocumentV1.model_validate(section_authoring_document)
        if section_authoring_document is not None
        else None
    )
    if validated_section_authoring is not None:
        if not validated_section_authoring.complete:
            raise ValueError("incomplete section authoring cannot enter candidate rendering")
        if validated_section_authoring.org_repo != org_repo:
            raise ValueError("section authoring document belongs to a different repository")
        if validated_section_authoring.source_revision != base_revision:
            raise ValueError("section authoring document source revision changed")
        if validated_section_authoring.facts_hash != facts.canonical_hash():
            raise ValueError("section authoring document facts changed")
        if (
            validated_section_authoring.source_sha256
            != hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        ):
            raise ValueError("section authoring document source README changed")
        if (
            validated_section_authoring.protected_literal_hash
            != fingerprint_protected_content(source_text).maintainer_region_hash
        ):
            raise ValueError("section authoring document protected-content fingerprint changed")
    if facts.content_assurance == "repository_verified" and validated_agentic_plan is not None:
        return build_verified_template_document_candidate(
            facts,
            source_text,
            base_revision,
            validated_agentic_plan,
            link_catalogs=link_catalogs,
            link_allocation_policy=link_allocation_policy,
            llm_disposition_client=llm_disposition_client,
            repository_root=repository_root,
            disposition_ratchet_path=disposition_ratchet_path,
            section_authoring_document=validated_section_authoring,
        )
    header_visuals = render_readme_header_visual(facts, validated_agentic_plan)
    withheld = build_unresolved_section_operations(context, assessment)
    withheld_spans = [
        (operation.source_byte_start, operation.source_byte_end) for operation in withheld
    ]
    opening_exclusion_spans = [
        *withheld_spans,
        *commercial_directory_spans(context),
    ]
    operations = build_core_opening_operations(
        context,
        validated_agentic_plan,
        header_visuals,
        exclusion_spans=opening_exclusion_spans,
    )
    operations.extend(build_existing_overview_diagram_operations(context, header_visuals))
    operations.extend(build_limitation_operations(context))
    operations.extend(build_acquisition_correction_operations(context))
    operations.extend(build_example_operations(context))
    operations.extend(build_additional_examples_collapse_operations(context, operations))
    for promotional_operation in build_promotional_callout_operations(context):
        if not any(
            operation.source_byte_start < promotional_operation.source_byte_end
            and promotional_operation.source_byte_start < operation.source_byte_end
            for operation in operations
        ):
            operations.append(promotional_operation)
    operations.extend(build_registry_badge_operations(context))
    operations.extend(build_release_operations(context))
    operations.extend(build_license_operations(context))
    operations.extend(build_third_party_notice_operations(context))
    # Equal-offset insertions appear in reverse plan order in the candidate.
    # Append the header operation last so badges remain immediately below H1.
    operations.extend(build_badge_header_operations(context, header_visuals))
    operations = remove_operations_overlapping_withheld_sections(operations, withheld)
    operations.extend(withheld)
    operations.extend(build_density_collapse_operations(context, operations))
    for comment_operation in build_comment_removal_operations(context):
        if not any(
            operation.source_byte_start < comment_operation.source_byte_end
            and comment_operation.source_byte_start < operation.source_byte_end
            for operation in operations
        ):
            operations.append(comment_operation)
    journey_operations = build_core_section_journey_operations(
        context,
        operations,
        header_visuals,
    )
    operations = [*journey_operations, *operations]
    operations.extend(build_presentation_policy_operations(context, operations))
    operations.extend(build_review_repair_operations(context, validated_agentic_plan, operations))
    product_name = enterprise_product_name(facts)
    if link_catalogs is not None and link_allocation_policy is not None:
        operations.extend(
            build_source_link_hygiene_operations(
                context,
                operations,
                link_catalogs,
                link_allocation_policy,
            )
        )
    terminology_corrections: list[EnterpriseTerminologyCorrectionV1] = []
    if product_name is not None:
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
    operations = canonicalize_operation_decorations(
        operations,
        canonical_terms=canonical_abbreviations_from_facts(facts),
    )
    operations = finalize_navigation_operations(source, operations)
    operations = enforce_canonical_section_order(source, operations)
    operations = prune_noop_operations(source, operations)
    validate_agentic_operation_coverage(
        assessment,
        assessment.sections,
        operations,
    )
    rendered_inner = apply_document_operations(source, operations).decode("utf-8")
    if rendered_inner == context.inner_text:
        operations = []
    terminology_findings = (
        find_enterprise_terminology_findings(
            rendered_inner,
            enterprise_product_name=product_name,
        )
        if product_name is not None
        else []
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
    return finalize_legacy_document_candidate(
        context,
        rendered_inner,
        operations,
        header_visuals,
        contextual_links,
        terminology_corrections,
    )
