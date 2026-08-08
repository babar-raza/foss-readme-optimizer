"""Expose the accepted presentation template to an assurance-neutral reviewer."""

from __future__ import annotations

from readme_agent.presentation.template_schema import (
    RepositoryPresentationTemplateV1,
    load_repository_presentation_template,
)
from readme_agent.readme.public_text import title_case_heading


def build_presentation_visitor_contract(
    template: RepositoryPresentationTemplateV1 | None = None,
    *,
    applicable_h2_headings: list[str] | None = None,
    primary_example_language: str | None = None,
) -> dict:
    """Return visible standards only, without producer reasoning or factual conclusions."""

    contract = template or load_repository_presentation_template()
    if applicable_h2_headings is None:
        required_prefix = [
            contract.headings[slot]
            for slot in contract.section_order
            if slot
            in {"navigation", "at_a_glance", "key_capabilities", "installation", "quick_start"}
        ]
        required_navigation = [
            contract.headings[slot] for slot in contract.required_slots if slot != "navigation"
        ]
        applicability_basis = "unresolved_template"
    else:
        applicable = list(
            dict.fromkeys(title_case_heading(heading.strip()) for heading in applicable_h2_headings)
        )
        applicable_set = {heading.casefold() for heading in applicable if heading}
        required_prefix = [
            contract.headings[slot]
            for slot in contract.section_order
            if slot
            in {"navigation", "at_a_glance", "key_capabilities", "installation", "quick_start"}
            and contract.headings[slot].casefold() in applicable_set
        ]
        navigation_heading = contract.headings["navigation"].casefold()
        required_navigation = [
            heading
            for heading in applicable
            if heading and heading.casefold() != navigation_heading
        ]
        applicability_basis = "validated_candidate_h2_headings"
    language = (primary_example_language or "default").strip().casefold()
    maximum_example_lines = contract.invariants.primary_example_max_nonblank_lines.get(
        language,
        contract.invariants.primary_example_max_nonblank_lines["default"],
    )
    return {
        "template_id": contract.template_id,
        "template_version": contract.template_version,
        "accepted_reference_sha256": contract.accepted_reference_sha256,
        "applicability_basis": applicability_basis,
        "configured_standards": [
            {
                "standard_id": "readme.header",
                "parameters": {
                    "brand_contract_version": (
                        f"{contract.template_id}-v{contract.template_version}"
                    ),
                    "required_h2_prefix": required_prefix,
                    "heading_style": contract.invariants.heading_case,
                    "emoji_policy": contract.invariants.emoji,
                },
            },
            {
                "standard_id": "readme.badges",
                "parameters": {
                    "badge_rows": contract.invariants.badge_rows,
                    "minimum_badges": contract.invariants.minimum_badges,
                    "block_spacing": "commonmark_blank_line",
                    "allow_inherited_badges_after_core": False,
                    "allowed_badge_kinds": [
                        "package",
                        "platform",
                        "license",
                        "contributors",
                    ],
                },
            },
            {
                "standard_id": "readme.navigation",
                "parameters": {
                    "required_labels": required_navigation,
                    "complete_h2_list": True,
                    "list_style": "markdown_bullets",
                },
            },
            {
                "standard_id": "readme.at_a_glance_mermaid",
                "parameters": {
                    "heading": contract.headings["at_a_glance"],
                    "visual_grammar": contract.invariants.mermaid_visual_grammar,
                    "capability_layout": contract.invariants.mermaid_capability_layout,
                    "capability_column_threshold": (
                        contract.invariants.mermaid_capability_column_threshold
                    ),
                    "capability_layout_constraint": (
                        contract.invariants.mermaid_capability_layout_constraint
                    ),
                    "topology": contract.invariants.mermaid_topology,
                    "minimum_inputs": contract.invariants.minimum_mermaid_inputs,
                    "minimum_capabilities": contract.invariants.minimum_mermaid_capabilities,
                    "minimum_outputs": contract.invariants.minimum_mermaid_outputs,
                    "target_inputs": contract.invariants.target_mermaid_inputs,
                    "target_capabilities": contract.invariants.target_mermaid_capabilities,
                    "target_outputs": contract.invariants.target_mermaid_outputs,
                    "capability_coverage": "all_selected_verified",
                    "maximum_capabilities_per_group": (
                        contract.invariants.target_mermaid_capabilities
                    ),
                    "directional_workflow": False,
                    "product_to_capabilities_edges": 1,
                    "capabilities_to_outputs_edges": 1,
                },
            },
            {
                "standard_id": "readme.primary_example",
                "parameters": {
                    "heading": contract.headings["quick_start"],
                    "maximum_fenced_blocks": 1,
                    "maximum_nonblank_code_lines": maximum_example_lines,
                    "secondary_examples": "collapsed_below_primary",
                    "secondary_examples_intro": contract.invariants.additional_examples_intro,
                    "public_internal_assurance": contract.invariants.public_internal_assurance,
                    "duplicate_generic_headings": "forbidden",
                },
            },
            {
                "standard_id": "readme.no_comments",
                "parameters": {
                    "html_comments": contract.invariants.comments,
                    "code_comments": contract.invariants.comments,
                },
            },
            {
                "standard_id": "readme.public_language",
                "parameters": {
                    "heading_case": contract.invariants.heading_case,
                    "technical_abbreviation_case": (
                        contract.invariants.technical_abbreviation_case
                    ),
                    "internal_assurance": contract.invariants.public_internal_assurance,
                    "semantic_section_repetition": (
                        contract.invariants.semantic_section_repetition
                    ),
                    "source_detail_routing": contract.invariants.source_detail_routing,
                },
            },
            {
                "standard_id": "readme.license",
                "parameters": {
                    "benefits_summary": "required",
                    "required_benefit_terms": [
                        "use",
                        "modification",
                        "distribution",
                        "commercial use",
                    ],
                },
            },
            {
                "standard_id": "readme.enterprise_edition_terminology",
                "parameters": {
                    "required_term": contract.invariants.commercial_term,
                    "required_section": contract.headings["scope_and_limitations"],
                    "placement": "below_the_fold_scope_context",
                    "anchor_style": contract.invariants.enterprise_link_anchor,
                },
            },
        ],
    }
