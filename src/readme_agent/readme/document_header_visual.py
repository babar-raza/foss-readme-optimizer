"""Plan marker removal, factual badge headers, and Mermaid overview operations."""

from __future__ import annotations

import re
from typing import cast

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import (
    DocumentOperation,
    ProtectedContentTreatment,
    ReadmeDocumentOperationV1,
)
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1

_HTML_COMMENT = re.compile(r"<!--.*?-->\s*", re.DOTALL)
_BADGE_LINE = re.compile(
    r"(?im)^(?![ \t]*<!--)[^\n]*(?:!\[[^\]]*\]\([^)]*(?:shields\.io|badge|actions/workflows)[^)]*\)"
    r"[^\n]*)\n?"
)
_MERMAID_FENCE = re.compile(r"(?ms)^```mermaid[ \t]*\n.*?^```[ \t]*\n?")


def build_comment_removal_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Remove visitor-visible HTML comments while preserving curated source examples."""

    operations: list[ReadmeDocumentOperationV1] = []
    for index, match in enumerate(_HTML_COMMENT.finditer(context.inner_text), start=1):
        start = context.byte_offset(match.start())
        end = context.byte_offset(match.end())
        operations.append(
            build_operation(
                operation_id=f"readme.comments.remove-html:{index}",
                operation="remove",
                source=context.source,
                start=start,
                end=end,
                replacement="",
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    "Keep ownership, hashes, and automation provenance in durable evidence "
                    "instead of visitor-facing README comments."
                ),
            )
        )
    return operations


def _header_badge_matches(context: DocumentRenderContext) -> list[re.Match[str]]:
    h1 = next((heading for heading in context.headings if heading.level == 1), None)
    if h1 is None:
        return []
    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    end = first_h2.start if first_h2 is not None else len(context.inner_text)
    return list(_BADGE_LINE.finditer(context.inner_text, h1.heading_end, end))


def build_badge_header_operations(
    context: DocumentRenderContext,
    visual: ReadmeHeaderVisualV1,
) -> list[ReadmeDocumentOperationV1]:
    """Insert or replace the top badge row with the exact fact-backed row."""

    h1 = next((heading for heading in context.headings if heading.level == 1), None)
    title_line = f"# {visual.title}\n"
    if h1 is None:
        badge_block = f"\n{visual.badge_markdown}" if visual.badge_markdown else ""
        return [
            build_operation(
                operation_id="readme.header.add",
                operation="insert_before",
                source=context.source,
                start=0,
                end=0,
                replacement=f"{title_line}{badge_block}\n\n",
                fact_ids=visual.all_fact_ids,
                treatment="additive",
                rationale=(
                    "Add the exact factual product title and applicable accepted-fact badges."
                ),
            )
        ]

    operations: list[ReadmeDocumentOperationV1] = []
    if context.inner_text[h1.start : h1.heading_end] != title_line:
        operations.append(
            build_operation(
                operation_id="readme.header.title",
                operation="replace",
                source=context.source,
                start=context.byte_offset(h1.start),
                end=context.byte_offset(h1.heading_end),
                replacement=title_line,
                fact_ids=visual.title_fact_ids,
                treatment="authoritative_fact_correction",
                rationale="Use the selected accepted product identity as the visible README title.",
            )
        )

    matches = _header_badge_matches(context)
    if not matches:
        if not visual.badge_markdown:
            return operations
        operations.append(
            build_operation(
                operation_id="readme.header.badges",
                operation="insert_after",
                source=context.source,
                start=context.byte_offset(h1.heading_end),
                end=context.byte_offset(h1.heading_end),
                replacement=f"\n{visual.badge_markdown}\n",
                fact_ids=visual.badge_fact_ids,
                treatment="additive",
                rationale="Add only applicable package, version, download, and license badges.",
            )
        )
        return operations

    first = matches[0]
    if first.group(0).rstrip("\r\n") != visual.badge_markdown:
        operations.append(
            build_operation(
                operation_id="readme.header.badges",
                operation="replace",
                source=context.source,
                start=context.byte_offset(first.start()),
                end=context.byte_offset(first.end()),
                replacement=(visual.badge_markdown + "\n" if visual.badge_markdown else ""),
                fact_ids=visual.badge_fact_ids,
                treatment="authoritative_fact_correction",
                rationale="Replace unsupported or stale badges with the exact accepted-fact set.",
            )
        )
    for index, match in enumerate(matches[1:], start=2):
        operations.append(
            build_operation(
                operation_id=f"readme.header.badges.remove-extra:{index}",
                operation="remove",
                source=context.source,
                start=context.byte_offset(match.start()),
                end=context.byte_offset(match.end()),
                replacement="",
                fact_ids=visual.badge_fact_ids,
                treatment="authoritative_fact_correction",
                rationale="Remove opening badges outside the accepted-fact badge set.",
            )
        )
    return operations


def build_existing_overview_diagram_operations(
    context: DocumentRenderContext,
    visual: ReadmeHeaderVisualV1,
) -> list[ReadmeDocumentOperationV1]:
    """Add or replace Mermaid only when the source already has At a glance."""

    overview = context.h2("at a glance")
    if overview is None or visual.mermaid_markdown in context.inner_text:
        return []
    existing = _MERMAID_FENCE.search(
        context.inner_text,
        overview.heading_end,
        overview.section_end,
    )
    if existing is not None:
        start_character, end_character = existing.span()
        operation = "replace"
        treatment = "authoritative_fact_correction"
        replacement = visual.mermaid_markdown + "\n"
    else:
        start_character = end_character = overview.heading_end
        operation = "insert_after"
        treatment = "additive"
        replacement = "\n" + visual.mermaid_markdown + "\n"
    return [
        build_operation(
            operation_id="readme.at-a-glance.mermaid",
            operation=cast(DocumentOperation, operation),
            source=context.source,
            start=context.byte_offset(start_character),
            end=context.byte_offset(end_character),
            replacement=replacement,
            fact_ids=visual.diagram_fact_ids,
            treatment=cast(ProtectedContentTreatment, treatment),
            rationale=(
                "Show a bounded product-specific flowchart whose labels map only to selected "
                "accepted identity, problem, capability, and format facts."
            ),
        )
    ]
