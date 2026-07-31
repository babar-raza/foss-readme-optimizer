"""Translate grounded reviewer findings into loss-bounded source operations."""

from __future__ import annotations

import re

from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import Heading

_CAPABILITY_HEADINGS = {
    "capabilities",
    "currently available features",
    "features",
    "key capabilities",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _overlaps(
    start: int,
    end: int,
    operations: list[ReadmeDocumentOperationV1],
) -> bool:
    return any(
        operation.source_byte_start < end and start < operation.source_byte_end
        for operation in operations
    )


def _source_heading(
    context: DocumentRenderContext,
    title: str,
    quoted_span: str,
) -> Heading | None:
    expected = title.strip().casefold()
    exact_matches = [
        heading
        for heading in context.headings
        if heading.level == 2
        and heading.title.strip().casefold() == expected
        and quoted_span in _body(context, heading)
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if expected not in _CAPABILITY_HEADINGS:
        return None
    canonical_matches = [
        heading
        for heading in context.headings
        if heading.level == 2
        and heading.title.strip().casefold() in _CAPABILITY_HEADINGS
        and quoted_span in _body(context, heading)
    ]
    return canonical_matches[0] if len(canonical_matches) == 1 else None


def _body(context: DocumentRenderContext, heading: Heading) -> str:
    return context.inner_text[heading.heading_end : heading.section_end]


def _details(title: str, body: str) -> str:
    return f"\n\n<details>\n<summary>{title.strip()}</summary>\n\n{body.strip()}\n\n</details>"


def build_review_repair_operations(
    context: DocumentRenderContext,
    plan: ReadmeAgenticCompositionPlanV1 | None,
    existing_operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Consolidate exact source sections only after a grounded duplication finding."""

    request = plan.review_repair if plan is not None else None
    if request is None:
        return []
    findings = [
        finding for finding in request.findings if _slug(finding.criterion) == "visible-duplication"
    ]
    targets: list[tuple[Heading, str]] = []
    for finding in findings:
        heading = _source_heading(context, finding.section, finding.quoted_candidate_span)
        if heading is None:
            continue
        targets.append((heading, finding.finding_id))
    unique = {heading.start: (heading, finding_id) for heading, finding_id in targets}
    targets = [unique[start] for start in sorted(unique)]
    if len(targets) < 2:
        return []

    keeper, _ = next(
        (
            item
            for item in reversed(targets)
            if item[0].title.strip().casefold() in _CAPABILITY_HEADINGS
        ),
        targets[-1],
    )
    removed = [heading for heading, _ in targets if heading.start != keeper.start]
    keeper_start = context.byte_offset(keeper.heading_end)
    keeper_end = context.byte_offset(keeper.section_end)
    removal_spans = [
        (context.byte_offset(heading.start), context.byte_offset(heading.section_end))
        for heading in removed
    ]
    if _overlaps(keeper_start, keeper_end, existing_operations) or any(
        _overlaps(start, end, existing_operations) for start, end in removal_spans
    ):
        return []

    keeper_body = _body(context, keeper).rstrip()
    replacement = (
        keeper_body
        + "".join(_details(heading.title, _body(context, heading)) for heading in removed)
        + "\n\n"
    )
    operations = [
        build_operation(
            operation_id=f"readme.review.consolidate-duplication:{keeper_start}",
            operation="replace",
            source=context.source,
            start=keeper_start,
            end=keeper_end,
            replacement=replacement,
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Consolidate independently identified visible duplication while retaining every "
                "maintainer-authored detail in one disclosure-owned capability section."
            ),
        )
    ]
    for heading, (start, end) in zip(removed, removal_spans, strict=True):
        operations.append(
            build_operation(
                operation_id=f"readme.review.remove-consolidated:{start}",
                operation="remove",
                source=context.source,
                start=start,
                end=end,
                replacement="",
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    f"Move the exact {heading.title!r} details into the retained capability "
                    "section so the same information is not shown twice."
                ),
            )
        )
    return operations
