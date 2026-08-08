"""Define and verify the adaptive Mermaid capability-column layout."""

from __future__ import annotations

import re
from itertools import pairwise
from typing import TypeVar

from readme_agent.readme.header_visual_models import MermaidNodeV1

CAPABILITY_COLUMN_THRESHOLD = 5
_T = TypeVar("_T")
_NODE_LINE = re.compile(r'^\s+(C\d+)\["[^"]+"\]$')


def split_capability_columns(items: list[_T]) -> tuple[tuple[_T, ...], ...]:
    """Return one short column or two balanced columns in reading order."""

    if len(items) <= CAPABILITY_COLUMN_THRESHOLD:
        return (tuple(items),)
    first_column_size = (len(items) + 1) // 2
    return (tuple(items[:first_column_size]), tuple(items[first_column_size:]))


def capability_layout_edges(node_ids: list[str]) -> list[tuple[str, str]]:
    """Return only the invisible consecutive edges needed within each column."""

    columns = split_capability_columns(node_ids)
    return [edge for column in columns for edge in pairwise(column)]


def render_capability_group(nodes: list[MermaidNodeV1]) -> list[str]:
    """Render one visible Core box with one or two vertical feature columns."""

    columns = split_capability_columns(nodes)
    lines = ['  subgraph Capabilities["Core Capabilities"]']
    if len(columns) == 1:
        lines.append("    direction TB")
        lines.extend(f'    {node.node_id}["{node.label}"]' for node in columns[0])
        lines.extend(
            f"    {current.node_id} ~~~ {following.node_id}"
            for current, following in pairwise(columns[0])
        )
    else:
        lines.append("    direction LR")
        for index, column in enumerate(columns, start=1):
            lines.append(f'    subgraph CapabilityColumn{index}[" "]')
            lines.append("      direction TB")
            lines.extend(f'      {node.node_id}["{node.label}"]' for node in column)
            lines.extend(
                f"      {current.node_id} ~~~ {following.node_id}"
                for current, following in pairwise(column)
            )
            lines.append("    end")
    lines.append("  end")
    if len(columns) == 2:
        lines.extend(
            (
                "  style CapabilityColumn1 fill:none,stroke:none",
                "  style CapabilityColumn2 fill:none,stroke:none",
            )
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
    expected = _expected_structure(node_ids)
    actual = [_structure_token(line) for line in block]
    expected_styles = (
        {
            "  style CapabilityColumn1 fill:none,stroke:none",
            "  style CapabilityColumn2 fill:none,stroke:none",
        }
        if len(node_ids) > CAPABILITY_COLUMN_THRESHOLD
        else set()
    )
    actual_styles = {line for line in lines if line.lstrip().startswith("style CapabilityColumn")}
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


def _structure_token(line: str) -> str:
    match = _NODE_LINE.fullmatch(line)
    if match is None:
        return line
    return f"{' ' * (len(line) - len(line.lstrip()))}NODE:{match.group(1)}"


def _expected_structure(node_ids: list[str]) -> list[str]:
    columns = split_capability_columns(node_ids)
    lines = ['  subgraph Capabilities["Core Capabilities"]']
    if len(columns) == 1:
        lines.append("    direction TB")
        lines.extend(f"    NODE:{node_id}" for node_id in columns[0])
        lines.extend(f"    {left} ~~~ {right}" for left, right in pairwise(columns[0]))
    else:
        lines.append("    direction LR")
        for index, column in enumerate(columns, start=1):
            lines.append(f'    subgraph CapabilityColumn{index}[" "]')
            lines.append("      direction TB")
            lines.extend(f"      NODE:{node_id}" for node_id in column)
            lines.extend(f"      {left} ~~~ {right}" for left, right in pairwise(column))
            lines.append("    end")
    lines.append("  end")
    return lines
