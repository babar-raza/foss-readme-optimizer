"""Markdown structural analysis for the README document pipeline.

Parses a README into byte-anchored ``Heading`` sections and derives GitHub
heading anchors. Extracted verbatim from the former single-file
``document_renderer`` (`GOVERNANCE.md` "no monoliths").
"""

from __future__ import annotations

import re
from collections.abc import Mapping
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


def normalize_navigation_targets(
    markdown: str,
    *,
    boundary_line_prefix: str | None = None,
) -> str:
    """Rebuild Navigation from the final H2 headings and their GitHub anchors."""

    headings = [heading for heading in parse_headings(markdown) if heading.level == 2]
    navigation = next(
        (heading for heading in headings if heading.title.casefold() == "navigation"),
        None,
    )
    if navigation is None:
        return markdown
    labels = [heading.title for heading in headings if heading.title.casefold() != "navigation"]
    if not labels:
        return markdown
    section_end = navigation.section_end
    if boundary_line_prefix:
        boundary = markdown.find(boundary_line_prefix, navigation.heading_end, section_end)
        if boundary >= 0:
            section_end = boundary
    body = "\n" + "\n".join(f"- [{label}](#{github_anchor(label)})" for label in labels) + "\n\n"
    rebuilt = markdown[: navigation.heading_end] + body + markdown[section_end:]
    targets = {
        heading.title.strip().casefold(): github_anchor(heading.title)
        for heading in parse_headings(rebuilt)
    }

    def replace_fragment(match: re.Match[str]) -> str:
        target = targets.get(match.group("label").strip().casefold())
        return f"[{match.group('label')}](#{target})" if target else match.group(0)

    return re.sub(
        r"\[(?P<label>[^\]]+)\]\(#[^)]+\)",
        replace_fragment,
        rebuilt,
    )


def remove_excess_headings(
    markdown: str,
    allowed_counts: Mapping[tuple[int, str], int],
) -> str:
    """Remove only heading repetitions beyond the source document's multiplicity."""

    seen: dict[tuple[int, str], int] = {}
    removals: list[tuple[int, int]] = []
    for heading in parse_headings(markdown):
        key = (heading.level, heading.title.strip().casefold())
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > max(allowed_counts.get(key, 0), 1):
            removals.append((heading.start, heading.heading_end))
    normalized = markdown
    for start, end in reversed(removals):
        normalized = normalized[:start] + normalized[end:]
    return normalized
