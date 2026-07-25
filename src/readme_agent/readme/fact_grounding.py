"""Locate exact fact phrases in generated or corrected README text."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2


@dataclass(frozen=True)
class LiteralFactMatch:
    phrase: str
    character_start: int
    character_end: int
    line_start: int
    line_end: int


def fact_strings(value: object) -> list[str]:
    """Flatten nonempty fact strings without inventing display text."""

    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [text for item in value for text in fact_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in fact_strings(item)]
    return []


def find_literal_fact_match(text: str, value: object) -> LiteralFactMatch | None:
    """Find the earliest literal fact phrase and its containing line."""

    folded = text.casefold()
    matches = [
        (folded.find(phrase.casefold()), phrase)
        for phrase in fact_strings(value)
        if len(phrase) >= 4 and phrase.casefold() in folded
    ]
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

    return sorted(
        {
            fact_id
            for fact_id in fact_ids
            if find_literal_fact_match(text, facts.fact_by_id(fact_id).value) is not None
        }
    )
