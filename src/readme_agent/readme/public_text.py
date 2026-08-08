"""Normalize visitor-facing README terminology without changing code or destinations."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from readme_agent.readme.public_vocabulary import (
    DEFAULT_TECHNICAL_ABBREVIATIONS,
    canonical_abbreviations_from_facts,
    canonicalize_abbreviations,
    compile_abbreviation_pattern,
)

_PROTECTED = re.compile(r"`[^`\n]+`|(?<=\]\()[^)\s]+|<https?://[^>\s]+>")
_QUALIFIED_IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
_IMPLEMENTATION_SUFFIX = re.compile(r"(?i)\s+(?:via|using)\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\s*$")
_HEADING = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
_MINOR_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class PublicTextCorrection:
    character_start: int
    character_end: int
    replacement: str
    standard_id: str
    rationale: str


def visitor_capability_phrase(value: str) -> str:
    """Remove implementation identifiers from one visitor-facing capability label."""

    normalized = " ".join(value.strip().rstrip(".").split())
    return _IMPLEMENTATION_SUFFIX.sub("", normalized).strip()


def _transform_unprotected(value: str, transform) -> str:
    parts: list[str] = []
    position = 0
    for match in _PROTECTED.finditer(value):
        parts.extend((transform(value[position : match.start()]), match.group(0)))
        position = match.end()
    parts.append(transform(value[position:]))
    return "".join(parts)


def _title_case_unprotected(
    value: str,
    canonical_terms: Iterable[str] = DEFAULT_TECHNICAL_ABBREVIATIONS,
) -> str:
    words = re.split(r"(\s+)", value)
    word_indexes = [index for index, word in enumerate(words) if word and not word.isspace()]
    if not word_indexes:
        return value
    first = word_indexes[0]
    last = word_indexes[-1]
    rendered: list[str] = []
    for index, word in enumerate(words):
        if word.isspace() or not word:
            rendered.append(word)
            continue
        leading = re.match(r"^[^A-Za-z0-9`]*", word).group(0)  # type: ignore[union-attr]
        if len(leading) == len(word):
            rendered.append(word)
            continue
        trailing = re.search(r"[^A-Za-z0-9`]*$", word).group(0)  # type: ignore[union-attr]
        core_end = len(word) - len(trailing) if trailing else len(word)
        core = word[len(leading) : core_end]
        if not core or core.startswith("`") or any(char.isupper() for char in core[1:]):
            titled = core
        elif index not in {first, last} and core.casefold() in _MINOR_WORDS:
            titled = core.casefold()
        else:
            pieces = re.split(r"([/-])", core)
            titled = "".join(
                piece if piece in {"/", "-"} else piece[:1].upper() + piece[1:].lower()
                for piece in pieces
            )
        rendered.append(leading + canonicalize_abbreviations(titled, canonical_terms) + trailing)
    return "".join(rendered)


def title_case_heading(
    value: str,
    canonical_terms: Iterable[str] = DEFAULT_TECHNICAL_ABBREVIATIONS,
) -> str:
    """Apply readable title case while preserving technical and code tokens."""

    return _transform_unprotected(
        value,
        lambda segment: _title_case_unprotected(segment, canonical_terms),
    )


def canonicalize_public_markdown(
    markdown: str,
    canonical_terms: Iterable[str] = DEFAULT_TECHNICAL_ABBREVIATIONS,
) -> str:
    """Normalize public prose/headings while preserving code and link destinations."""

    lines = markdown.splitlines(keepends=True)
    rendered: list[str] = []
    fence_language: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if fence_language is None:
                fence_language = stripped[3:].strip().casefold()
            else:
                fence_language = None
            rendered.append(line)
            continue
        if fence_language is not None:
            rendered.append(
                _transform_unprotected_with_pattern(
                    line,
                    _QUALIFIED_IDENTIFIER,
                    lambda value: canonicalize_abbreviations(value, canonical_terms),
                )
                if fence_language == "mermaid"
                else line
            )
            continue
        line_ending = "\n" if line.endswith("\n") else ""
        body = line[:-1] if line_ending else line
        heading = _HEADING.match(body)
        if heading is not None:
            body = (
                f"{heading.group('marks')} "
                f"{title_case_heading(heading.group('title'), canonical_terms)}"
            )
        else:
            body = _transform_unprotected(
                body, lambda value: canonicalize_abbreviations(value, canonical_terms)
            )
        rendered.append(body + line_ending)
    return "".join(rendered)


def heading_is_title_case(
    value: str,
    canonical_terms: Iterable[str] = DEFAULT_TECHNICAL_ABBREVIATIONS,
) -> bool:
    """Return whether one public heading follows the canonical title-case policy."""

    return value == title_case_heading(value, canonical_terms)


def _transform_unprotected_with_pattern(value: str, pattern: re.Pattern[str], transform) -> str:
    parts: list[str] = []
    position = 0
    for match in pattern.finditer(value):
        parts.extend((transform(value[position : match.start()]), match.group(0)))
        position = match.end()
    parts.append(transform(value[position:]))
    return "".join(parts)


def public_text_corrections(
    markdown: str,
    canonical_terms: Iterable[str] = DEFAULT_TECHNICAL_ABBREVIATIONS,
) -> list[PublicTextCorrection]:
    """Return exact public heading and abbreviation corrections outside executable code."""

    corrections: list[PublicTextCorrection] = []
    offset = 0
    fence_language: str | None = None
    for raw in markdown.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            if fence_language is None:
                fence_language = stripped[3:].strip().casefold()
            else:
                fence_language = None
            offset += len(raw)
            continue
        if fence_language is not None:
            if fence_language == "mermaid":
                protected = [match.span() for match in _QUALIFIED_IDENTIFIER.finditer(line)]
                for match in compile_abbreviation_pattern(canonical_terms).finditer(line):
                    if any(start <= match.start() < end for start, end in protected):
                        continue
                    replacement = canonicalize_abbreviations(match.group(0), canonical_terms)
                    if match.group(0) != replacement:
                        corrections.append(
                            PublicTextCorrection(
                                offset + match.start(),
                                offset + match.end(),
                                replacement,
                                "readme.technical_abbreviation_case",
                                "Use canonical uppercase technical abbreviation casing.",
                            )
                        )
            offset += len(raw)
            continue
        heading = _HEADING.match(line)
        if heading is not None:
            replacement = title_case_heading(heading.group("title"), canonical_terms)
            if heading.group("title") != replacement:
                corrections.append(
                    PublicTextCorrection(
                        offset + heading.start("title"),
                        offset + heading.end("title"),
                        replacement,
                        "readme.heading_title_case",
                        "Apply the portfolio title-case heading contract.",
                    )
                )
            offset += len(raw)
            continue
        protected = [match.span() for match in _PROTECTED.finditer(line)]
        for match in compile_abbreviation_pattern(canonical_terms).finditer(line):
            if any(start <= match.start() < end for start, end in protected):
                continue
            replacement = canonicalize_abbreviations(match.group(0), canonical_terms)
            if match.group(0) != replacement:
                corrections.append(
                    PublicTextCorrection(
                        offset + match.start(),
                        offset + match.end(),
                        replacement,
                        "readme.technical_abbreviation_case",
                        "Use canonical uppercase technical abbreviation casing.",
                    )
                )
        offset += len(raw)
    unique = {
        (item.character_start, item.character_end, item.replacement, item.standard_id): item
        for item in corrections
    }
    return sorted(unique.values(), key=lambda item: (item.character_start, item.character_end))


__all__ = [
    "canonicalize_abbreviations",
    "canonical_abbreviations_from_facts",
    "canonicalize_public_markdown",
    "heading_is_title_case",
    "public_text_corrections",
    "title_case_heading",
    "visitor_capability_phrase",
]
