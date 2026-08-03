"""Plan fact-backed license prose required by the presentation contract."""

from __future__ import annotations

import re

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import accepted_fact
from readme_agent.readme.license_location import repository_license_path

_BARE_LICENSE_LINK = re.compile(
    r"(?im)^\s*\[(?:mit(?: license)?|apache(?: license)?(?: 2\.0)?|license)\]"
    r"\([^)]+\)\.?\s*$"
)
_LICENSE_DECLARATION = re.compile(
    r"(?im)^\s*[^\n]*(?:licensed under|available under)[^\n]*"
    r"\[(?:mit(?: license)?|apache(?: license)?(?: 2\.0)?|license)\]\([^)]+\)\.?\s*$"
)
_COPYRIGHT_LINE = re.compile(
    r"(?im)^\s*(?:copyright(?:\s+(?:©|Â©|\(c\)))?|©|Â©|\(c\))\s+"
    r"\d{4}(?:\s*[-–]\s*\d{4})?[^\n]*(?:\n|$)"
)
_THIRD_PARTY_NOTICE_LINK = re.compile(
    r"\[(?P<label>[^\]]*(?:third[- ]party|THIRD_PARTY_NOTICES)[^\]]*)\]"
    r"\((?P<target>[^)]+)\)",
    re.IGNORECASE,
)


def _license_paragraph(name: str, path: str) -> str:
    normalized = name.casefold().replace("license", "").strip(" -")
    if normalized == "mit":
        return (
            f"This project is available under the [MIT License]({path}). It permits use, "
            "modification, distribution, and commercial use when the license and copyright "
            "notice are retained."
        )
    if normalized in {"apache-2.0", "apache 2.0"}:
        return (
            f"This project is available under the [Apache License 2.0]({path}). It permits use, "
            "modification, distribution, and commercial use subject to its notice, attribution, "
            "and patent terms."
        )
    return (
        f"This project is available under the [{name}]({path}). The license describes the "
        "permissions and conditions for use, modification, and distribution."
    )


def _remove_copyright_operations(
    context: DocumentRenderContext,
    *,
    body: str,
    body_start: int,
    fact_id: str,
) -> list[ReadmeDocumentOperationV1]:
    return [
        build_operation(
            operation_id=f"readme.license.remove-copyright:{body_start + match.start()}",
            operation="remove",
            source=context.source,
            start=context.byte_offset(body_start + match.start()),
            end=context.byte_offset(body_start + match.end()),
            replacement="",
            fact_ids=[fact_id],
            treatment="presentation_policy_correction",
            rationale=(
                "Use the portfolio-wide license-benefits paragraph without a standalone "
                "README copyright line."
            ),
        )
        for match in _COPYRIGHT_LINE.finditer(body)
    ]


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
    path = repository_license_path(license_fact)
    paragraph = _license_paragraph(name, path)
    target = context.h2("license")
    if target is not None:
        body = context.inner_text[target.heading_end : target.section_end]
        copyright_operations = _remove_copyright_operations(
            context,
            body=body,
            body_start=target.heading_end,
            fact_id=license_fact.fact_id,
        )
        if f"]({path})" in body and "permit" in body.casefold():
            return copyright_operations
        declarations = [
            match for match in _LICENSE_DECLARATION.finditer(body) if f"]({path})" in match.group()
        ]
        if declarations:
            declaration = declarations[0]
            return [
                build_operation(
                    operation_id="readme.license.replace-declaration",
                    operation="replace",
                    source=context.source,
                    start=context.byte_offset(target.heading_end + declaration.start()),
                    end=context.byte_offset(target.heading_end + declaration.end()),
                    replacement=paragraph,
                    fact_ids=[license_fact.fact_id],
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Replace a simple license declaration with the accepted "
                        "repository-relative path and readable permission summary."
                    ),
                ),
                *copyright_operations,
            ]
        bare_links = list(_BARE_LICENSE_LINK.finditer(body))
        if bare_links:
            bare_link = bare_links[0]
            return [
                build_operation(
                    operation_id="readme.license.replace-bare-link",
                    operation="replace",
                    source=context.source,
                    start=context.byte_offset(target.heading_end + bare_link.start()),
                    end=context.byte_offset(target.heading_end + bare_link.end()),
                    replacement=paragraph,
                    fact_ids=[license_fact.fact_id],
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Replace a bare license link with the accepted repository-relative path "
                        "and readable permission summary."
                    ),
                ),
                *copyright_operations,
            ]
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
        ] + copyright_operations
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


def build_third_party_notice_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Promote inherited notice evidence into a dedicated relative-link section."""

    if "distribution.license_expression" not in context.facts.selected_fact_ids:
        return []
    license_expression = accepted_fact(context.facts, "distribution.license_expression")
    if license_expression is None:
        return []
    match = _THIRD_PARTY_NOTICE_LINK.search(context.inner_text)
    if match is None or not match.group("target").rstrip("/").casefold().endswith(
        "third_party_notices.md"
    ):
        return []
    target_start, target_end = match.span("target")
    notices = context.h2("third-party notices")
    if notices is not None:
        if not match.group("target").casefold().startswith(("http://", "https://")):
            return []
        return [
            build_operation(
                operation_id="readme.notices.use-relative-link",
                operation="replace",
                source=context.source,
                start=context.byte_offset(target_start),
                end=context.byte_offset(target_end),
                replacement="THIRD_PARTY_NOTICES.md",
                fact_ids=[],
                treatment="presentation_policy_correction",
                rationale="Use the inherited root notice filename as a repository-relative link.",
            )
        ]

    line_start = context.inner_text.rfind("\n", 0, match.start()) + 1
    line_end = context.inner_text.find("\n", match.end())
    line_end = len(context.inner_text) if line_end < 0 else line_end + 1
    inherited_line = context.inner_text[line_start:line_end].strip()
    inherited_line = _THIRD_PARTY_NOTICE_LINK.sub(
        lambda found: f"[{found.group('label')}](THIRD_PARTY_NOTICES.md)",
        inherited_line,
        count=1,
    )
    return [
        build_operation(
            operation_id="readme.notices.add-dedicated-section",
            operation="replace",
            source=context.source,
            start=context.byte_offset(line_start),
            end=context.byte_offset(line_end),
            replacement=f"## Third-party notices\n\n{inherited_line}\n",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale=(
                "Preserve inherited third-party context under the dedicated legal heading and "
                "use its repository-relative root notice path."
            ),
        )
    ]
