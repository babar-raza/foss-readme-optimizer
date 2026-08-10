"""Define assurance-neutral visible presentation rules for every README lane."""

from __future__ import annotations

from readme_agent.presentation.template_schema import load_repository_presentation_template

_TEMPLATE = load_repository_presentation_template()

PRESENTATION_CONTRACT_VERSION = "repository-presentation-brand-v1"
PRESENTATION_H2_PREFIX = tuple(
    _TEMPLATE.headings[slot]
    for slot in _TEMPLATE.section_order
    if slot in {"navigation", "at_a_glance", "key_capabilities", "installation", "quick_start"}
)
PRESENTATION_HEADING_SUFFIX_ALIASES = {"examples": "Examples"}
PRESENTATION_HEADING_PREFIX_ALIASES = {"Why ": "Key capabilities"}
PRESENTATION_EMOJI_POLICY = "none"
PRESENTATION_MERMAID_GRAMMAR = _TEMPLATE.invariants.mermaid_visual_grammar
PRESENTATION_MERMAID_MAX_NODES = 16
PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS = 36
PRESENTATION_MERMAID_MAX_BLOCK_LINES = 64
PRESENTATION_MERMAID_MAX_COLUMN_NODES = 4
PRESENTATION_MERMAID_MIN_INPUTS = _TEMPLATE.invariants.minimum_mermaid_inputs
PRESENTATION_MERMAID_MIN_CAPABILITIES = _TEMPLATE.invariants.minimum_mermaid_capabilities
PRESENTATION_MERMAID_MIN_OUTPUTS = _TEMPLATE.invariants.minimum_mermaid_outputs
PRESENTATION_MERMAID_TARGET_INPUTS = _TEMPLATE.invariants.target_mermaid_inputs
PRESENTATION_MERMAID_TARGET_CAPABILITIES = _TEMPLATE.invariants.target_mermaid_capabilities
PRESENTATION_MERMAID_TARGET_OUTPUTS = _TEMPLATE.invariants.target_mermaid_outputs
PRESENTATION_ENTERPRISE_LINK_SECTION = "Scope and limitations"
PRESENTATION_SECTION_VISIBLE_LINE_LIMITS = {
    "additional_examples": 3,
    "api_reference": 4,
}
PRESENTATION_SECTION_VISIBLE_LIMITS_BY_HEADING = {
    _TEMPLATE.headings[slot]: limit
    for slot, limit in PRESENTATION_SECTION_VISIBLE_LINE_LIMITS.items()
    if slot in _TEMPLATE.headings
}
