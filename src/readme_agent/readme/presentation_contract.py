"""Define assurance-neutral visible presentation rules for every README lane."""

from __future__ import annotations

PRESENTATION_CONTRACT_VERSION = "repository-presentation-brand-v1"
PRESENTATION_H2_PREFIX = (
    "At a glance",
    "Navigation",
    "Key capabilities",
    "Installation",
    "Quick start",
)
PRESENTATION_HEADING_SUFFIX_ALIASES = {"examples": "Examples"}
PRESENTATION_HEADING_PREFIX_ALIASES = {"Why ": "Key capabilities"}
PRESENTATION_EMOJI_POLICY = "none"
PRESENTATION_MERMAID_GRAMMAR = "inputs-product-capabilities-outputs"
PRESENTATION_MERMAID_MAX_NODES = 12
PRESENTATION_MERMAID_MAX_LABEL_CHARACTERS = 52
PRESENTATION_ENTERPRISE_LINK_SECTION = "Project scope and limitations"
