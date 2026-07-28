"""Plan bounded Enterprise Edition corrections for visitor-facing README text."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.terminology import (
    EnterpriseTerminologyCorrectionV1,
    canonicalize_enterprise_edition,
    enterprise_product_name_from_facts,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import accepted_fact


def enterprise_product_name(facts: ProductFactsV2) -> str:
    """Return the accepted product/platform name without the FOSS edition token."""

    return enterprise_product_name_from_facts(facts)


def canonicalize_operation_terminology(
    operations: list[ReadmeDocumentOperationV1],
    *,
    product_name: str,
    identity_fact_id: str,
) -> list[ReadmeDocumentOperationV1]:
    """Normalize generated replacement text before operations reach the candidate."""

    normalized: list[ReadmeDocumentOperationV1] = []
    for operation in operations:
        replacement, corrections = canonicalize_enterprise_edition(
            operation.replacement_text,
            enterprise_product_name=product_name,
        )
        if not corrections:
            normalized.append(operation)
            continue
        normalized.append(
            operation.model_copy(
                update={
                    "replacement_text": replacement,
                    "replacement_sha256": sha256_hex(replacement),
                    "fact_ids": list(dict.fromkeys([*operation.fact_ids, identity_fact_id])),
                    "rationale": (
                        operation.rationale
                        + " Normalize all visitor-facing Aspose product references to "
                        "Enterprise Edition."
                    ),
                }
            )
        )
    return normalized


def build_enterprise_terminology_operations(
    context: DocumentRenderContext,
    existing_operations: list[ReadmeDocumentOperationV1],
    *,
    product_name: str,
) -> tuple[list[ReadmeDocumentOperationV1], list[EnterpriseTerminologyCorrectionV1]]:
    """Correct uncovered legacy source labels without overlapping another operation."""

    _, corrections = canonicalize_enterprise_edition(
        context.inner_text,
        enterprise_product_name=product_name,
    )
    identity = accepted_fact(context.facts, "product.identity")
    relationship = accepted_fact(context.facts, "relationship.commercial_foss")
    fact_ids = [fact.fact_id for fact in (identity, relationship) if fact is not None]
    operations: list[ReadmeDocumentOperationV1] = []
    for index, correction in enumerate(corrections, start=1):
        start = context.byte_offset(correction.character_start)
        end = context.byte_offset(correction.character_end)
        if any(
            operation.source_byte_start < end and start < operation.source_byte_end
            for operation in existing_operations
        ):
            continue
        operations.append(
            build_operation(
                operation_id=f"readme.terminology.enterprise-{index}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=correction.replacement,
                fact_ids=fact_ids,
                treatment="presentation_policy_correction",
                rationale=(
                    "Replace a legacy Aspose edition label with the exact accepted product "
                    "name and Enterprise Edition descriptor."
                ),
            )
        )
    return operations, corrections
