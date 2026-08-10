"""Define and verify the adaptive Mermaid block-grid capability layout."""

from __future__ import annotations

import re
from typing import TypeVar

from readme_agent.readme.header_visual_models import MermaidNodeV1

CAPABILITY_COLUMN_THRESHOLD = 5
_T = TypeVar("_T")
_CAPABILITY_NODE = re.compile(r'^\s+C\d+\["[^"]+"\](?::2)?(?:\s|$)')


def split_capability_columns(items: list[_T]) -> tuple[tuple[_T, ...], ...]:
    """Return one vertical column through five items, otherwise two balanced columns."""

    if not items:
        return (tuple(items),)
    if len(items) <= CAPABILITY_COLUMN_THRESHOLD:
        return (tuple(items),)
    split = (len(items) + 1) // 2
    return (tuple(items[:split]), tuple(items[split:]))


def capability_grid_rows(items: list[_T]) -> tuple[tuple[_T | None, ...], ...]:
    """Return stable rows for one full-width column or two consecutive columns."""

    columns = split_capability_columns(items)
    if len(columns) == 1:
        return tuple((item,) for item in columns[0])
    left, right = columns
    return tuple(
        (left[index], right[index] if index < len(right) else None) for index in range(len(left))
    )


def _render_node(node: MermaidNodeV1, *, span_two: bool = False) -> str:
    suffix = ":2" if span_two else ""
    return f'{node.node_id}["{node.label}"]{suffix}'


def render_capability_group(nodes: list[MermaidNodeV1]) -> list[str]:
    """Render one compact Core block with a visible central relationship anchor."""

    rows = capability_grid_rows(nodes)
    columns = split_capability_columns(nodes)
    anchor_at = (len(rows) + 1) // 2
    lines = ["  block:Capabilities:2", "    columns 2"]
    for index, row in enumerate(rows):
        if index == anchor_at:
            lines.append('    CH["Core Capabilities"]:2')
        left_node = row[0]
        if left_node is None:
            raise ValueError("capability grid cannot start a row with an empty cell")
        if len(columns) == 1:
            lines.append("    " + _render_node(left_node, span_two=True))
        else:
            left = _render_node(left_node)
            right = _render_node(row[1]) if row[1] is not None else "space"
            lines.append(f"    {left} {right}")
    if anchor_at == len(rows):
        lines.append('    CH["Core Capabilities"]:2')
    lines.append("  end")
    return lines


def validate_capability_group_layout(source: str, node_ids: list[str]) -> bool:
    """Require the exact block-grid layout for the supplied capability IDs."""

    # Callers that recover IDs from block-grid source observe row-major order
    # (C1, C5, C2, C6, ...), while the renderer assigns IDs in semantic list
    # order. Reconstruct from the stable numeric identity, never parse order.
    node_ids = sorted(node_ids, key=lambda node_id: int(node_id[1:]))
    expected_nodes = [
        MermaidNodeV1(
            node_id=node_id,
            role="capability",
            label="x",
            fact_ids=["layout:validation"],
        )
        for node_id in node_ids
    ]
    expected = [_structure_skeleton(line) for line in render_capability_group(expected_nodes)]
    block = _capability_block(source.splitlines())
    if block is None:
        return False
    actual = [_structure_skeleton(line) for line in block]
    return actual == expected


def _capability_block(lines: list[str]) -> list[str] | None:
    try:
        start = lines.index("  block:Capabilities:2")
    except ValueError:
        return None
    for index in range(start + 1, len(lines)):
        if lines[index] == "  end":
            return lines[start : index + 1]
    return None


def _structure_skeleton(line: str) -> str:
    if _CAPABILITY_NODE.match(line):
        return re.sub(r'\["[^"]+"\]', "[]", line)
    return line
