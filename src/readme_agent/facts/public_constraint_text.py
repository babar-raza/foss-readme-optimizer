"""Classify repository constraint text that is suitable for public presentation."""

from __future__ import annotations

import re

_DOCSTRING_SECTION = re.compile(r"\b(?:Returns|Raises|Parameters)\s*-{3,}", re.IGNORECASE)
_INTERNAL_STATE = re.compile(
    r"\brequires?\s+(?:[a-z][a-z0-9]*_)+[a-z0-9]+\s+state\b|"
    r"\brequires?\s+[a-z][a-z0-9]*\s+state\b",
    re.IGNORECASE,
)
_INCOMPLETE_SUBJECT = re.compile(
    r"^(?:is|are|was|were|has|have|can|cannot|does|do|returns?|raises?)\b",
    re.IGNORECASE,
)
_MOJIBAKE = re.compile(r"(?:\u00c2|\u00c3|\u00e2\u0080)")
_INTERNAL_NARRATION = re.compile(
    r"^(?:normalize|deterministic\s+unsupported\s+handling)\b|\(/\d+(?:/\d+)+\)",
    re.IGNORECASE,
)


def is_public_constraint_sentence(value: str) -> bool:
    """Accept complete visitor-facing constraints and reject implementation diagnostics."""

    sentence = " ".join(value.strip().split())
    if len(re.findall(r"[A-Za-z0-9]+", sentence)) < 4:
        return False
    if _INCOMPLETE_SUBJECT.search(sentence) or _DOCSTRING_SECTION.search(sentence):
        return False
    if (
        _INTERNAL_STATE.search(sentence)
        or _INTERNAL_NARRATION.search(sentence)
        or _MOJIBAKE.search(sentence)
    ):
        return False
    if sentence.count("(") != sentence.count(")") or sentence.count("`") % 2:
        return False
    if "no invented behaviour" in sentence.casefold():
        return False
    return True


__all__ = ["is_public_constraint_sentence"]
