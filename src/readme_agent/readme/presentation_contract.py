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
PRESENTATION_MERMAID_GRAMMAR = "inputs-product-capabilities-outputs"
PRESENTATION_MERMAID_MAX_NODES = 16
PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS = 52
PRESENTATION_ENTERPRISE_LINK_SECTION = "Scope and limitations"
