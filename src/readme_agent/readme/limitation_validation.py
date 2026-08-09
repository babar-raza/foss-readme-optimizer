"""Validate item-complete representation of selected verified limitations."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.public_limitations import public_limitation_phrases

_ACCEPTED_STATES = {"verified", "policy_approved"}


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
    return all(phrase in candidate_text for phrase in phrases)
