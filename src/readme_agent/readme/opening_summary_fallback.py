"""Build a conservative fact-literal opening when agentic prose cannot pass its gate."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import AgenticOverviewSentenceV1

_DIRECTIONAL_FORMAT = re.compile(r"(?i)^(input|output)\s+format\s*:\s*(.+)$")
_ACTION_FORMAT = re.compile(r"(?i)^(reads?|loads?|imports?|writes?|saves?|exports?)\s+(.+)$")
_ACTIONABLE_PURPOSE = re.compile(
    r"(?i)(?:^(?:add|build|convert|create|edit|export|extract|generate|import|inspect|"
    r"load|manage|process|read|render|save|traverse|validate|write)\b|"
    r"\b(?:conversion|creation|editing|export|extraction|generation|inspection|"
    r"management|processing|rendering|validation)\b)"
)


def _joined(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return ", ".join(values[:-1]) + f", and {values[-1]}"


def verified_format_opening_summary(
    facts: ProductFactsV2,
) -> AgenticOverviewSentenceV1 | None:
    """Return natural prose grounded in exact identity, audience, and directed formats."""

    identity = visitor_fact_render_view(facts, "product.identity")
    audience = visitor_fact_render_view(facts, "product.audience")
    formats = visitor_fact_render_view(facts, "product.formats")
    if identity is None or audience is None or formats is None:
        return None
    title = identity.phrases[0].strip().rstrip(".") if identity.phrases else ""
    audience_text = audience.phrases[0].strip().rstrip(".") if audience.phrases else ""
    inputs: list[str] = []
    outputs: list[str] = []
    for phrase in formats.phrases:
        normalized = " ".join(phrase.split()).rstrip(".")
        match = _DIRECTIONAL_FORMAT.fullmatch(normalized)
        action = _ACTION_FORMAT.fullmatch(normalized)
        if match is None and action is None:
            continue
        if match is not None:
            direction = match.group(1).casefold()
            value = match.group(2).strip()
        else:
            assert action is not None
            direction = action.group(1).casefold()
            value = action.group(2).strip()
        values = inputs if direction.startswith(("input", "read", "load", "import")) else outputs
        if value and value.casefold() not in {item.casefold() for item in values}:
            values.append(value)
    if not title or not audience_text or not (inputs or outputs):
        return None
    audience_clause = audience_text[:1].lower() + audience_text[1:]
    if inputs and outputs:
        purpose = f"It reads {_joined(inputs)} and writes {_joined(outputs)}."
    elif inputs:
        purpose = f"It reads {_joined(inputs)}."
    else:
        purpose = f"It writes {_joined(outputs)}."
    return AgenticOverviewSentenceV1(
        text=f"{title} is an open-source library for {audience_clause}. {purpose}",
        supporting_fact_ids=[identity.fact_id, audience.fact_id, formats.fact_id],
    )


def verified_identity_opening_summary(
    facts: ProductFactsV2,
) -> AgenticOverviewSentenceV1 | None:
    """Return the identity-and-audience-only opening for working-condition repositories.

    When no purpose evidence (problems, capabilities, formats) is accepted, an
    identity-grounded sentence is the honest maximum the summary can claim.
    """

    identity = visitor_fact_render_view(facts, "product.identity")
    if identity is None or not identity.phrases:
        return None
    title = identity.phrases[0].strip().rstrip(".")
    if not title:
        return None
    audience = visitor_fact_render_view(facts, "product.audience")
    fact_ids = [identity.fact_id]
    if audience is not None and audience.phrases:
        audience_text = audience.phrases[0].strip().rstrip(".")
        audience_clause = audience_text[:1].lower() + audience_text[1:]
        text = f"{title} is an open-source library for {audience_clause}."
        fact_ids.append(audience.fact_id)
    else:
        text = f"{title} is an open-source library."
    return AgenticOverviewSentenceV1(text=text, supporting_fact_ids=fact_ids)


def should_use_verified_format_opening(facts: ProductFactsV2) -> bool:
    """Return whether the first purpose is a taxonomy label rather than a useful action."""

    purpose = visitor_fact_render_view(facts, "product.problems_solved")
    if purpose is None or not purpose.phrases:
        return True
    fact = facts.fact_by_id(purpose.fact_id)
    return (
        fact.source.source_type == "mechanical_repository"
        and _ACTIONABLE_PURPOSE.search(purpose.phrases[0]) is None
    )


__all__ = [
    "should_use_verified_format_opening",
    "verified_format_opening_summary",
    "verified_identity_opening_summary",
]
