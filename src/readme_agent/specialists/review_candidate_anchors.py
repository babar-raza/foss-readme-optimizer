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
CANDIDATE_REVIEW_ANCHOR_BINDING_CONTRACT_VERSION = "2"


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


def reconcile_unknown_candidate_review_anchors(
    value: object,
    anchors: tuple[CandidateReviewAnchorV1, ...],
    candidate_text: str,
) -> tuple[object, tuple[str, ...]]:
    """Replace a stale redundant anchor only when its exact quote is unique."""

    if not isinstance(value, dict) or not isinstance(value.get("findings"), list):
        return value, ()
    known = {anchor.anchor_id for anchor in anchors}
    by_content_identity: dict[str, list[CandidateReviewAnchorV1]] = {}
    by_text: dict[str, list[CandidateReviewAnchorV1]] = {}
    for anchor in anchors:
        content_identity, _occurrence = anchor.anchor_id.rsplit(".", maxsplit=1)
        by_content_identity.setdefault(content_identity, []).append(anchor)
        by_text.setdefault(anchor.text, []).append(anchor)
    findings: list[object] = []
    reconciled_ids: list[str] = []
    for item in value["findings"]:
        if not isinstance(item, dict):
            findings.append(item)
            continue
        anchor_id = item.get("candidate_anchor_id")
        if anchor_id is None or str(anchor_id) in known:
            findings.append(item)
            continue
        content_identity, separator, _occurrence = str(anchor_id).rpartition(".")
        identity_matches = by_content_identity.get(content_identity, []) if separator else []
        if len(identity_matches) == 1:
            findings.append({**item, "candidate_anchor_id": identity_matches[0].anchor_id})
            finding_id = item.get("finding_id")
            if isinstance(finding_id, str) and finding_id:
                reconciled_ids.append(finding_id)
            continue
        quote = item.get("quoted_candidate_span")
        if not isinstance(quote, str) or not quote or candidate_text.count(quote) != 1:
            findings.append(item)
            continue
        exact_anchors = by_text.get(quote, [])
        replacement_id = exact_anchors[0].anchor_id if len(exact_anchors) == 1 else None
        findings.append({**item, "candidate_anchor_id": replacement_id})
        finding_id = item.get("finding_id")
        if isinstance(finding_id, str) and finding_id:
            reconciled_ids.append(finding_id)
    if not reconciled_ids:
        return value, ()
    return {**value, "findings": findings}, tuple(reconciled_ids)


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
