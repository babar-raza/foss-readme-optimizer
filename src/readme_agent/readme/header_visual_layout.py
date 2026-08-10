"""Define and verify the adaptive Mermaid flowchart capability layout."""

from __future__ import annotations

import re
from itertools import pairwise
from typing import TypeVar

from readme_agent.readme.header_visual_models import MermaidNodeV1

CAPABILITY_COLUMN_THRESHOLD = 5
_T = TypeVar("_T")
_CAPABILITY_NODE = re.compile(r'^\s+C\d+\["[^"]+"\]$')


def split_capability_columns(items: list[_T]) -> tuple[tuple[_T, ...], ...]:
    """Return one vertical column through five items, otherwise two balanced columns."""

    if not items:
        return (tuple(items),)
    if len(items) <= CAPABILITY_COLUMN_THRESHOLD:
        return (tuple(items),)
    split = (len(items) + 1) // 2
    return (tuple(items[:split]), tuple(items[split:]))


def _render_node(node: MermaidNodeV1, label: str) -> str:
    return f'{node.node_id}["{label}"]'


def _render_column(
    nodes: tuple[MermaidNodeV1, ...], labels: dict[str, str], indent: str
) -> list[str]:
    lines = [f"{indent}{_render_node(node, labels[node.node_id])}" for node in nodes]
    lines.extend(f"{indent}{left.node_id} ~~~ {right.node_id}" for left, right in pairwise(nodes))
    return lines


def render_capability_group(
    nodes: list[MermaidNodeV1],
    labels: dict[str, str] | None = None,
) -> list[str]:
    """Render Core Capabilities as one vertical column or two balanced vertical columns."""

    labels = labels or {node.node_id: node.label for node in nodes}
    columns = split_capability_columns(nodes)
    lines = ['  subgraph CORE["Core Capabilities"]']
    if len(columns) == 1:
        lines.append("    direction TB")
        lines.extend(_render_column(columns[0], labels, "    "))
    else:
        lines.extend(("    direction LR", '    subgraph CORE_LEFT[" "]', "      direction TB"))
        lines.extend(_render_column(columns[0], labels, "      "))
        lines.extend(("    end", '    subgraph CORE_RIGHT[" "]', "      direction TB"))
        lines.extend(_render_column(columns[1], labels, "      "))
        lines.extend(("    end", "    CORE_LEFT ~~~ CORE_RIGHT"))
    lines.append("  end")
    return lines


def validate_capability_group_layout(source: str, node_ids: list[str]) -> bool:
    """Require the exact adaptive flowchart structure for the supplied capability IDs."""

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
    return block is not None and [_structure_skeleton(line) for line in block] == expected


def _capability_block(lines: list[str]) -> list[str] | None:
    try:
        start = lines.index('  subgraph CORE["Core Capabilities"]')
    except ValueError:
        return None
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
    if _CAPABILITY_NODE.match(line):
        return re.sub(r'\["[^"]+"\]', "[]", line)
    return line
