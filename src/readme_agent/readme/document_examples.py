"""Plan bounded README minimal-example operations."""

from __future__ import annotations

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import code_blocks_in_span
from readme_agent.readme.document_templates import accepted_fact, example_text


def build_example_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Insert or replace only the verified minimal example within a usage section."""

    example = accepted_fact(context.facts, "example.minimal")
    value = example.value if example is not None and isinstance(example.value, dict) else {}
    exact_code = str(value.get("code", "")).rstrip()
    target = context.h2("quick start", "usage")
    if not exact_code or exact_code in context.inner_text or target is None:
        return []
    existing_examples = code_blocks_in_span(
        context.inner_text,
        target.heading_end,
        target.section_end,
    )
    rendered = example_text(context.facts, context.base_revision)
    if len(existing_examples) == 1:
        existing = existing_examples[0]
        return [
            build_operation(
                operation_id="readme.example.replace-unverified-minimal",
                operation="replace",
                source=context.source,
                start=context.byte_offset(existing.start),
                end=context.byte_offset(existing.end),
                replacement=rendered + "\n",
                fact_ids=[example.fact_id] if example is not None else [],
                treatment="authoritative_fact_correction",
                rationale=(
                    "Replace the one existing usage example with the exact minimal example "
                    "compiled against the verified source build."
                ),
            )
        ]
    byte_offset = context.byte_offset(target.heading_end)
    return [
        build_operation(
            operation_id="readme.example.insert-verified-minimal",
            operation="insert_after",
            source=context.source,
            start=byte_offset,
            end=byte_offset,
            replacement="\n" + rendered + "\n\n",
            fact_ids=[example.fact_id] if example is not None else [],
            treatment="additive",
            rationale=(
                "Lead the usage section with the exact minimal example compiled against the "
                "verified source build; preserve multiple existing examples until their "
                "individual roles can be assessed."
            ),
        )
    ]
