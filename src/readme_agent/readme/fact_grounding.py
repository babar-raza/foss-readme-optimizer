"""Locate exact fact phrases in generated or corrected README text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.fact_grounding_acquisition import (
    exact_coordinate_match,
    verified_acquisition_matches,
)
from readme_agent.readme.fact_grounding_views import (
    fact_strings,
    structured_rows,
    typed_fact_strings,
)


@dataclass(frozen=True)
class LiteralFactMatch:
    phrase: str
    character_start: int
    character_end: int
    line_start: int
    line_end: int


def find_literal_fact_match(text: str, value: object) -> LiteralFactMatch | None:
    """Find the earliest literal fact phrase and its containing line."""

    folded = text.casefold()
    matches: list[tuple[int, str]] = []
    for phrase in fact_strings(value):
        folded_phrase = phrase.casefold()
        if len(phrase) >= 4:
            start = folded.find(folded_phrase)
            if start >= 0:
                matches.append((start, phrase))
            continue
        if len(phrase) < 2:
            continue
        match = re.search(
            rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
        if match is not None:
            matches.append((match.start(), phrase))
    if not matches:
        return None
    start, phrase = min(matches, key=lambda item: (item[0], -len(item[1])))
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start + len(phrase))
    if line_end < 0:
        line_end = len(text)
    return LiteralFactMatch(
        phrase=phrase,
        character_start=start,
        character_end=start + len(phrase),
        line_start=line_start,
        line_end=line_end,
    )


def literal_fact_ids(
    text: str,
    facts: ProductFactsV2,
    fact_ids: list[str],
) -> list[str]:
    """Keep only fact IDs whose selected value is literally present in text."""

    matched: set[str] = set()
    for fact_id in fact_ids:
        fact = facts.fact_by_id(fact_id)
        if fact.field == "installation.verified_acquisition":
            if verified_acquisition_matches(text, fact.value):
                matched.add(fact_id)
            continue
        if fact.field == "installation.coordinates":
            if exact_coordinate_match(text, fact.value):
                matched.add(fact_id)
            continue
        view = visitor_fact_render_view(facts, fact.field)
        value = (
            view.phrases
            if view is not None and view.fact_id == fact_id and view.phrases
            else [
                *typed_fact_strings(fact.field, fact.value),
                *structured_rows(fact.field, fact.value),
            ]
        )
        if fact.field == "product.audience":
            value = [phrase.rstrip().rstrip(".!?") for phrase in value if phrase.rstrip(".!?")]
        if find_literal_fact_match(text, value) is not None:
            matched.add(fact_id)
    return sorted(matched)
