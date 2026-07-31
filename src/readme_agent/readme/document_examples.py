"""Plan bounded README minimal-example operations."""

from __future__ import annotations

import re

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import code_blocks_in_span
from readme_agent.readme.document_templates import accepted_fact, example_text, load_template


def _collapsed_additional_examples(content: str) -> str:
    return load_template("additional-examples-details.md").format(content=content.strip()).strip()


def build_example_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Insert or replace only the verified minimal example within a usage section."""

    example = accepted_fact(context.facts, "example.minimal")
    value = example.value if example is not None and isinstance(example.value, dict) else {}
    exact_code = str(value.get("code", "")).rstrip()
    target = context.h2("quick start", "usage")
    if not exact_code or target is None:
        return []
    existing_examples = code_blocks_in_span(
        context.inner_text,
        target.heading_end,
        target.section_end,
    )
    if exact_code in context.inner_text and len(existing_examples) <= 1:
        return []
    rendered = example_text(context.facts, context.base_revision)
    if len(existing_examples) > 1:
        section_body = context.inner_text[target.heading_end : target.section_end]
        verified_existing = next(
            (block for block in existing_examples if exact_code in block.content),
            None,
        )
        if verified_existing is None:
            primary = rendered
            additional = section_body
        else:
            primary = context.inner_text[verified_existing.start : verified_existing.end].strip()
            relative_start = verified_existing.start - target.heading_end
            relative_end = verified_existing.end - target.heading_end
            additional = section_body[:relative_start] + section_body[relative_end:]
        replacement = "\n\n" + primary.strip() + "\n\n"
        if additional.strip():
            replacement += (
                "## Additional examples\n\n" + _collapsed_additional_examples(additional) + "\n\n"
            )
        return [
            build_operation(
                operation_id="readme.example.separate-primary-workflow",
                operation="replace",
                source=context.source,
                start=context.byte_offset(target.heading_end),
                end=context.byte_offset(target.section_end),
                replacement=replacement,
                fact_ids=[example.fact_id] if example is not None else [],
                treatment="presentation_policy_correction",
                rationale=(
                    "Keep one mechanically verified primary workflow while retaining the "
                    "maintainer-authored examples in a separate section."
                ),
            )
        ]
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


def build_additional_examples_collapse_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
) -> list[ReadmeDocumentOperationV1]:
    """Collapse a pre-existing long additional-examples section once."""

    operations: list[ReadmeDocumentOperationV1] = []
    for heading in context.headings:
        if heading.level != 2 or heading.title.strip().casefold() != "additional examples":
            continue
        body = context.inner_text[heading.heading_end : heading.section_end]
        if not body.strip() or re.search(r"(?mi)^\s*<details>\s*$", body):
            continue
        start = context.byte_offset(heading.heading_end)
        end = context.byte_offset(heading.section_end)
        if any(
            operation.source_byte_start < end and start < operation.source_byte_end
            for operation in existing_operations
        ):
            continue
        replacement = "\n\n" + _collapsed_additional_examples(body) + "\n\n"
        operations.append(
            build_operation(
                operation_id=f"readme.example.collapse-additional:{start}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=replacement,
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale=(
                    "Keep the primary workflow visible while making extensive curated examples "
                    "available on demand."
                ),
            )
        )
    return operations
