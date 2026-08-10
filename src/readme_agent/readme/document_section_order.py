"""Enforce the accepted H2 journey as one exact post-composition section move."""

from __future__ import annotations

from readme_agent.presentation.template_schema import load_repository_presentation_template
from readme_agent.readme.document_operations import apply_document_operations, build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_structure import normalize_navigation_targets, parse_headings


def _normalize_public_spacing(markdown: str) -> str:
    """Collapse repeated public blank separators while preserving fenced-code bytes."""

    rendered: list[str] = []
    fenced = False
    previous_public_blank = False
    for raw in markdown.splitlines(keepends=True):
        content = raw.rstrip("\r\n")
        fence_boundary = content.lstrip().startswith("```")
        if fence_boundary:
            rendered.append(raw)
            fenced = not fenced
            previous_public_blank = False
            continue
        if fenced:
            rendered.append(raw)
            continue
        blank = not content.strip()
        if blank and previous_public_blank:
            continue
        rendered.append(raw)
        previous_public_blank = blank
    return "".join(rendered)


def _ordered_candidate(markdown: str) -> str:
    contract = load_repository_presentation_template()
    rank_by_heading = {
        contract.headings[slot].strip().casefold(): rank
        for rank, slot in enumerate(contract.section_order)
    }
    headings = [heading for heading in parse_headings(markdown) if heading.level == 2]
    recognized = [
        (index, rank_by_heading[heading.title.strip().casefold()])
        for index, heading in enumerate(headings)
        if heading.title.strip().casefold() in rank_by_heading
    ]
    ranks = [rank for _, rank in recognized]
    if len(ranks) != len(set(ranks)):
        raise ValueError("README candidate contains duplicate canonical H2 sections")
    ordered = markdown
    if ranks != sorted(ranks):
        blocks = [markdown[heading.start : heading.section_end] for heading in headings]
        recognized_indexes = [index for index, _ in recognized]
        ordered_blocks = [
            blocks[index] for index, _ in sorted(recognized, key=lambda item: item[1])
        ]
        for index, block in zip(recognized_indexes, ordered_blocks, strict=True):
            blocks[index] = block

        opening_end = headings[0].start if headings else len(markdown)
        ordered = markdown[:opening_end] + "".join(blocks)
        ordered = normalize_navigation_targets(ordered)
    return _normalize_public_spacing(ordered)


def _changed_character_span(before: str, after: str) -> tuple[int, int, int]:
    prefix = 0
    shared = min(len(before), len(after))
    while prefix < shared and before[prefix] == after[prefix]:
        prefix += 1

    suffix = 0
    before_remaining = len(before) - prefix
    after_remaining = len(after) - prefix
    while (
        suffix < before_remaining
        and suffix < after_remaining
        and before[len(before) - suffix - 1] == after[len(after) - suffix - 1]
    ):
        suffix += 1
    return prefix, len(before) - suffix, len(after) - suffix


def enforce_canonical_section_order(
    source: bytes,
    operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Move complete H2 blocks without rewriting their content or unknown sections."""

    preliminary_bytes = apply_document_operations(source, operations)
    preliminary = preliminary_bytes.decode("utf-8")
    ordered = _ordered_candidate(preliminary)
    if ordered == preliminary:
        return operations

    before_start, before_end, after_end = _changed_character_span(preliminary, ordered)
    start = len(preliminary[:before_start].encode("utf-8"))
    end = len(preliminary[:before_end].encode("utf-8"))
    replacement = ordered[before_start:after_end]
    move = build_operation(
        operation_id="readme.presentation.canonical-section-order",
        operation="move_exact",
        source=preliminary_bytes,
        start=start,
        end=end,
        replacement=replacement,
        fact_ids=[],
        treatment="preserve",
        rationale=(
            "Move complete applicable H2 blocks into the accepted portfolio journey, "
            "synchronize Navigation, and collapse repeated public blank separators without "
            "rewriting section content, unknown sections, or fenced-code bytes."
        ),
        coordinate_space="candidate_utf8",
    )
    return [*operations, move]
