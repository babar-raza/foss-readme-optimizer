"""Apply density rules from the repository-presentation contract at runtime."""

from __future__ import annotations

from readme_agent.presentation.template_compiler import select_density_profile
from readme_agent.presentation.template_schema import (
    TemplateSlot,
    load_repository_presentation_template,
)
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext


def _slot_for_heading(title: str) -> TemplateSlot | None:
    normalized = title.strip().casefold()
    if "example" in normalized and "quick" not in normalized:
        return "additional_examples"
    if "api" in normalized:
        return "api_reference"
    if any(token in normalized for token in ("development", "testing", "workflow")):
        return "development_and_testing"
    return None


def _overlaps(
    start: int,
    end: int,
    operations: list[ReadmeDocumentOperationV1],
) -> bool:
    return any(
        operation.source_byte_start < end and start < operation.source_byte_end
        for operation in operations
    )


def build_density_collapse_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Collapse long secondary detail while preserving its exact Markdown content."""

    contract = load_repository_presentation_template()
    profile = select_density_profile(
        len(context.inner_text.splitlines()),
        template=contract,
    )
    collapsed_slots = set(contract.profiles[profile].collapse_slots)
    operations: list[ReadmeDocumentOperationV1] = []
    for heading in context.headings:
        if heading.level != 2:
            continue
        slot = _slot_for_heading(heading.title)
        body = context.inner_text[heading.heading_end : heading.section_end]
        nonblank_lines = sum(bool(line.strip()) for line in body.splitlines())
        if slot not in collapsed_slots or nonblank_lines < 12 or "<details>" in body.casefold():
            continue
        start = context.byte_offset(heading.heading_end)
        end = context.byte_offset(heading.section_end)
        if _overlaps(start, end, [*existing_operations, *operations]):
            continue
        replacement = (
            "\n<details>\n"
            f"<summary>Show {heading.title.strip().casefold()}</summary>\n\n"
            f"{body.strip()}\n\n"
            "</details>\n\n"
        )
        operations.append(
            build_operation(
                operation_id=f"readme.density.collapse:{start}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=replacement,
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    "Keep the primary reader journey concise while preserving long secondary "
                    "examples, API detail, or development workflow on demand."
                ),
            )
        )
    return operations
