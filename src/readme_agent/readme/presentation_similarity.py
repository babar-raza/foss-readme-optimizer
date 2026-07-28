"""Share deterministic visitor-summary similarity semantics."""

from __future__ import annotations

import re


def content_words(value: str) -> set[str]:
    """Return stable visitor-significant words for overlap checks."""

    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2}


def summaries_overlap(left: str, right: str, *, threshold: float = 0.8) -> bool:
    """Return whether the smaller summary substantially repeats the larger."""

    left_words = content_words(left)
    right_words = content_words(right)
    return bool(
        left_words
        and right_words
        and len(left_words & right_words) / min(len(left_words), len(right_words)) >= threshold
    )
