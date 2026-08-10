"""Compare public limitation statements without collapsing distinct constraints."""

from __future__ import annotations

import re

from readme_agent.readme.capability_semantics import capability_domains
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
    if bool(_LIMITING_LANGUAGE.search(normalized_left)) != bool(
        _LIMITING_LANGUAGE.search(normalized_right)
    ):
        return False
    if not left_domains:
        left_subject = semantic_content_words(normalized_left) - _GENERIC_LIMITATION_WORDS
        right_subject = semantic_content_words(normalized_right) - _GENERIC_LIMITATION_WORDS
        if not left_subject.intersection(right_subject):
            return False
    threshold = 0.5 if left_domains else 0.65
    return semantically_repeats(normalized_left, normalized_right, threshold=threshold)


__all__ = ["public_limitations_equivalent"]
