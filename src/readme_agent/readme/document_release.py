"""Plan verified README release-version corrections."""

from __future__ import annotations

import re

from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import accepted_fact, first_mapping

_DECLARED_VERSION = re.compile(r"\*\*Version\s+([^*]+)\*\*")


def build_release_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Align one declared version with the verified immutable-revision manifest."""

    release = accepted_fact(context.facts, "release.state")
    value = first_mapping(release.value) if release is not None else {}
    selected_version = str(value.get("version", "")).strip()
    declared_version = _DECLARED_VERSION.search(context.inner_text)
    if (
        declared_version is None
        or not selected_version
        or declared_version.group(1).strip() == selected_version
    ):
        return []
    return [
        build_operation(
            operation_id="readme.release.correct-manifest-version",
            operation="replace",
            source=context.source,
            start=context.byte_offset(declared_version.start(1)),
            end=context.byte_offset(declared_version.end(1)),
            replacement=selected_version,
            fact_ids=[release.fact_id] if release is not None else [],
            treatment="authoritative_fact_correction",
            rationale="Align the stated current version with the immutable revision's manifest.",
        )
    ]
