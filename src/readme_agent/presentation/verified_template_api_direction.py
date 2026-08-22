"""Prevent public API symbol names from becoming unsupported format behavior claims."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_api_text import public_noun
from readme_agent.readme.format_role_truth import (
    explicit_format_roles,
    unsupported_format_directions,
)

_INPUT_SEMANTICS = re.compile(r"(?i)\b(?:importer|input|load options?|loads?|reads?)\b")
_OUTPUT_SEMANTICS = re.compile(r"(?i)\b(?:exporter|output|save options?|saves?|writes?)\b")


def reconcile_api_format_description(
    *,
    name: str,
    module: str,
    description: str,
    facts: ProductFactsV2,
) -> str:
    """Keep exact API presence while removing unproved functional direction inference."""

    semantic_text = f"{public_noun(name)} {description}"
    unsupported: set[str] = set()
    if _INPUT_SEMANTICS.search(semantic_text):
        unsupported.update(unsupported_format_directions(semantic_text, facts, "input"))
    if _OUTPUT_SEMANTICS.search(semantic_text):
        unsupported.update(unsupported_format_directions(semantic_text, facts, "output"))
    if not unsupported:
        return description

    rendered = f"The package exposes the public `{name}` type in the `{module}` namespace."
    roles = explicit_format_roles(facts)
    role_notes = []
    for format_name in sorted(unsupported):
        allowed = roles.get(format_name, frozenset())
        if allowed == {"input"}:
            role_notes.append(f"{format_name} is listed for input workflows only.")
        elif allowed == {"output"}:
            role_notes.append(f"{format_name} is listed for output workflows only.")
    return " ".join([rendered, *role_notes])


__all__ = ["reconcile_api_format_description"]
