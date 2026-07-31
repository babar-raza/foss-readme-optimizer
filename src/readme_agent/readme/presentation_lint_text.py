"""Shared text and stable-finding helpers for README presentation lint."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from readme_agent.readme.presentation_lint_models import (
    PresentationLintFindingV1,
    PresentationLintSpanV1,
)

_INLINE_CODE = re.compile(r"`+[^`\r\n]+`+")


@dataclass(frozen=True)
class VisibleLine:
    start: int
    end: int
    text: str


def visible_lines(text: str) -> list[VisibleLine]:
    """Return non-fenced lines with exact character offsets."""

    lines: list[VisibleLine] = []
    offset = 0
    fenced = False
    for raw in text.splitlines(keepends=True):
        content = raw.rstrip("\r\n")
        if content.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            lines.append(VisibleLine(offset, offset + len(content), content))
        offset += len(raw)
    return lines


def _is_emoji_base(character: str) -> bool:
    codepoint = ord(character)
    return 0x2600 <= codepoint <= 0x27BF or 0x1F000 <= codepoint <= 0x1FAFF


def emoji_decoration_spans(markdown: str) -> list[tuple[int, int]]:
    """Return visible emoji spans without touching fenced or inline code."""

    spans: list[tuple[int, int]] = []
    for line in visible_lines(markdown):
        protected = [match.span() for match in _INLINE_CODE.finditer(line.text)]
        index = 0
        while index < len(line.text):
            if not _is_emoji_base(line.text[index]) or any(
                start <= index < end for start, end in protected
            ):
                index += 1
                continue
            start = index
            index += 1
            while index < len(line.text) and (
                _is_emoji_base(line.text[index])
                or line.text[index] in {"\ufe0f", "\u200d"}
                or 0x1F3FB <= ord(line.text[index]) <= 0x1F3FF
            ):
                index += 1
            if index < len(line.text) and line.text[index] == " ":
                index += 1
            spans.append((line.start + start, line.start + index))
    return spans


def strip_emoji_decorations(text: str) -> str:
    """Remove visitor-visible emoji decorations from a text fragment."""

    rendered = text
    for start, end in reversed(emoji_decoration_spans(text)):
        rendered = rendered[:start] + rendered[end:]
    return rendered


def exact_span(text: str, start: int, end: int) -> PresentationLintSpanV1:
    return PresentationLintSpanV1(start=start, end=end, text=text[start:end])


def line_span(text: str, line: VisibleLine) -> PresentationLintSpanV1:
    leading = len(line.text) - len(line.text.lstrip())
    trailing = len(line.text.rstrip())
    return exact_span(text, line.start + leading, line.start + trailing)


def make_finding(
    rule_id: str,
    message: str,
    spans: list[PresentationLintSpanV1],
    *,
    severity: Literal["critical", "warning"] = "critical",
) -> PresentationLintFindingV1:
    ordered = sorted(spans, key=lambda span: (span.start, span.end, span.text))
    fingerprint = hashlib.sha256(
        (
            rule_id
            + "\0"
            + "\0".join(
                f"{span.start}\0{span.end}\0{span.text}\0{index}"
                for index, span in enumerate(ordered)
            )
        ).encode("utf-8")
    ).hexdigest()[:12]
    return PresentationLintFindingV1(
        finding_id=f"presentation.{rule_id}.{fingerprint}",
        rule_id=rule_id,
        severity=severity,
        message=message,
        spans=ordered,
    )
