"""Validate item-complete representation of selected verified limitations."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.public_limitations import public_limitation_phrases

_ACCEPTED_STATES = {"verified", "policy_approved"}


def _normalized_public_text(value: str) -> str:
    """Normalize presentation-only punctuation without weakening phrase identity."""

    return " ".join(re.sub(r"[`*_~]", "", value).casefold().split()).rstrip(". !?")


def verified_limitations_are_represented(
    facts: ProductFactsV2,
    candidate_text: str,
) -> bool:
    """Require every item of a nonempty selected limitation fact in candidate prose."""

    limitations = facts.selected_fact("product.limitations")
    if (
        limitations.verification_state not in _ACCEPTED_STATES
        or limitations.has_unresolved_conflict
        or not limitations.value
    ):
        return True
    phrases = public_limitation_phrases(facts)
    if not phrases:
        return False
    normalized_candidate = _normalized_public_text(candidate_text)
    return all(_normalized_public_text(phrase) in normalized_candidate for phrase in phrases)
