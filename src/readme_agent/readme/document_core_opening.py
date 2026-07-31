"""Plan independently ordered core README opening sections."""

from __future__ import annotations

from dataclasses import replace

from readme_agent.readme.agentic_composition_models import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.document_acquisition import build_missing_installation_operations
from readme_agent.readme.document_examples import build_missing_quick_start_operations
from readme_agent.readme.document_opening import build_opening_operations
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations


def build_core_opening_operations(
    context: DocumentRenderContext,
    agentic_plan: ReadmeAgenticCompositionPlanV1 | None,
    header_visuals: ReadmeHeaderVisualV1,
    *,
    exclusion_spans: list[tuple[int, int]],
) -> list[ReadmeDocumentOperationV1]:
    """Plan overview, Installation, and Quick start as separately ordered operations."""

    opening_context = replace(
        context,
        headings=[
            replace(heading, title=strip_emoji_decorations(heading.title))
            for heading in context.headings
            if not any(
                start <= context.byte_offset(heading.start) < end for start, end in exclusion_spans
            )
        ],
    )
    first_h2 = next((heading for heading in context.headings if heading.level == 2), None)
    insertion = context.byte_offset(first_h2.start) if first_h2 is not None else len(context.source)
    operations = build_opening_operations(
        opening_context,
        agentic_plan,
        header_visuals,
        insertion_byte_offset=insertion,
    )
    operations.extend(
        build_missing_installation_operations(
            context,
            fallback_insertion=insertion,
        )
    )
    operations.extend(
        build_missing_quick_start_operations(
            context,
            fallback_insertion=insertion,
        )
    )
    return operations
