"""Markdown structural analysis for the README document pipeline.

Parses a README into byte-anchored ``Heading`` sections and derives GitHub
heading anchors. Extracted verbatim from the former single-file
``document_renderer`` (`GOVERNANCE.md` "no monoliths").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    start: int
    heading_end: int
    section_end: int


@dataclass(frozen=True)
class CodeBlock:
    start: int
    end: int
    content: str


def line_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def parse_headings(text: str) -> list[Heading]:
    tokens = MarkdownIt("commonmark").parse(text)
    offsets = line_offsets(text)
    raw: list[tuple[int, str, int, int]] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        title = tokens[index + 1].content if index + 1 < len(tokens) else ""
        level = int(token.tag.removeprefix("h"))
        start_line, end_line = token.map
        raw.append((level, title, offsets[start_line], offsets[end_line]))
    headings = []
    for index, (level, title, start, heading_end) in enumerate(raw):
        section_end = len(text)
        for later_level, _, later_start, _ in raw[index + 1 :]:
            if later_level <= level:
                section_end = later_start
                break
        headings.append(Heading(level, title, start, heading_end, section_end))
    return headings


def code_blocks_in_span(text: str, start: int, end: int) -> list[CodeBlock]:
    """Return Markdown code blocks wholly contained in one character span."""

    offsets = line_offsets(text)
    blocks: list[CodeBlock] = []
    for token in MarkdownIt("commonmark").parse(text):
        if token.type not in {"fence", "code_block"} or token.map is None:
            continue
        start_line, end_line = token.map
        block_start = offsets[start_line]
        block_end = offsets[end_line]
        if start <= block_start and block_end <= end:
            blocks.append(CodeBlock(start=block_start, end=block_end, content=token.content))
    return blocks


def github_anchor(title: str) -> str:
    lowered = title.strip().lower()
    lowered = re.sub(r"[^\w\s-]", "", lowered)
    return re.sub(r"[\s-]+", "-", lowered).strip("-")
