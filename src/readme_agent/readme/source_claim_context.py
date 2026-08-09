"""Resolve heading and list ancestry for immutable README source claims."""

from __future__ import annotations

import re

from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1

_HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
_LIST_ITEM = re.compile(r"(?s)^(?P<indent>[ \t]*)[-+*]\s+(?P<body>.+?)\s*$")


def heading_ancestry(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
) -> tuple[str, ...]:
    """Return the active heading stack at one immutable claim."""

    character_start = len(document.encode("utf-8")[: claim.source_byte_start].decode("utf-8"))
    headings: dict[int, str] = {}
    for line in document[:character_start].splitlines():
        match = _HEADING.fullmatch(line)
        if match is None:
            continue
        level = len(match.group("level"))
        headings = {key: value for key, value in headings.items() if key < level}
        headings[level] = match.group("title")
    return tuple(headings[key] for key in sorted(headings))


def list_ancestor_bodies(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
) -> tuple[str, ...]:
    """Return enclosing list-item bodies from outermost to innermost."""

    character_start = len(document.encode("utf-8")[: claim.source_byte_start].decode("utf-8"))
    line_start = document.rfind("\n", 0, character_start) + 1
    current = document[line_start : document.find("\n", line_start)]
    next_indent = len(current) - len(current.lstrip())
    ancestors: list[str] = []
    for line in reversed(document[:line_start].splitlines()):
        match = _LIST_ITEM.fullmatch(line)
        if match is None or len(match.group("indent")) >= next_indent:
            continue
        ancestors.append(match.group("body"))
        next_indent = len(match.group("indent"))
        if next_indent == 0:
            break
    return tuple(reversed(ancestors))


def descendant_list_text(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
) -> str:
    """Return the exact descendant list bodies owned by one list item."""

    document_bytes = document.encode("utf-8")
    character_start = len(document_bytes[: claim.source_byte_start].decode("utf-8"))
    character_end = len(document_bytes[: claim.source_byte_end].decode("utf-8"))
    line_start = document.rfind("\n", 0, character_start) + 1
    current_line = document[line_start : document.find("\n", line_start)]
    current = _LIST_ITEM.fullmatch(current_line)
    if current is None:
        return ""
    current_indent = len(current.group("indent"))
    descendants = []
    for line in document[character_end:].splitlines():
        item = _LIST_ITEM.fullmatch(line)
        if item is None:
            if line.strip():
                break
            continue
        indent = len(item.group("indent"))
        if indent <= current_indent:
            break
        descendants.append(item.group("body"))
    return " ".join(descendants)


__all__ = ["descendant_list_text", "heading_ancestry", "list_ancestor_bodies"]
