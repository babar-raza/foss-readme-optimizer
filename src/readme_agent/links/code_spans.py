"""Locate fenced and inline code spans so link scanners can skip sample data."""

from __future__ import annotations

import re

_FENCED_CODE = re.compile(
    r"(?ms)^(?P<fence>`{3,}|~{3,})[^\r\n]*\r?\n.*?^(?P=fence)[ \t]*(?:\r?\n|$)"
)
_INLINE_CODE = re.compile(r"`+[^`\r\n]+`+")


def protected_code_spans(markdown: str) -> list[tuple[int, int]]:
    """Return every fenced-code-block and inline-code character span.

    A URL that appears only inside one of these spans is sample data (for
    example, a literal passed as an API argument in a verified code
    example), not a visitor-facing navigational link -- GitHub's renderer
    never turns backtick-quoted text into a clickable link either way.
    Callers that govern real Aspose links (budgets, catalog verification,
    hygiene rewrites) must exclude these spans from consideration.
    """

    return [
        match.span()
        for pattern in (_FENCED_CODE, _INLINE_CODE)
        for match in pattern.finditer(markdown)
    ]


def overlaps_protected_span(start: int, end: int, protected: list[tuple[int, int]]) -> bool:
    """True if the half-open span [start, end) overlaps any protected code span."""

    return any(
        start < protected_end and protected_start < end
        for protected_start, protected_end in protected
    )


__all__ = ["overlaps_protected_span", "protected_code_spans"]
