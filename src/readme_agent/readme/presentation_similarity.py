"""Share deterministic visitor-summary similarity semantics."""

from __future__ import annotations

import re

from readme_agent.readme.public_vocabulary import DOCUMENT_FORMAT_ABBREVIATIONS

_RASTER_FORMATS = frozenset({"BMP", "GIF", "JPEG", "JPG", "PNG", "TIFF"})


def capability_discriminators(value: str) -> set[str]:
    """Return normalized format/direction terms that distinguish capabilities."""

    uppercase = value.upper()
    present = {
        term
        for term in DOCUMENT_FORMAT_ABBREVIATIONS
        if re.search(rf"(?<![A-Z0-9_-]){re.escape(term)}(?![A-Z0-9_-])", uppercase)
    }
    if present.intersection(_RASTER_FORMATS):
        present.difference_update(_RASTER_FORMATS)
        present.add("IMAGE")
    if re.search(r"(?i)\bimages?\b", value):
        present.add("IMAGE")
    return present


def content_words(value: str) -> set[str]:
    """Return stable visitor-significant words for overlap checks.

    A token survives the length-3 stopword-like floor if it is longer than 2
    characters, OR if it contains a digit -- a short digit-bearing token (a
    barcode symbology number, a page size, a format version) is almost never
    noise and is exactly the kind of distinguishing identifier overlap checks
    must not silently drop (e.g. "39" in "Code 39" vs "128" in "Code 128").
    """

    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 or any(character.isdigit() for character in token)
    }


def summaries_overlap(left: str, right: str, *, threshold: float = 0.8) -> bool:
    """Return whether the smaller summary substantially repeats the larger."""

    left_words = content_words(left)
    right_words = content_words(right)
    return bool(
        left_words
        and right_words
        and len(left_words & right_words) / min(len(left_words), len(right_words)) >= threshold
    )


def semantic_content_words(value: str) -> set[str]:
    """Return lightly normalized terms for cross-section repetition detection."""

    ignored = {
        "aspose",
        "available",
        "currently",
        "foss",
        "for",
        "from",
        "python",
        "supports",
        "the",
        "use",
        "with",
    }
    normalized: set[str] = set()
    for token in content_words(value):
        if token in ignored:
            continue
        if token == "conversion":
            token = "convert"
        elif token.endswith("ation") and len(token) > 7:
            token = token[:-5] + "e"
        elif token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 5:
            token = token[:-2]
        normalized.add(token)
    if normalized.intersection({"bmp", "gif", "jpeg", "jpg", "png", "tiff"}):
        normalized.add("image")
    return normalized


def semantically_repeats(left: str, right: str, *, threshold: float = 0.7) -> bool:
    """Return whether one visitor statement repeats another after light normalization."""

    left_words = semantic_content_words(left)
    right_words = semantic_content_words(right)
    return bool(
        left_words
        and right_words
        and len(left_words & right_words) / min(len(left_words), len(right_words)) >= threshold
    )
