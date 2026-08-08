"""Validate one agent-authored opening summary against accepted product facts."""

from __future__ import annotations

import re

from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import AgenticCompositionDraftV1
from readme_agent.readme.fact_grounding import literal_fact_ids


def validate_opening_summary(
    draft: AgenticCompositionDraftV1,
    facts: ProductFactsV2,
) -> None:
    """Fail closed when the optional opening summary exceeds its fact bindings."""

    summary = draft.opening_summary
    if summary is None:
        return
    if re.search(r"[.!?][ \t]*[,;:]", summary.text):
        raise LLMError("composition opening summary contains invalid sentence punctuation")
    identity_id = facts.selected_fact_ids.get("product.identity")
    if identity_id not in summary.supporting_fact_ids:
        raise LLMError("composition opening summary does not cite the selected identity")
    audience_id = facts.selected_fact_ids.get("product.audience")
    if audience_id and audience_id not in summary.supporting_fact_ids:
        raise LLMError("composition opening summary does not cite the selected audience")
    if audience_id and audience_id not in literal_fact_ids(summary.text, facts, [audience_id]):
        raise LLMError(
            "composition opening summary does not literally ground the selected audience"
        )
    purpose_ids = {
        facts.selected_fact_ids.get(field)
        for field in ("product.problems_solved", "product.capabilities", "product.formats")
    }
    if not purpose_ids.intersection(summary.supporting_fact_ids):
        raise LLMError("composition opening summary has no accepted purpose citation")
    identity = visitor_fact_render_view(facts, "product.identity")
    title = identity.phrases[0] if identity and identity.phrases else ""
    if title not in summary.text:
        raise LLMError("composition opening summary omits the complete product identity")
    if re.search(
        r"(?i)(?:https?://|official\b|100%\s+free|revision\s+`?[0-9a-f]{7,}"
        r"|\bcommercial\b|\benterprise\s+edition\b|\bon[- ]premise\b)",
        summary.text,
    ):
        raise LLMError(
            "composition opening summary contains promotional, edition-comparison, or internal text"
        )
    capabilities = visitor_fact_render_view(facts, "product.capabilities")
    raw_capability_phrases = (
        [
            phrase
            for phrase in capabilities.phrases
            if len(phrase.strip()) >= 4
            and re.match(
                r"(?i)^(?:add|convert|create|edit|export|extract|generate|import|inspect|"
                r"load|read|render|save|traverse|validate|write)\b",
                phrase,
            )
            is None
            and phrase.casefold() in summary.text.casefold()
        ]
        if capabilities is not None
        else []
    )
    if len(raw_capability_phrases) >= 2 and re.search(
        r"(?i)\b(?:provides?|includes?|features?)\b",
        summary.text,
    ):
        raise LLMError(
            "composition opening summary inserts a raw capability inventory into generic prose"
        )


__all__ = ["validate_opening_summary"]
