"""Compare public limitation statements without collapsing distinct constraints."""

from __future__ import annotations

import re

from readme_agent.readme.capability_semantics import capability_domains, identifier_discriminators
from readme_agent.readme.presentation_similarity import (
    capability_discriminators,
    semantic_content_words,
    semantically_repeats,
)

_MARKUP = re.compile(r"[`*_~]+")
_LIMITING_LANGUAGE = re.compile(
    r"(?i)\b(?:best effort|heuristic|incomplete|limited|limitation|not|no|only|outside|"
    r"unsupported|unavailable|without)\b"
)
_GENERIC_LIMITATION_WORDS = {
    "are",
    "best",
    "effort",
    "implement",
    "implemented",
    "incomplete",
    "is",
    "limited",
    "limitation",
    "not",
    "only",
    "support",
    "supported",
    "unsupported",
}
_CONSTRAINT_PREDICATE = re.compile(
    r"(?i)\b(?:allows?|are|does|do|fails?|is|must|permits?|rejects?|requires?|returns?|"
    r"supports?)\b"
)
_FAILS_EXPLICITLY = re.compile(r"(?i)\bfail\w*\s+explicitly\b")
_INCOMPLETE_COVERAGE = re.compile(
    r"(?i)(?:\bcoverage\b.*\bnot\s+(?:yet\s+)?complete\b|"
    r"\bnot\s+(?:yet\s+)?complete\b.*\bcoverage\b)"
)


def _constraint_subject(value: str) -> frozenset[str]:
    """Return the normalized entity constrained by one public limitation."""

    prefix = _CONSTRAINT_PREDICATE.split(value, maxsplit=1)[0]
    words = semantic_content_words(prefix) - _GENERIC_LIMITATION_WORDS
    return frozenset(word[:-1] if len(word) > 4 and word.endswith("s") else word for word in words)


# Quantifier/determiner scaffolding a "requires at least N ..." style sentence
# shares regardless of what is actually being counted -- stripping it (and bare
# numerals) from the constraint object isolates the noun that actually
# discriminates two same-subject constraints (e.g. "steps" vs "frames").
_QUANTIFIER_WORDS = {
    "a",
    "an",
    "the",
    "one",
    "two",
    "three",
    "four",
    "five",
    "exactly",
    "at",
    "least",
    "most",
    "no",
    "any",
    "all",
}


def _constraint_object(value: str) -> frozenset[str]:
    """Return the normalized entity required by one public limitation's constraint."""

    parts = _CONSTRAINT_PREDICATE.split(value, maxsplit=1)
    suffix = parts[1] if len(parts) > 1 else ""
    words = semantic_content_words(suffix) - _GENERIC_LIMITATION_WORDS - _QUANTIFIER_WORDS
    words = {word for word in words if not word.isdigit()}
    return frozenset(word[:-1] if len(word) > 4 and word.endswith("s") else word for word in words)


def public_limitations_equivalent(left: str, right: str) -> bool:
    """Return whether two statements express one constraint at the same assurance."""

    normalized_left = " ".join(_MARKUP.sub(" ", left).split())
    normalized_right = " ".join(_MARKUP.sub(" ", right).split())
    if not normalized_left or not normalized_right:
        return False
    if normalized_left.casefold().rstrip(". !?") == normalized_right.casefold().rstrip(". !?"):
        return True
    left_domains = capability_domains(normalized_left)
    right_domains = capability_domains(normalized_right)
    if left_domains != right_domains:
        return False
    left_discriminators = capability_discriminators(normalized_left)
    right_discriminators = capability_discriminators(normalized_right)
    if left_discriminators and right_discriminators and left_discriminators != right_discriminators:
        return False
    # Format-name discriminators above catch "PDF vs XPS"; a barcode symbology
    # number, a version, or any other acronym/digit-bearing identifier is not in
    # that fixed vocabulary but is exactly as distinguishing (e.g. "Code 128" vs
    # "Code 39" -- see the shared identifier_discriminators() docstring).
    left_identifiers = identifier_discriminators(normalized_left)
    right_identifiers = identifier_discriminators(normalized_right)
    if left_identifiers and right_identifiers and left_identifiers != right_identifiers:
        return False
    if bool(_LIMITING_LANGUAGE.search(normalized_left)) != bool(
        _LIMITING_LANGUAGE.search(normalized_right)
    ):
        return False
    if all(
        _FAILS_EXPLICITLY.search(value) and _INCOMPLETE_COVERAGE.search(value)
        for value in (normalized_left, normalized_right)
    ):
        return True
    if not left_domains:
        left_subject = _constraint_subject(normalized_left)
        right_subject = _constraint_subject(normalized_right)
        if left_subject and right_subject and left_subject != right_subject:
            return False
        if not left_subject.intersection(right_subject):
            return False
        # A shared subject alone is not enough: "Animation path requires at
        # least two steps" and "Animation path requires at least 2 frames per
        # segment" share their subject but constrain different things (path
        # waypoint count vs. interpolation density). Require the object --
        # what is actually required -- to overlap too, once quantifier
        # scaffolding shared by any "requires at least N ..." phrasing is
        # stripped away.
        left_object = _constraint_object(normalized_left)
        right_object = _constraint_object(normalized_right)
        if left_object and right_object and not left_object.intersection(right_object):
            return False
    threshold = 0.5 if left_domains else 0.65
    return semantically_repeats(normalized_left, normalized_right, threshold=threshold)


__all__ = ["public_limitations_equivalent"]
