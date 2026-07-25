"""Markdown-aware fingerprints for technical and maintainer-authored content."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from readme_agent.readme.markers import SPAN_NAMES, remove_span

ProtectedCategory = Literal[
    "technical_terminology",
    "command",
    "example",
    "limitation",
]

_LIMITATION_HEADINGS = (
    "limitation",
    "known issue",
    "not supported",
    "compatibility",
    "caveat",
)
_COMMAND_RE = re.compile(
    r"^\s*(?:[$>]\s*)?(?:pip|python\s+-m\s+pip|npm|npx|yarn|pnpm|dotnet|"
    r"mvn|gradle|go|cargo|cmake|make|git)\b",
    re.IGNORECASE,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProtectedFragmentV1(_StrictModel):
    fragment_id: str
    category: ProtectedCategory
    content_hash: str
    source_descriptor: str


class ProtectedContentSnapshotV1(_StrictModel):
    schema_version: Literal[1] = 1
    maintainer_region_hash: str
    fragments: list[ProtectedFragmentV1] = Field(default_factory=list)


class ProtectedContentLossV1(_StrictModel):
    fragment_id: str
    category: str
    reason: str


class ProtectedContentDecisionV1(_StrictModel):
    valid: bool
    losses: list[ProtectedContentLossV1] = Field(default_factory=list)


def _normalized(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def _hash(text: str) -> str:
    return hashlib.sha256(_normalized(text).encode("utf-8")).hexdigest()


def _fragment(
    category: ProtectedCategory, text: str, source_descriptor: str
) -> ProtectedFragmentV1:
    digest = _hash(text)
    return ProtectedFragmentV1(
        fragment_id=f"{category}:{digest[:16]}",
        category=category,
        content_hash=digest,
        source_descriptor=source_descriptor,
    )


def _without_owned_spans(readme_text: str) -> str:
    stripped = readme_text
    for span_name in SPAN_NAMES:
        stripped = remove_span(stripped, span_name)
    return stripped


def fingerprint_protected_content(readme_text: str) -> ProtectedContentSnapshotV1:
    """Parse CommonMark with markdown-it-py and fingerprint protected semantics."""

    maintainer_text = _without_owned_spans(readme_text)
    tokens = MarkdownIt("commonmark").parse(maintainer_text)
    lines = maintainer_text.replace("\r\n", "\n").splitlines()
    fragments: dict[tuple[str, str], ProtectedFragmentV1] = {}

    for index, token in enumerate(tokens):
        if token.type in {"fence", "code_block"} and token.content.strip():
            example = _fragment("example", token.content, f"markdown:{token.type}")
            fragments[(example.category, example.content_hash)] = example
            for line in token.content.splitlines():
                if _COMMAND_RE.match(line):
                    command = _fragment("command", line, f"markdown:{token.type}")
                    fragments[(command.category, command.content_hash)] = command
        if token.type == "inline":
            for child in token.children or []:
                if child.type != "code_inline" or not child.content.strip():
                    continue
                terminology = _fragment(
                    "technical_terminology", child.content, "markdown:inline_code"
                )
                fragments[(terminology.category, terminology.content_hash)] = terminology
                if _COMMAND_RE.match(child.content):
                    command = _fragment("command", child.content, "markdown:inline_code")
                    fragments[(command.category, command.content_hash)] = command
        if token.type != "heading_open" or token.map is None:
            continue
        heading_text = tokens[index + 1].content if index + 1 < len(tokens) else ""
        if not any(marker in heading_text.lower() for marker in _LIMITATION_HEADINGS):
            continue
        level = int(token.tag.removeprefix("h"))
        start = token.map[0]
        end = len(lines)
        for later in tokens[index + 1 :]:
            if later.type != "heading_open" or later.map is None:
                continue
            later_level = int(later.tag.removeprefix("h"))
            if later_level <= level:
                end = later.map[0]
                break
        section = "\n".join(lines[start:end])
        limitation = _fragment("limitation", section, f"markdown:heading:{heading_text}")
        fragments[(limitation.category, limitation.content_hash)] = limitation

    return ProtectedContentSnapshotV1(
        maintainer_region_hash=_hash(maintainer_text),
        fragments=sorted(fragments.values(), key=lambda item: (item.category, item.fragment_id)),
    )


def validate_protected_content(
    before: ProtectedContentSnapshotV1,
    after: ProtectedContentSnapshotV1,
    *,
    require_maintainer_region_unchanged: bool = True,
) -> ProtectedContentDecisionV1:
    losses = []
    if (
        require_maintainer_region_unchanged
        and before.maintainer_region_hash != after.maintainer_region_hash
    ):
        losses.append(
            ProtectedContentLossV1(
                fragment_id="maintainer_region",
                category="maintainer_region",
                reason="content outside agent-owned spans changed",
            )
        )
    after_keys = {(fragment.category, fragment.content_hash) for fragment in after.fragments}
    for fragment in before.fragments:
        if (fragment.category, fragment.content_hash) not in after_keys:
            losses.append(
                ProtectedContentLossV1(
                    fragment_id=fragment.fragment_id,
                    category=fragment.category,
                    reason=f"protected {fragment.category} content was removed or changed",
                )
            )
    return ProtectedContentDecisionV1(valid=not losses, losses=losses)


def protected_fragment_ids_overlapping_byte_span(
    readme_text: str,
    byte_start: int,
    byte_end: int,
) -> set[str]:
    """Return protected fragment IDs whose Markdown source overlaps an exact byte span."""

    tokens = MarkdownIt("commonmark").parse(readme_text)
    # Markdown token maps use logical line numbers, while the caller supplies
    # byte offsets in the original document. Preserve each original line
    # ending here so CRLF documents do not shift every span after line one.
    lines = readme_text.splitlines(keepends=True)
    line_byte_starts = [0]
    for line in lines:
        line_byte_starts.append(line_byte_starts[-1] + len(line.encode("utf-8")))

    def overlaps(line_range: list[int] | None) -> bool:
        if line_range is None:
            return False
        start_line, end_line = line_range
        token_start = line_byte_starts[start_line]
        token_end = line_byte_starts[min(end_line, len(lines))]
        return byte_start < token_end and token_start < byte_end

    fragment_ids: set[str] = set()
    for index, token in enumerate(tokens):
        if token.type in {"fence", "code_block"} and token.content.strip() and overlaps(token.map):
            fragment_ids.add(
                _fragment("example", token.content, f"markdown:{token.type}").fragment_id
            )
            fragment_ids.update(
                _fragment("command", line, f"markdown:{token.type}").fragment_id
                for line in token.content.splitlines()
                if _COMMAND_RE.match(line)
            )
        if token.type == "inline" and overlaps(token.map):
            for child in token.children or []:
                if child.type != "code_inline" or not child.content.strip():
                    continue
                fragment_ids.add(
                    _fragment(
                        "technical_terminology",
                        child.content,
                        "markdown:inline_code",
                    ).fragment_id
                )
                if _COMMAND_RE.match(child.content):
                    fragment_ids.add(
                        _fragment("command", child.content, "markdown:inline_code").fragment_id
                    )
        if token.type != "heading_open" or token.map is None:
            continue
        heading_text = tokens[index + 1].content if index + 1 < len(tokens) else ""
        if not any(marker in heading_text.lower() for marker in _LIMITATION_HEADINGS):
            continue
        level = int(token.tag.removeprefix("h"))
        start_line = token.map[0]
        end_line = len(lines)
        for later in tokens[index + 1 :]:
            if later.type == "heading_open" and later.map is not None:
                if int(later.tag.removeprefix("h")) <= level:
                    end_line = later.map[0]
                    break
        if overlaps([start_line, end_line]):
            section = "".join(lines[start_line:end_line]).rstrip("\r\n")
            fragment_ids.add(
                _fragment(
                    "limitation",
                    section,
                    f"markdown:heading:{heading_text}",
                ).fragment_id
            )
    return fragment_ids
