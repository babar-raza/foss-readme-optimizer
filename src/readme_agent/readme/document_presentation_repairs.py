"""Plan bounded deterministic repairs for known visitor-facing presentation defects."""

from __future__ import annotations

import re

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import (
    ReadmeDocumentOperationV1,
)
from readme_agent.readme.document_render_context import DocumentRenderContext

_VAGUE_FUTURE_BULLET = re.compile(
    r"(?im)^[ \t]*[-*+][ \t]+more[^\r\n]*coming soon(?:[.!…]+)?[ \t]*(?:\r?\n|$)"
)
_RAW_OPTION_BULLET = re.compile(
    r"(?m)^(?P<prefix>[ \t]*[-*+][ \t]+)"
    r"`(?P<token>[a-z][a-z0-9_]*_[a-z0-9_]+)`"
    r"[ \t]+[-–—:][ \t]+(?P<description>[^\r\n]+)(?P<newline>\r?\n|$)"
)
_COMMERCIAL_HEADING = re.compile(r"(?i)(?:enterprise edition|aspose\.com)")
_COMMERCIAL_CTA = re.compile(r"(?i)\b(?:buy|free trial|download|upgrade now)\b")
_MOJIBAKE_REPLACEMENTS = {
    "鈥?": "—",
}


def _overlaps(
    start: int,
    end: int,
    operations: list[ReadmeDocumentOperationV1],
) -> bool:
    return any(
        operation.source_byte_start < end and start < operation.source_byte_end
        for operation in operations
    )


def _friendly_option_name(token: str) -> str:
    return token.replace("_", " ").strip().capitalize()


def build_presentation_policy_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Repair only exact, source-local defects with lossless or policy-owned transforms."""

    operations: list[ReadmeDocumentOperationV1] = []
    occupied = [*existing_operations]

    for heading in context.headings:
        if heading.level != 3 or not _COMMERCIAL_HEADING.search(heading.title):
            continue
        section = context.inner_text[heading.start : heading.section_end]
        if not _COMMERCIAL_CTA.search(section):
            continue
        start = context.byte_offset(heading.start)
        end = context.byte_offset(heading.section_end)
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.remove-commercial-directory:{start}",
            operation="remove",
            source=context.source,
            start=start,
            end=end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Remove a standalone commercial call-to-action directory; verified Enterprise "
                "Edition context remains eligible only where it naturally supports reader prose."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    for match in _VAGUE_FUTURE_BULLET.finditer(context.inner_text):
        start = context.byte_offset(match.start())
        end = context.byte_offset(match.end())
        if _overlaps(start, end, occupied):
            continue
        operation = build_operation(
            operation_id=f"readme.presentation.remove-vague-future:{start}",
            operation="remove",
            source=context.source,
            start=start,
            end=end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Remove an unbounded future-format placeholder that has no verified release scope."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    for match in _RAW_OPTION_BULLET.finditer(context.inner_text):
        start = context.byte_offset(match.start())
        end = context.byte_offset(match.end())
        if _overlaps(start, end, occupied):
            continue
        token = match.group("token")
        replacement = (
            f"{match.group('prefix')}**{_friendly_option_name(token)}** "
            f"(`{token}`) — {match.group('description')}{match.group('newline')}"
        )
        operation = build_operation(
            operation_id=f"readme.presentation.explain-option:{start}",
            operation="replace",
            source=context.source,
            start=start,
            end=end,
            replacement=replacement,
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Retain the exact maintainer-authored option and description while adding a "
                "visitor-readable task label."
            ),
        )
        operations.append(operation)
        occupied.append(operation)

    for broken, corrected in _MOJIBAKE_REPLACEMENTS.items():
        cursor = 0
        while (position := context.inner_text.find(broken, cursor)) >= 0:
            start = context.byte_offset(position)
            end = context.byte_offset(position + len(broken))
            cursor = position + len(broken)
            if _overlaps(start, end, occupied):
                continue
            operation = build_operation(
                operation_id=f"readme.presentation.repair-encoding:{start}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=corrected,
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    "Replace a known broken punctuation sequence with its unambiguous UTF-8 "
                    "character without changing the surrounding maintainer-authored claim."
                ),
            )
            operations.append(operation)
            occupied.append(operation)

    return operations
