"""Plan verified README acquisition corrections and registry-badge removal."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2
from readme_agent.readme.acquisition_contracts import (
    contradicted_package_claim_spans,
    stale_coordinate_version_replacements,
)
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import ReadmeDocumentOperationV1
from readme_agent.readme.document_render_context import DocumentRenderContext
from readme_agent.readme.document_templates import (
    accepted_fact,
    installation_text,
    mapping_value,
)
from readme_agent.readme.fact_grounding import literal_fact_ids

_MAVEN_CENTRAL_BADGE = re.compile(r"(?m)^\[!\[[^\]]*Maven Central[^\]]*\]\([^\n]*\)\]\([^\n]*\)\n")


def _source_build_only(context: DocumentRenderContext) -> tuple[bool, FactRecordV2 | None]:
    acquisition = accepted_fact(context.facts, "installation.verified_acquisition")
    value = mapping_value(acquisition.value) if acquisition is not None else {}
    return value.get("method") == "source_build", acquisition


def build_acquisition_correction_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Correct contradicted acquisition claims and stale coordinate versions."""

    installation = context.h2("installation")
    if installation is None:
        return []
    source_build_only, _ = _source_build_only(context)
    verified_installation = installation_text(
        context.facts,
        context.org_repo,
        context.base_revision,
    )
    body = context.inner_text[installation.heading_end : installation.section_end]
    operations: list[ReadmeDocumentOperationV1] = []
    contradicted_spans = contradicted_package_claim_spans(body) if source_build_only else []
    if contradicted_spans:
        if not verified_installation:
            raise ValueError(
                "verified source acquisition has no ecosystem-specific rendering contract"
            )
        insertion = context.byte_offset(installation.heading_end)
        operations.append(
            build_operation(
                operation_id="readme.installation.verified-source-insertion",
                operation="insert_after",
                source=context.source,
                start=insertion,
                end=insertion,
                replacement="\n" + verified_installation + "\n\n",
                fact_ids=[
                    selected.fact_id
                    for field in (
                        "installation.coordinates",
                        "installation.verified_acquisition",
                        "product.compatibility",
                    )
                    if (selected := accepted_fact(context.facts, field)) is not None
                ],
                treatment="additive",
                rationale=(
                    "Add the source-build path that was executed for this immutable revision "
                    "before removing only the contradicted package claim."
                ),
            )
        )
        for index, (claim_start, claim_end) in enumerate(contradicted_spans, start=1):
            start = context.byte_offset(installation.heading_end + claim_start)
            end = context.byte_offset(installation.heading_end + claim_end)
            operations.append(
                build_operation(
                    operation_id=f"readme.installation.remove-false-package-claim:{index}",
                    operation="remove",
                    source=context.source,
                    start=start,
                    end=end,
                    replacement="",
                    fact_ids=[
                        selected.fact_id
                        for field in (
                            "installation.coordinates",
                            "installation.verified_acquisition",
                        )
                        if (selected := accepted_fact(context.facts, field)) is not None
                    ],
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Remove only the package-registry claim contradicted by the verified "
                        "source-build acquisition, preserving adjacent maintainer content."
                    ),
                )
            )
    coordinates = accepted_fact(context.facts, "installation.coordinates")
    stale_versions = (
        stale_coordinate_version_replacements(body, coordinates.value)
        if coordinates is not None and not source_build_only
        else []
    )
    for index, (version_start, version_end, selected_version) in enumerate(
        stale_versions,
        start=1,
    ):
        start = context.byte_offset(installation.heading_end + version_start)
        end = context.byte_offset(installation.heading_end + version_end)
        operations.append(
            build_operation(
                operation_id=f"readme.installation.correct-coordinate-version:{index}",
                operation="replace",
                source=context.source,
                start=start,
                end=end,
                replacement=selected_version,
                fact_ids=literal_fact_ids(
                    selected_version,
                    context.facts,
                    [coordinates.fact_id] if coordinates is not None else [],
                ),
                treatment="authoritative_fact_correction",
                rationale=(
                    "Align the package acquisition coordinate with the selected immutable "
                    "manifest version."
                ),
            )
        )
    return operations


def build_registry_badge_operations(
    context: DocumentRenderContext,
) -> list[ReadmeDocumentOperationV1]:
    """Remove a registry badge only when verified acquisition is source-build-only."""

    source_build_only, acquisition = _source_build_only(context)
    badge = _MAVEN_CENTRAL_BADGE.search(context.inner_text) if source_build_only else None
    if badge is None:
        return []
    return [
        build_operation(
            operation_id="readme.installation.remove-unverified-registry-badge",
            operation="remove",
            source=context.source,
            start=context.byte_offset(badge.start()),
            end=context.byte_offset(badge.end()),
            replacement="",
            fact_ids=[acquisition.fact_id] if acquisition is not None else [],
            treatment="authoritative_fact_correction",
            rationale=(
                "Remove a package-registry availability badge when the selected verified "
                "acquisition method is a source build."
            ),
        )
    ]
