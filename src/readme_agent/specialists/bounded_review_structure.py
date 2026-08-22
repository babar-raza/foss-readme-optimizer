"""Markdown block parsing for bounded README review packets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from readme_agent.readme.document_structure import heading_identity
from readme_agent.specialists.bounded_review_contracts import UnitKind

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
_FENCE_OPEN_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[ \t]*\S*[ \t]*$")
_TABLE_ROW_RE = re.compile(r"^[ \t]*\|.*\|[ \t]*$")
_TABLE_DELIM_CELL_RE = re.compile(r"^:?-+:?$")
_LIST_MARKER_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]+|\d+[.)][ \t]+)")


@dataclass
class _MutableUnit:
    kind: UnitKind
    char_start: int
    char_end: int
    line_start: int
    line_end: int
    section_path: str
    claim_ids: list[str] = field(default_factory=list)
    provenance_ids: list[str] = field(default_factory=list)
    unit_id: str = ""


def _line_records(text: str) -> list[tuple[int, int, str]]:
    records: list[tuple[int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        records.append((offset, offset + len(line), line.rstrip("\r\n")))
        offset += len(line)
    return records


def _fence_open(line: str) -> tuple[str, int] | None:
    match = _FENCE_OPEN_RE.match(line)
    if match is None:
        return None
    run = match.group(1)
    return run[0], len(run)


def _fence_close(line: str, char: str, min_len: int) -> bool:
    stripped = line.strip()
    return len(stripped) >= min_len and bool(stripped) and set(stripped) == {char}


def _is_table_delimiter_row(line: str) -> bool:
    if not _TABLE_ROW_RE.match(line):
        return False
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(_TABLE_DELIM_CELL_RE.match(cell) for cell in cells)


def _build_raw_units(text: str) -> list[_MutableUnit]:
    """Walk lines once, tracking cumulative char offsets and a heading-chain stack."""

    records = _line_records(text)
    n = len(records)
    units: list[_MutableUnit] = []
    stack: list[tuple[int, str]] = []

    def section_path_now() -> str:
        return "/".join(slug for _, slug in stack) if stack else "front-matter"

    i = 0
    while i < n:
        start, end, stripped = records[i]
        if not stripped.strip():
            i += 1
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match is not None:
            level = len(heading_match.group(1))
            title = re.sub(r"[ \t]+#+[ \t]*$", "", heading_match.group(2).strip()).strip()
            if level == 1:
                unit_section_path = "front-matter"
            else:
                slug = heading_identity(title)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, slug))
                unit_section_path = section_path_now()
            units.append(
                _MutableUnit(
                    kind="heading",
                    char_start=start,
                    char_end=end,
                    line_start=i + 1,
                    line_end=i + 1,
                    section_path=unit_section_path,
                )
            )
            i += 1
            continue

        fence_info = _fence_open(stripped)
        if fence_info is not None:
            char, min_len = fence_info
            j = i + 1
            close_index = None
            while j < n:
                if _fence_close(records[j][2], char, min_len):
                    close_index = j
                    break
                j += 1
            end_index = close_index if close_index is not None else n - 1
            units.append(
                _MutableUnit(
                    kind="fence",
                    char_start=start,
                    char_end=records[end_index][1],
                    line_start=i + 1,
                    line_end=end_index + 1,
                    section_path=section_path_now(),
                )
            )
            i = end_index + 1
            continue

        table_starts_here = (
            _TABLE_ROW_RE.match(stripped)
            and i + 1 < n
            and _is_table_delimiter_row(records[i + 1][2])
        )
        if table_starts_here:
            j = i + 1
            while j < n and records[j][2].strip() and _TABLE_ROW_RE.match(records[j][2]):
                j += 1
            end_index = j - 1
            units.append(
                _MutableUnit(
                    kind="table",
                    char_start=start,
                    char_end=records[end_index][1],
                    line_start=i + 1,
                    line_end=end_index + 1,
                    section_path=section_path_now(),
                )
            )
            i = end_index + 1
            continue

        # Paragraph or list: the remaining contiguous non-blank line run.
        j = i
        is_list = False
        while j < n and records[j][2].strip():
            candidate = records[j][2]
            if _HEADING_RE.match(candidate) or _fence_open(candidate) is not None:
                break
            if _LIST_MARKER_RE.match(candidate):
                is_list = True
            j += 1
        end_index = j - 1
        units.append(
            _MutableUnit(
                kind="list" if is_list else "paragraph",
                char_start=start,
                char_end=records[end_index][1],
                line_start=i + 1,
                line_end=end_index + 1,
                section_path=section_path_now(),
            )
        )
        i = end_index + 1

    return units
