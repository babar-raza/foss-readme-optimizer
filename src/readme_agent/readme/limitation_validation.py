"""Validate item-complete representation of selected verified limitations."""

from __future__ import annotations

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2

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
    view = visitor_fact_render_view(facts, "product.limitations")
    if view is None or not view.phrases:
        return False
    return all(phrase in candidate_text for phrase in view.phrases)
