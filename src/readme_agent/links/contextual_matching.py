"""Rank contextual articles against accepted example and public-API evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass

from readme_agent.links.catalog_models import AsposeLinkRecordV2

_CODE_TERM = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_STOP_TERMS = {
    "as",
    "auto",
    "class",
    "const",
    "data",
    "false",
    "for",
    "foss",
    "from",
    "go",
    "import",
    "int",
    "let",
    "main",
    "new",
    "none",
    "null",
    "package",
    "page",
    "pdf",
    "print",
    "println",
    "public",
    "return",
    "static",
    "str",
    "string",
    "true",
    "use",
    "using",
    "var",
    "void",
}


@dataclass(frozen=True)
class ContextualArticleMatch:
    """One article plus reproducible relevance evidence and sort key."""

    record: AsposeLinkRecordV2
    matched_terms: list[str]
    matched_public_api_terms: list[str]
    rank: tuple


def _example_terms(code: str) -> tuple[set[str], set[str]]:
    all_terms: set[str] = set()
    fallback_strong: set[str] = set()
    for raw in _CODE_TERM.findall(code):
        folded = raw.casefold().rstrip(".")
        parts = [part for part in folded.split(".") if len(part) >= 3]
        all_terms.update(parts)
        all_terms.add(folded)
        if "." in raw or raw[:1].isupper() or "_" in raw:
            fallback_strong.add(folded)
            fallback_strong.update(parts)
    all_terms.difference_update(_STOP_TERMS)
    fallback_strong.difference_update(_STOP_TERMS)
    return all_terms, fallback_strong


def _public_api_terms(example_value: dict) -> set[str]:
    terms: set[str] = set()
    raw_symbols = example_value.get("verified_public_symbols")
    if not isinstance(raw_symbols, list):
        return terms
    for symbol in raw_symbols:
        identifiers = _IDENTIFIER.findall(str(symbol))
        for identifier in identifiers:
            folded = identifier.casefold()
            if len(folded) >= 3 and folded not in _STOP_TERMS and folded != "github":
                terms.add(folded)
    return terms


def rank_contextual_articles(
    records: list[AsposeLinkRecordV2],
    *,
    code: str,
    example_value: dict,
) -> list[ContextualArticleMatch]:
    """Require accepted public-symbol overlap when that stronger evidence exists."""

    all_terms, fallback_strong = _example_terms(code)
    public_terms = _public_api_terms(example_value)
    ranked: list[ContextualArticleMatch] = []
    for record in records:
        subjects = {term.casefold().rstrip(".") for term in record.subject_terms}
        matched = sorted(subjects & all_terms)
        matched_public = sorted(subjects & public_terms)
        strong = matched_public if public_terms else sorted(subjects & fallback_strong)
        if not strong:
            continue
        dotted = [term for term in matched if "." in term]
        surface_rank = {"docs": 0, "kb": 1, "reference": 2}
        ranked.append(
            ContextualArticleMatch(
                record=record,
                matched_terms=sorted(set([*strong, *matched])),
                matched_public_api_terms=matched_public,
                rank=(
                    -len(matched_public),
                    -len(dotted),
                    -len(strong),
                    -len(matched),
                    surface_rank[record.surface],
                    len(record.url),
                    record.record_id,
                ),
            )
        )
    return sorted(ranked, key=lambda item: item.rank)
