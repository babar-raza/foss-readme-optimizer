"""Materialize composition overview text from accepted visitor-facing facts."""

from __future__ import annotations

import re

from readme_agent.errors import LLMError
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.agentic_composition_models import (
    OVERVIEW_FIELD_PREFERENCE,
    AgenticCompositionDraftV1,
    AgenticCompositionToolDraftV1,
    AgenticOverviewSentenceV1,
)

_ACCEPTED_STATES = {"verified", "policy_approved"}


def accepted_composition_fact_ids(facts: ProductFactsV2) -> set[str]:
    """Return selected, conflict-free fact IDs eligible for composition."""

    return {
        fact.fact_id
        for fact in facts.facts
        if facts.selected_fact_ids.get(fact.field) == fact.fact_id
        and fact.verification_state in _ACCEPTED_STATES
        and not fact.has_unresolved_conflict
    }


def overview_phrase_options(facts: ProductFactsV2) -> list[dict]:
    """Return literal visitor-facing phrases keyed by accepted fact ID."""

    accepted_ids = accepted_composition_fact_ids(facts)
    options = []
    for field in OVERVIEW_FIELD_PREFERENCE:
        view = visitor_fact_render_view(facts, field)
        if view is None or view.fact_id not in accepted_ids:
            continue
        phrases = [phrase.strip() for phrase in view.phrases if len(phrase.strip()) >= 4]
        if phrases:
            options.append({"fact_id": view.fact_id, "phrases": phrases[:8]})
    return options


def required_overview_fact_ids(facts: ProductFactsV2) -> set[str]:
    """Return the minimum accepted fact IDs that an overview must cover."""

    options = overview_phrase_options(facts)
    option_ids = {option["fact_id"] for option in options}
    audience_problem = {
        facts.selected_fact_ids[field]
        for field in ("product.audience", "product.problems_solved")
        if facts.selected_fact_ids.get(field) in option_ids
    }
    return audience_problem or {option["fact_id"] for option in options[:2]}


def normalized_overview_words(text: str) -> str:
    """Normalize punctuation so one grounded phrase can subsume another."""

    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def phrases_overlap(left: str, right: str) -> bool:
    """Return whether normalized literal phrases subsume one another."""

    left_words = normalized_overview_words(left)
    right_words = normalized_overview_words(right)
    return bool(
        left_words and right_words and (left_words in right_words or right_words in left_words)
    )


def materialize_tool_draft(
    tool_draft: AgenticCompositionToolDraftV1,
    phrase_options: list[dict],
    facts: ProductFactsV2,
) -> AgenticCompositionDraftV1:
    """Turn model-selected fact IDs into literal fact text deterministically."""

    phrases_by_fact_id = {option["fact_id"]: option["phrases"] for option in phrase_options}
    selected_ids = tool_draft.overview_fact_ids
    unknown_ids = set(selected_ids) - set(phrases_by_fact_id)
    if unknown_ids:
        raise LLMError(f"composition selected ineligible overview fact IDs: {sorted(unknown_ids)}")
    if len(selected_ids) != len(set(selected_ids)):
        raise LLMError("composition selected duplicate overview fact IDs")
    materialized_ids = list(
        dict.fromkeys([*selected_ids, *sorted(required_overview_fact_ids(facts))])
    )
    used_phrases: set[str] = set()
    overview_sentences: list[AgenticOverviewSentenceV1] = []
    for fact_id in materialized_ids:
        phrases = phrases_by_fact_id[fact_id]
        text = next(
            (
                phrase
                for phrase in phrases
                if phrase.strip().rstrip(".").casefold() not in used_phrases
            ),
            phrases[0],
        )
        used_phrases.add(text.strip().rstrip(".").casefold())
        overlapping_index = next(
            (
                index
                for index, sentence in enumerate(overview_sentences)
                if phrases_overlap(sentence.text, text)
            ),
            None,
        )
        if overlapping_index is not None:
            existing = overview_sentences[overlapping_index]
            rendered_text = (
                text
                if len(normalized_overview_words(text))
                > len(normalized_overview_words(existing.text))
                else existing.text
            )
            overview_sentences[overlapping_index] = AgenticOverviewSentenceV1(
                text=rendered_text,
                supporting_fact_ids=list(dict.fromkeys([*existing.supporting_fact_ids, fact_id])),
            )
            continue
        overview_sentences.append(
            AgenticOverviewSentenceV1(text=text, supporting_fact_ids=[fact_id])
        )
    return AgenticCompositionDraftV1(
        repository_summary=tool_draft.repository_summary,
        section_decisions=tool_draft.section_decisions,
        overview_sentences=overview_sentences,
    )
