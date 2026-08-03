"""Materialize contextual-link bindings beside the verified README example."""

from __future__ import annotations

import re

from readme_agent.facts.render_views import ecosystem_display_label
from readme_agent.links.contextual_models import ContextualLinkPlanV1
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_structure import code_blocks_in_span
from readme_agent.readme.document_templates import accepted_fact, load_template
from readme_agent.readme.presentation_contract import PRESENTATION_ENTERPRISE_LINK_SECTION

__all__ = [
    "apply_contextual_link_bindings",
    "render_contextual_example_markdown",
    "render_contextual_relationship_markdown",
]


def _context_paragraph(title: str, url: str) -> str:
    safe_title = " ".join(title.split()).replace("[", r"\[").replace("]", r"\]")
    return (
        load_template("contextual-example-link.md")
        .format(target_title=safe_title, target_url=url)
        .strip()
    )


def _foss_product_name(enterprise_product_name: str, platform: str) -> str:
    if " for " in enterprise_product_name:
        family, embedded_platform = enterprise_product_name.rsplit(" for ", maxsplit=1)
        return f"{family} FOSS for {embedded_platform}"
    return f"{enterprise_product_name} FOSS for {ecosystem_display_label(platform)}"


def render_contextual_relationship_markdown(
    plan: ContextualLinkPlanV1,
) -> tuple[str, list[str]]:
    """Render the one governed below-fold product-relationship paragraph."""

    relationship = [binding for binding in plan.bindings if binding.context_kind == "relationship"]
    enterprise = next(
        (binding for binding in relationship if binding.parent_domain == "aspose.com"),
        None,
    )
    foss = next(
        (binding for binding in relationship if binding.parent_domain == "aspose.org"),
        None,
    )
    fact_ids = list(
        dict.fromkeys(fact_id for binding in relationship for fact_id in binding.accepted_fact_ids)
    )
    if enterprise is not None and foss is not None:
        foss_product_name = _foss_product_name(plan.enterprise_product_name, plan.platform)
        return (
            load_template("contextual-product-relationship.md")
            .format(
                foss_product_name=foss_product_name,
                foss_url=foss.target_url,
                enterprise_product_name=plan.enterprise_product_name,
                enterprise_url=enterprise.target_url,
            )
            .strip(),
            fact_ids,
        )
    if enterprise is not None:
        return (
            load_template("contextual-enterprise-relationship.md")
            .format(
                enterprise_product_name=plan.enterprise_product_name,
                enterprise_url=enterprise.target_url,
            )
            .strip(),
            fact_ids,
        )
    if foss is not None:
        foss_product_name = _foss_product_name(plan.enterprise_product_name, plan.platform)
        return (
            load_template("contextual-foss-product.md")
            .format(foss_product_name=foss_product_name, foss_url=foss.target_url)
            .strip(),
            fact_ids,
        )
    return "", []


def render_contextual_example_markdown(plan: ContextualLinkPlanV1) -> tuple[str, list[str]]:
    """Render the selected article link beside its exact verified example."""

    bindings = [binding for binding in plan.bindings if binding.context_kind == "code_example"]
    if not bindings:
        return "", []
    if len(bindings) != 1:
        raise ValueError("verified README supports one contextual article per primary example")
    binding = bindings[0]
    return _context_paragraph(binding.target_title, binding.target_url), list(
        binding.accepted_fact_ids
    )


def _apply_relationship_bindings(
    context: DocumentRenderContext,
    operations: list[ReadmeDocumentOperationV1],
    plan: ContextualLinkPlanV1,
) -> list[ReadmeDocumentOperationV1]:
    paragraph, fact_ids = render_contextual_relationship_markdown(plan)
    if not paragraph:
        return operations
    updated = list(operations)
    source_heading = context.h2(
        "scope and limitations",
        "project scope and limitations",
        "current limitations",
        "limitations",
        "known limitations",
    )
    generated_scope_index = next(
        (
            index
            for index, operation in enumerate(updated)
            if re.search(
                r"(?mi)^##[ \t]+(?:scope and limitations|project scope and limitations|"
                r"current limitations|limitations|known limitations)[ \t]*$",
                operation.replacement_text,
            )
        ),
        None,
    )
    if source_heading is None and generated_scope_index is not None:
        operation = updated[generated_scope_index]
        replacement = operation.replacement_text.rstrip() + "\n\n" + paragraph + "\n"
        updated[generated_scope_index] = operation.model_copy(
            update={
                "replacement_text": replacement,
                "replacement_sha256": sha256_hex(replacement),
                "fact_ids": list(dict.fromkeys([*operation.fact_ids, *fact_ids])),
                "rationale": (
                    operation.rationale
                    + " Add the verified product relationship inside the same scope section."
                ),
            }
        )
        return updated
    if source_heading is None:
        offset = len(context.source)
        separator = (
            ""
            if context.inner_text.endswith("\n\n")
            else "\n"
            if context.inner_text.endswith("\n")
            else "\n\n"
        )
        replacement = f"{separator}## {PRESENTATION_ENTERPRISE_LINK_SECTION}\n\n{paragraph}\n"
    else:
        offset = context.byte_offset(source_heading.section_end)
        section = context.inner_text[source_heading.heading_end : source_heading.section_end]
        separator = "" if section.endswith("\n\n") else "\n" if section.endswith("\n") else "\n\n"
        replacement = separator + paragraph + "\n\n"
    updated.append(
        build_operation(
            operation_id="readme.links.insert-product-relationship",
            operation="insert_before" if source_heading is not None else "insert_after",
            source=context.source,
            start=offset,
            end=offset,
            replacement=replacement,
            fact_ids=fact_ids,
            treatment="additive",
            rationale=(
                "Add catalog-verified product links as natural below-fold scope context under "
                "the accepted relationship fact and configured link budget."
            ),
        )
    )
    return updated


def _insert_after_example(replacement: str, exact_code: str, paragraph: str) -> str:
    blocks = [
        block
        for block in code_blocks_in_span(replacement, 0, len(replacement))
        if block.content.strip() == exact_code
    ]
    if len(blocks) != 1:
        raise ValueError("contextual example binding cannot locate one replacement code block")
    offset = blocks[0].end
    return replacement[:offset].rstrip() + "\n\n" + paragraph + "\n" + replacement[offset:]


def apply_contextual_link_bindings(
    context: DocumentRenderContext,
    operations: list[ReadmeDocumentOperationV1],
    plan: ContextualLinkPlanV1,
) -> list[ReadmeDocumentOperationV1]:
    """Attach each selected binding to the exact accepted example operation or block."""

    if not plan.bindings:
        return operations
    updated = _apply_relationship_bindings(context, operations, plan)
    example_bindings = [
        binding for binding in plan.bindings if binding.context_kind == "code_example"
    ]
    if not example_bindings:
        return updated
    example = accepted_fact(context.facts, "example.minimal")
    value = example.value if example is not None and isinstance(example.value, dict) else {}
    exact_code = str(value.get("code") or "").strip()
    if example is None or not exact_code:
        raise ValueError("contextual example binding has no accepted example")
    for binding_index, binding in enumerate(example_bindings, start=1):
        paragraph = _context_paragraph(binding.target_title, binding.target_url)
        safe_title = " ".join(binding.target_title.split()).replace("[", r"\[").replace("]", r"\]")
        code_start = context.inner_text.find(exact_code)
        code_end_byte = len(context.inner_text[: code_start + len(exact_code)].encode("utf-8"))
        reusable_index = next(
            (
                index
                for index, operation in enumerate(updated)
                if operation.operation_id.startswith("readme.links.unwrap-unbound:")
                and operation.replacement_text == safe_title
                and context.source[operation.source_byte_start : operation.source_byte_end].decode(
                    "utf-8"
                )
                == f"[{safe_title}]({binding.target_url})"
                and operation.source_byte_start > code_end_byte
                and any(
                    heading.level == 2
                    and heading.title == binding.section_heading
                    and heading.heading_end <= code_start
                    and operation.source_byte_start
                    < len(context.inner_text[: heading.section_end].encode("utf-8"))
                    for heading in context.headings
                )
            ),
            None,
        )
        if reusable_index is not None:
            operation = updated[reusable_index]
            replacement = f"[{safe_title}]({binding.target_url})"
            updated[reusable_index] = operation.model_copy(
                update={
                    "replacement_text": replacement,
                    "replacement_sha256": sha256_hex(replacement),
                    "fact_ids": list(
                        dict.fromkeys([*operation.fact_ids, *binding.accepted_fact_ids])
                    ),
                    "rationale": (
                        operation.rationale + " Reapply the verified target because its exact "
                        "fact-bound context remains."
                    ),
                }
            )
            continue
        operation_index = next(
            (
                index
                for index, operation in enumerate(updated)
                if example.fact_id in operation.fact_ids
                and exact_code in operation.replacement_text
            ),
            None,
        )
        if operation_index is not None:
            operation = updated[operation_index]
            replacement = _insert_after_example(
                operation.replacement_text,
                exact_code,
                paragraph,
            )
            updated[operation_index] = operation.model_copy(
                update={
                    "replacement_text": replacement,
                    "replacement_sha256": sha256_hex(replacement),
                    "fact_ids": list(
                        dict.fromkeys([*operation.fact_ids, *binding.accepted_fact_ids])
                    ),
                    "rationale": operation.rationale + " Add its verified contextual article.",
                }
            )
            continue
        blocks = [
            block
            for block in code_blocks_in_span(context.inner_text, 0, len(context.inner_text))
            if block.content.strip() == exact_code
        ]
        if len(blocks) != 1:
            raise ValueError("contextual example binding cannot locate one exact source code block")
        offset = context.byte_offset(blocks[0].end)
        updated.append(
            build_operation(
                operation_id=f"readme.links.insert-example-context:{binding_index}",
                operation="insert_after",
                source=context.source,
                start=offset,
                end=offset,
                replacement="\n" + paragraph + "\n",
                fact_ids=binding.accepted_fact_ids,
                treatment="additive",
                rationale=(
                    "Place one verified article immediately after the accepted example whose "
                    "API terms it directly explains."
                ),
            )
        )
    return updated
