"""Shared text and stable-finding helpers for README presentation lint."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from markdown_it import MarkdownIt

from readme_agent.facts.example_quality import strip_source_comments
from readme_agent.readme.document_structure import line_offsets
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
        protected_index = 0
        index = 0
        while index < len(line.text):
            while protected_index < len(protected) and protected[protected_index][1] <= index:
                protected_index += 1
            inside_inline_code = (
                protected_index < len(protected)
                and protected[protected_index][0] <= index < protected[protected_index][1]
            )
            if not _is_emoji_base(line.text[index]) or inside_inline_code:
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


def strip_fenced_code_comments(text: str) -> str:
    """Remove comments from generated fenced code while preserving fence syntax."""

    offsets = line_offsets(text)
    replacements: list[tuple[int, int, str]] = []
    for token in MarkdownIt("commonmark").parse(text):
        if token.type != "fence" or token.map is None:
            continue
        language = token.info.strip().split(maxsplit=1)[0]
        if not language or language.casefold() == "mermaid":
            continue
        start_line, end_line = token.map
        block_start = offsets[start_line]
        block_end = offsets[end_line]
        block = text[block_start:block_end]
        content_start = block.find(token.content)
        if content_start < 0:
            continue
        absolute_start = block_start + content_start
        absolute_end = absolute_start + len(token.content)
        replacement = strip_source_comments(language, token.content)
        if replacement != token.content:
            replacements.append((absolute_start, absolute_end, replacement))
    normalized = text
    for start, end, replacement in reversed(replacements):
        normalized = normalized[:start] + replacement + normalized[end:]
    return normalized


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
