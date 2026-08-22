"""Bind bounded source format-direction captions to accepted format facts."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.format_role_truth import (
    directional_format_claims,
    unsupported_format_directions_for_formats,
)

_DIRECTION_CAPTION = re.compile(
    r"(?is)^\s*(?:convert|export|import|load|open|read|save|write)\b[^\n]{1,220}[.:]?\s*$"
)


def format_direction_caption_fact_ids(text: str, facts: ProductFactsV2) -> set[str]:
    """Bind one short directional caption only when every named role is authorized."""

    if _DIRECTION_CAPTION.fullmatch(text.strip()) is None:
        return set()
    claims = directional_format_claims(text)
    if not claims:
        return set()
    for role, formats in claims.items():
        if unsupported_format_directions_for_formats(set(formats), facts, role):
            return set()
    fact_id = facts.selected_fact_ids.get("product.formats")
    if fact_id is None:
        return set()
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return set()
    return set() if fact.has_unresolved_conflict else {fact_id}


__all__ = ["format_direction_caption_fact_ids"]
