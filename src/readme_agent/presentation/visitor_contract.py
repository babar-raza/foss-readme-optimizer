"""Expose the accepted presentation template to an assurance-neutral reviewer."""

from __future__ import annotations

from readme_agent.presentation.template_schema import (
    RepositoryPresentationTemplateV1,
    load_repository_presentation_template,
)


def build_presentation_visitor_contract(
    template: RepositoryPresentationTemplateV1 | None = None,
) -> dict:
    """Return visible standards only, without producer reasoning or factual conclusions."""

    contract = template or load_repository_presentation_template()
    required_prefix = [
        contract.headings[slot]
        for slot in contract.section_order
        if slot in {"navigation", "at_a_glance", "key_capabilities", "installation", "quick_start"}
    ]
    required_navigation = [
        contract.headings[slot] for slot in contract.required_slots if slot != "navigation"
    ]
    return {
        "template_id": contract.template_id,
        "template_version": contract.template_version,
        "accepted_reference_sha256": contract.accepted_reference_sha256,
        "configured_standards": [
            {
                "standard_id": "readme.header",
                "parameters": {
                    "brand_contract_version": (
                        f"{contract.template_id}-v{contract.template_version}"
                    ),
                    "required_h2_prefix": required_prefix,
                    "heading_style": "sentence_case_without_emoji",
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
                    "visual_grammar": "inputs-product-capabilities-outputs",
                    "minimum_inputs": contract.invariants.minimum_mermaid_inputs,
                    "minimum_capabilities": contract.invariants.minimum_mermaid_capabilities,
                    "minimum_outputs": contract.invariants.minimum_mermaid_outputs,
                    "directional_workflow": False,
                },
            },
            {
                "standard_id": "readme.primary_example",
                "parameters": {
                    "heading": contract.headings["quick_start"],
                    "maximum_fenced_blocks": 1,
                    "maximum_nonblank_code_lines": 12,
                    "secondary_examples": "collapsed_below_primary",
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
                "standard_id": "readme.enterprise_edition_terminology",
                "parameters": {
                    "required_term": contract.invariants.commercial_term,
                    "required_section": contract.headings["scope_and_limitations"],
                    "placement": "below_the_fold_scope_context",
                },
            },
        ],
    }
