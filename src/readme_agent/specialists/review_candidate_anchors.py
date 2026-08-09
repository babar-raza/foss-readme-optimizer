"""Build stable candidate-block identities for independently grounded review findings."""

from __future__ import annotations

import hashlib
import json

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

_ANCHOR_TOKEN_TYPES = frozenset(
    {
        "blockquote_open",
        "bullet_list_open",
        "fence",
        "heading_open",
        "html_block",
        "ordered_list_open",
        "paragraph_open",
    }
)
_MAX_ANCHOR_CHARACTERS = 12_000


class CandidateReviewAnchorV1(BaseModel):
    """One exact visible Markdown block selectable without copying its bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    anchor_id: str = Field(pattern=r"^candidate\.anchor\.[0-9a-f]{20}\.[0-9]+$")
    text: str = Field(min_length=1, max_length=_MAX_ANCHOR_CHARACTERS)
    start_line: int = Field(ge=1)
    end_line_exclusive: int = Field(ge=2)


def _bounded_block_parts(lines: list[str], start: int, end: int) -> list[tuple[str, int, int]]:
    """Split one oversized source block without omitting or rewriting candidate bytes."""

    text = "".join(lines[start:end]).rstrip("\r\n")
    if len(text) <= _MAX_ANCHOR_CHARACTERS:
        return [(text, start + 1, end + 1)] if text.strip() else []
    parts: list[tuple[str, int, int]] = []
    chunk_lines: list[str] = []
    chunk_start = start
    for line_index in range(start, end):
        line = lines[line_index]
        if len(line.rstrip("\r\n")) > _MAX_ANCHOR_CHARACTERS:
            if chunk_lines:
                chunk = "".join(chunk_lines).rstrip("\r\n")
                parts.append((chunk, chunk_start + 1, line_index + 1))
                chunk_lines = []
            visible = line.rstrip("\r\n")
            for offset in range(0, len(visible), _MAX_ANCHOR_CHARACTERS):
                parts.append(
                    (
                        visible[offset : offset + _MAX_ANCHOR_CHARACTERS],
                        line_index + 1,
                        line_index + 2,
                    )
                )
            chunk_start = line_index + 1
            continue
        candidate = "".join([*chunk_lines, line]).rstrip("\r\n")
        if chunk_lines and len(candidate) > _MAX_ANCHOR_CHARACTERS:
            chunk = "".join(chunk_lines).rstrip("\r\n")
            parts.append((chunk, chunk_start + 1, line_index + 1))
            chunk_lines = [line]
            chunk_start = line_index
        else:
            if not chunk_lines:
                chunk_start = line_index
            chunk_lines.append(line)
    if chunk_lines:
        chunk = "".join(chunk_lines).rstrip("\r\n")
        if chunk.strip():
            parts.append((chunk, chunk_start + 1, end + 1))
    return parts


def build_candidate_review_anchors(markdown: str) -> tuple[CandidateReviewAnchorV1, ...]:
    """Return non-overlapping CommonMark blocks with content-addressed stable identities."""

    lines = markdown.splitlines(keepends=True)
    proposed: set[tuple[int, int]] = set()
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type not in _ANCHOR_TOKEN_TYPES or token.map is None:
            continue
        start, end = token.map
        if start < end:
            proposed.add((start, end))
    selected: list[tuple[int, int]] = []
    for start, end in sorted(proposed, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(
            parent_start <= start and end <= parent_end for parent_start, parent_end in selected
        ):
            continue
        selected.append((start, end))
    occurrences: dict[str, int] = {}
    anchors: list[CandidateReviewAnchorV1] = []
    bounded = [
        part for start, end in sorted(selected) for part in _bounded_block_parts(lines, start, end)
    ]
    for text, start_line, end_line_exclusive in bounded:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]
        occurrence = occurrences.get(digest, 0) + 1
        occurrences[digest] = occurrence
        anchors.append(
            CandidateReviewAnchorV1(
                anchor_id=f"candidate.anchor.{digest}.{occurrence}",
                text=text,
                start_line=start_line,
                end_line_exclusive=end_line_exclusive,
            )
        )
    return tuple(anchors)


def render_candidate_review_anchor_catalog(
    anchors: tuple[CandidateReviewAnchorV1, ...],
) -> str:
    """Render exact blocks as bounded JSON for the reviewer-only selection interface."""

    return json.dumps(
        [anchor.model_dump(mode="json") for anchor in anchors],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def bind_candidate_review_anchors(
    value: object,
    anchors: tuple[CandidateReviewAnchorV1, ...],
) -> object:
    """Replace a blind reviewer's copied quote with exact bytes selected by stable ID."""

    if not isinstance(value, dict) or not isinstance(value.get("findings"), list):
        return value
    by_id = {anchor.anchor_id: anchor for anchor in anchors}
    findings: list[object] = []
    for item in value["findings"]:
        if not isinstance(item, dict):
            findings.append(item)
            continue
        anchor_id = item.get("candidate_anchor_id")
        if anchor_id is None:
            findings.append(item)
            continue
        anchor = by_id.get(str(anchor_id))
        if anchor is None:
            findings.append(item)
            continue
        findings.append({**item, "quoted_candidate_span": anchor.text})
    return {**value, "findings": findings}


def unknown_candidate_review_anchor_ids(
    value: object,
    anchors: tuple[CandidateReviewAnchorV1, ...],
) -> tuple[str, ...]:
    """Return model-selected IDs that are absent from the exact candidate catalog."""

    if not isinstance(value, dict) or not isinstance(value.get("findings"), list):
        return ()
    known = {anchor.anchor_id for anchor in anchors}
    return tuple(
        sorted(
            {
                str(item["candidate_anchor_id"])
                for item in value["findings"]
                if isinstance(item, dict)
                and item.get("candidate_anchor_id") is not None
                and str(item["candidate_anchor_id"]) not in known
            }
        )
    )
