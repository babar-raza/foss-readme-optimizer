"""Identify inherited README shell and comment spans superseded by verified presentation."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from markdown_it import MarkdownIt
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, String
from pygments.util import ClassNotFound

from readme_agent.readme.document_structure import heading_identity, line_offsets, parse_headings
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1

_BADGE = re.compile(r"(?:!\[[^\]]+\]\([^)]+\)|\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\))")
_HTML_COMMENT = re.compile(r"(?s)<!--[\s\S]*?-->[ \t]*(?:\r?\n|$)")
_CLOSING_FENCE = re.compile(r"^[ ]{0,3}(?P<marker>`{3,}|~{3,})[ \t]*(?:\r?\n)?$")
_NAVIGATION_SHELL_IDENTITIES = frozenset(
    {"contents", "navigation", "quick-links", "table-of-contents"}
)
_SHELL_OMISSION_STANDARD_IDS = frozenset(
    {"readme.at_a_glance", "readme.badges", "readme.navigation", "readme.no_comments"}
)
_MERMAID = re.compile(r"(?m)^```mermaid(?:[ \t].*)?$")


class _PolicyEdit(Protocol):
    source_byte_start: int
    source_byte_end: int
    replacement: str
    fact_ids: list[str]
    configured_standard_ids: list[str]


@dataclass(frozen=True)
class SourceShellPolicySpan:
    """One character-addressed source span governed by a presentation standard."""

    character_start: int
    character_end: int
    standard_id: str
    rationale: str
    replacement: str = ""


@dataclass(frozen=True)
class _FenceSpan:
    character_start: int
    character_end: int
    body_start: int
    body_end: int
    info: str


def _fence_spans(markdown: str) -> list[_FenceSpan]:
    """Map CommonMark fence tokens back to exact source character spans."""

    offsets = line_offsets(markdown)
    lines = markdown.splitlines(keepends=True)
    spans: list[_FenceSpan] = []
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type != "fence" or token.map is None:
            continue
        start_line, end_line = token.map
        if start_line + 1 > end_line or end_line > len(lines):
            continue
        body_start = offsets[start_line + 1]
        body_end = offsets[end_line]
        if end_line > start_line + 1:
            closing = _CLOSING_FENCE.fullmatch(lines[end_line - 1])
            if (
                closing is not None
                and closing.group("marker")[0] == token.markup[0]
                and len(closing.group("marker")) >= len(token.markup)
            ):
                body_end = offsets[end_line - 1]
        spans.append(
            _FenceSpan(
                character_start=offsets[start_line],
                character_end=offsets[end_line],
                body_start=body_start,
                body_end=body_end,
                info=token.info.strip(),
            )
        )
    return spans


def _visitor_visible(fences: list[_FenceSpan], start: int, end: int) -> bool:
    return not any(fence.character_start < end and start < fence.character_end for fence in fences)


def _shell_spans(source_text: str) -> list[SourceShellPolicySpan]:
    spans: list[SourceShellPolicySpan] = []
    fences = _fence_spans(source_text)
    for heading in parse_headings(source_text):
        if heading.level != 2:
            continue
        identity = heading_identity(heading.title)
        if identity in _NAVIGATION_SHELL_IDENTITIES:
            spans.append(
                SourceShellPolicySpan(
                    heading.start,
                    heading.section_end,
                    "readme.navigation",
                    "Omit the inherited navigation shell because the compiled template owns "
                    "one complete list-based Navigation section.",
                )
            )
            continue
        if identity != "at-a-glance":
            continue
        for fence in fences:
            if not (
                heading.heading_end <= fence.character_start
                and fence.character_end <= heading.section_end
            ):
                continue
            info = fence.info.split(maxsplit=1)
            if not info or info[0].casefold() != "mermaid":
                continue
            spans.append(
                SourceShellPolicySpan(
                    fence.character_start,
                    fence.character_end,
                    "readme.at_a_glance",
                    "Omit the inherited At-a-glance diagram because the compiled template "
                    "owns one repository-fact-backed Mermaid visualization.",
                )
            )

    offset = 0
    for line in source_text.splitlines(keepends=True):
        if _BADGE.search(line) and not _BADGE.sub("", line).strip():
            spans.append(
                SourceShellPolicySpan(
                    offset,
                    offset + len(line),
                    "readme.badges",
                    "Omit the inherited badge row because the compiled template owns one "
                    "fact-backed canonical badge row.",
                )
            )
        offset += len(line)

    for comment in _HTML_COMMENT.finditer(source_text):
        if _visitor_visible(fences, comment.start(), comment.end()):
            spans.append(
                SourceShellPolicySpan(
                    comment.start(),
                    comment.end(),
                    "readme.no_comments",
                    "Omit an inherited HTML comment under the no-comments standard.",
                )
            )
    return spans


def _comment_token_spans(language: str, body: str) -> list[tuple[int, int]]:
    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return []
    spans: list[tuple[int, int]] = []
    cursor = 0
    for token, value in lex(body, lexer):
        start = cursor
        end = cursor + len(value)
        cursor = end
        if not (
            (token in Comment and token not in Comment.Preproc and token not in Comment.PreprocFile)
            or token in String.Doc
        ):
            continue
        line_start = body.rfind("\n", 0, start) + 1
        line_end = body.find("\n", end)
        line_end = len(body) if line_end < 0 else line_end + 1
        if not body[line_start:start].strip() and not body[end:line_end].strip():
            start, end = line_start, line_end
        else:
            start = len(body[:start].rstrip(" \t"))
        if start < end:
            spans.append((start, end))
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _source_comment_spans(source_text: str) -> list[SourceShellPolicySpan]:
    spans: list[SourceShellPolicySpan] = []
    for fence in _fence_spans(source_text):
        info = fence.info
        if not info:
            continue
        language = info.split(maxsplit=1)[0].casefold()
        body = source_text[fence.body_start : fence.body_end]
        for relative_start, relative_end in _comment_token_spans(language, body):
            spans.append(
                SourceShellPolicySpan(
                    fence.body_start + relative_start,
                    fence.body_start + relative_end,
                    "readme.no_comments",
                    "Omit an inherited source-code comment while retaining the surrounding "
                    "curated executable code under exact source lineage.",
                )
            )
    return spans


def source_shell_policy_spans(source_text: str) -> list[SourceShellPolicySpan]:
    """Return non-overlapping inherited shell and source-comment policy spans."""

    spans = [*_shell_spans(source_text), *_source_comment_spans(source_text)]
    accepted: list[SourceShellPolicySpan] = []
    for span in sorted(spans, key=lambda item: (item.character_start, -item.character_end)):
        if any(
            existing.character_start < span.character_end
            and span.character_start < existing.character_end
            for existing in accepted
        ):
            continue
        accepted.append(span)
    return accepted


def fully_omitted_by_shell_policy(
    source_byte_start: int,
    source_byte_end: int,
    policy_edits: Sequence[_PolicyEdit],
) -> bool:
    """Return whether one exact source block is wholly superseded by compiled shell policy."""

    return any(
        not edit.replacement
        and edit.source_byte_start <= source_byte_start
        and source_byte_end <= edit.source_byte_end
        for edit in policy_edits
    )


def unapplied_shell_omission_corrections(
    source_text: str,
    policy_edits: Sequence[_PolicyEdit],
    applied: list[SourceClaimPolicyCorrectionV1],
) -> list[SourceClaimPolicyCorrectionV1]:
    """Retain exact lineage when a superseded shell never enters candidate bytes."""

    applied_spans = {
        (correction.source_byte_start, correction.source_byte_end) for correction in applied
    }
    source = source_text.encode("utf-8")
    empty_hash = hashlib.sha256(b"").hexdigest()
    corrections = list(applied)
    for edit in policy_edits:
        span = (edit.source_byte_start, edit.source_byte_end)
        if (
            edit.replacement
            or span in applied_spans
            or not _SHELL_OMISSION_STANDARD_IDS.intersection(edit.configured_standard_ids)
        ):
            continue
        corrections.append(
            SourceClaimPolicyCorrectionV1(
                correction_id=f"source.policy.{span[0]}-{span[1]}",
                disposition="omit",
                source_byte_start=span[0],
                source_byte_end=span[1],
                source_content_sha256=hashlib.sha256(source[span[0] : span[1]]).hexdigest(),
                candidate_byte_start=0,
                candidate_byte_end=0,
                candidate_content_sha256=empty_hash,
                fact_ids=edit.fact_ids,
                configured_standard_ids=edit.configured_standard_ids,
                operation_id="readme.verified-template.compile",
            )
        )
    return sorted(corrections, key=lambda item: item.source_byte_start)


def validate_compiled_source_shell(candidate: str) -> None:
    """Fail closed if source reconciliation duplicates the compiled document shell."""

    headings = parse_headings(candidate)
    h1_count = sum(heading.level == 1 for heading in headings)
    h2_identities = [heading_identity(heading.title) for heading in headings if heading.level == 2]
    duplicate_h2s = sorted(
        identity for identity, count in Counter(h2_identities).items() if count > 1
    )
    first_h2 = min(
        (heading.start for heading in headings if heading.level == 2),
        default=len(candidate),
    )
    badge_rows = [
        line
        for line in candidate[:first_h2].splitlines()
        if _BADGE.search(line) and "products.aspose.org/media/" not in line
    ]
    if (
        h1_count != 1
        or duplicate_h2s
        or h2_identities.count("navigation") != 1
        or h2_identities.count("at-a-glance") != 1
        or len(badge_rows) != 1
        or len(_MERMAID.findall(candidate)) != 1
    ):
        raise ValueError(
            "source-preserving composition introduced an invalid document shell: "
            f"h1_count={h1_count}, duplicate_h2s={duplicate_h2s}, "
            f"navigation_count={h2_identities.count('navigation')}, "
            f"at_a_glance_count={h2_identities.count('at-a-glance')}, "
            f"badge_rows={len(badge_rows)}, mermaid_count={len(_MERMAID.findall(candidate))}"
        )
