"""Plan fact-backed license prose required by the presentation contract."""

from __future__ import annotations

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import accepted_fact


def _license_paragraph(name: str) -> str:
    normalized = name.casefold().replace("license", "").strip(" -")
    if normalized == "mit":
        return (
            "This project is available under the [MIT License](LICENSE). It permits use, "
            "modification, distribution, and commercial use when the license and copyright "
            "notice are retained."
        )
    if normalized in {"apache-2.0", "apache 2.0"}:
        return (
            "This project is available under the [Apache License 2.0](LICENSE). It permits use, "
            "modification, distribution, and commercial use subject to its notice, attribution, "
            "and patent terms."
        )
    return (
        f"This project is available under the [{name}](LICENSE). The license describes the "
        "permissions and conditions for use, modification, and distribution."
    )


def build_license_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Add readable license benefits without inventing a license classification."""

    license_fact = accepted_fact(context.facts, "product.license")
    if license_fact is None:
        return []
    name = str(license_fact.value).strip()
    if not name:
        return []
    paragraph = _license_paragraph(name)
    target = context.h2("license")
    if target is not None:
        body = context.inner_text[target.heading_end : target.section_end]
        if "[MIT License](LICENSE)" in body or (
            "[Apache License 2.0](LICENSE)" in body and "permit" in body.casefold()
        ):
            return []
        return [
            build_operation(
                operation_id="readme.license.add-benefits",
                operation="insert_after",
                source=context.source,
                start=context.byte_offset(target.heading_end),
                end=context.byte_offset(target.heading_end),
                replacement=f"\n{paragraph}\n",
                fact_ids=[license_fact.fact_id],
                treatment="additive",
                rationale=(
                    "State the selected repository license as readable prose and summarize its "
                    "practical permissions."
                ),
            )
        ]
    return [
        build_operation(
            operation_id="readme.license.add-section",
            operation="insert_after",
            source=context.source,
            start=len(context.source),
            end=len(context.source),
            replacement=f"\n\n## License\n\n{paragraph}\n",
            fact_ids=[license_fact.fact_id],
            treatment="additive",
            rationale=(
                "Add the selected repository license as readable prose with practical benefits."
            ),
        )
    ]
