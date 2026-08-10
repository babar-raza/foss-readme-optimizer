"""Define and verify the adaptive Mermaid capability-column layout."""

from __future__ import annotations

import re
from itertools import pairwise
from typing import TypeVar

from readme_agent.readme.header_visual_models import MermaidNodeV1

CAPABILITY_COLUMN_THRESHOLD = 5
_T = TypeVar("_T")
_LABELED_NODE = re.compile(r'\["[^"]*"\]')


def split_capability_columns(items: list[_T]) -> tuple[tuple[_T, ...], ...]:
    """Return one compact vertical column through five items, otherwise two balanced columns."""

    if not items:
        return (tuple(items),)
    if len(items) <= CAPABILITY_COLUMN_THRESHOLD:
        return (tuple(items),)
    split = (len(items) + 1) // 2
    return (tuple(items[:split]), tuple(items[split:]))


def capability_layout_edges(node_ids: list[str]) -> list[tuple[str, str]]:
    """Return only the invisible consecutive edges needed within each column."""

    columns = split_capability_columns(node_ids)
    return [edge for column in columns for edge in pairwise(column)]


def _column_lines(nodes: tuple[MermaidNodeV1, ...], indent: str) -> list[str]:
    lines = [f'{indent}{node.node_id}["{node.label}"]' for node in nodes]
    lines.extend(f"{indent}{left.node_id} ~~~ {right.node_id}" for left, right in pairwise(nodes))
    return lines


def render_capability_group(nodes: list[MermaidNodeV1]) -> list[str]:
    """Render one visible Core box with short single-line-chained feature columns."""

    columns = split_capability_columns(nodes)
    lines = ['  subgraph Capabilities["Core Capabilities"]']
    if len(columns) == 1:
        lines.append("    direction TB")
        lines.extend(_column_lines(columns[0], "    "))
    else:
        lines.append("    direction LR")
        for index, column in enumerate(columns, start=1):
            lines.append(f'    subgraph Col{index}[" "]')
            lines.extend(_column_lines(column, "      "))
            lines.append("    end")
    lines.append("  end")
    if len(columns) > 1:
        lines.extend(
            f"  style Col{index} fill:none,stroke:none" for index in range(1, len(columns) + 1)
        )
    return lines


def validate_capability_group_layout(source: str, node_ids: list[str]) -> bool:
    """Require the exact adaptive layout structure for the supplied capability IDs."""

    lines = source.splitlines()
    try:
        start = lines.index('  subgraph Capabilities["Core Capabilities"]')
    except ValueError:
        return False
    block = _capability_block(lines, start)
    if block is None:
        return False
    expected = [_structure_skeleton(line) for line in _expected_structure(node_ids)]
    actual = [_structure_skeleton(line) for line in block]
    columns = split_capability_columns(node_ids)
    expected_styles = (
        {f"  style Col{index} fill:none,stroke:none" for index in range(1, len(columns) + 1)}
        if len(columns) > 1
        else set()
    )
    actual_styles = {line for line in lines if line.lstrip().startswith("style Col")}
    return actual == expected and actual_styles == expected_styles


def _capability_block(lines: list[str], start: int) -> list[str] | None:
    depth = 0
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("subgraph "):
            depth += 1
        elif stripped == "end":
            depth -= 1
            if depth == 0:
                return lines[start : index + 1]
    return None


def _structure_skeleton(line: str) -> str:
    return _LABELED_NODE.sub("[]", line)


def _expected_structure(node_ids: list[str]) -> list[str]:
    columns = split_capability_columns(node_ids)
    lines = ['  subgraph Capabilities["Core Capabilities"]']
    if len(columns) == 1:
        lines.append("    direction TB")
        lines.extend(f'    {node_id}["x"]' for node_id in columns[0])
        lines.extend(f"    {left} ~~~ {right}" for left, right in pairwise(columns[0]))
    else:
        lines.append("    direction LR")
        for index, column in enumerate(columns, start=1):
            lines.append(f'    subgraph Col{index}[" "]')
            lines.extend(f'      {node_id}["x"]' for node_id in column)
            lines.extend(f"      {left} ~~~ {right}" for left, right in pairwise(column))
            lines.append("    end")
    lines.append("  end")
    return lines
