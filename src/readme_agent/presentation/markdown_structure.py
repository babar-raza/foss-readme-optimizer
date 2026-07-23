"""Markdown-it-backed source structure with UTF-8 byte spans."""

from __future__ import annotations

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field


class MarkdownSourceNodeV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token_type: str
    tag: str
    line_start: int = Field(ge=0)
    line_end: int = Field(ge=0)
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    markup: str = ""
    info: str = ""
    text: str = ""
    links: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)


class MarkdownStructureV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_sha256: str
    nodes: list[MarkdownSourceNodeV1]

    @property
    def headings(self) -> list[MarkdownSourceNodeV1]:
        return [node for node in self.nodes if node.token_type == "heading_open"]

    @property
    def code_blocks(self) -> list[MarkdownSourceNodeV1]:
        return [node for node in self.nodes if node.token_type in {"fence", "code_block"}]

    @property
    def link_targets(self) -> list[str]:
        return [link for node in self.nodes for link in node.links]

    @property
    def image_targets(self) -> list[str]:
        return [image for node in self.nodes for image in node.images]


def _line_byte_offsets(source: str) -> list[int]:
    offsets = [0]
    total = 0
    for line in source.splitlines(keepends=True):
        total += len(line.encode("utf-8"))
        offsets.append(total)
    if not source.splitlines(keepends=True):
        return [0]
    return offsets


def _inline_details(token) -> tuple[str, list[str], list[str]]:
    if token.type != "inline":
        return "", [], []
    links: list[str] = []
    images: list[str] = []
    for child in token.children or []:
        if child.type == "link_open":
            href = child.attrGet("href")
            if href:
                links.append(href)
        elif child.type == "image":
            src = child.attrGet("src")
            if src:
                images.append(src)
    return token.content, links, images


def parse_markdown_structure(source: str) -> MarkdownStructureV1:
    """Parse block structure through markdown-it; no README prose controls behavior."""

    import hashlib

    tokens = MarkdownIt("commonmark").parse(source)
    offsets = _line_byte_offsets(source)
    lines = source.splitlines(keepends=True)
    nodes: list[MarkdownSourceNodeV1] = []
    for index, token in enumerate(tokens):
        if token.map is None:
            continue
        line_start, line_end = token.map
        if line_start < 0 or line_end < line_start or line_end > len(lines):
            raise ValueError(f"markdown-it returned invalid line map {token.map}")
        text, links, images = _inline_details(token)
        if token.type == "heading_open" and index + 1 < len(tokens):
            text, links, images = _inline_details(tokens[index + 1])
        nodes.append(
            MarkdownSourceNodeV1(
                token_type=token.type,
                tag=token.tag,
                line_start=line_start,
                line_end=line_end,
                byte_start=offsets[line_start],
                byte_end=offsets[line_end],
                markup=token.markup,
                info=token.info,
                text=text,
                links=links,
                images=images,
            )
        )
    return MarkdownStructureV1(
        source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        nodes=nodes,
    )
