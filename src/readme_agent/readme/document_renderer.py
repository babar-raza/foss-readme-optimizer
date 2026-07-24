"""Render a complete fact-backed README through bounded document operations.

This module holds only the editorial policy -- ``build_readme_document_candidate``
decides *which* bounded operations to apply for a repository. The supporting
machinery lives in sibling modules, each with one responsibility
(`GOVERNANCE.md` "no monoliths"):

- ``document_structure``  -- markdown heading/section parsing and anchors;
- ``document_templates``  -- template loading/hashing and fact-to-section prose;
- ``document_operations`` -- operation construction and hash-checked application;
- ``document_hashing``    -- the shared SHA-256 helper.

``apply_document_operations`` and ``document_template_hash`` are re-exported here
so existing importers (``document_validation``) keep their import path.
"""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import apply_document_operations, build_operation
from readme_agent.readme.document_plan import (
    PresentationSpanAdoptionV1,
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.document_structure import parse_headings
from readme_agent.readme.document_templates import (
    document_template_hash,
    example_text,
    fact,
    first_mapping,
    installation_text,
    mapping_value,
    overview_text,
)
from readme_agent.readme.markers import find_presentation_span, render_presentation_span

__all__ = [
    "apply_document_operations",
    "build_readme_document_candidate",
    "document_template_hash",
]

_PROMOTIONAL_CALLOUT = re.compile(
    r"(?m)^>[^\n]*(?:products\.aspose\.org)[^\n]*(?:products\.aspose\.com)[^\n]*\n(?:\n)?",
    re.IGNORECASE,
)
_MAVEN_CENTRAL_BADGE = re.compile(r"(?m)^\[!\[[^\]]*Maven Central[^\]]*\]\([^\n]*\)\]\([^\n]*\)\n")
_DECLARED_VERSION = re.compile(r"\*\*Version\s+([^*]+)\*\*")


def build_readme_document_candidate(
    org_repo: str,
    source_text: str,
    facts: ProductFactsV2,
    *,
    base_revision: str,
) -> tuple[str, ReadmeDocumentPlanV1]:
    """Return one reproducible candidate and its fine-grained source operations."""

    existing = find_presentation_span(source_text)
    inner_text = existing.content if existing is not None else source_text
    source = inner_text.encode("utf-8")
    headings = parse_headings(inner_text)
    operations: list[ReadmeDocumentOperationV1] = []

    first_h2 = next((heading for heading in headings if heading.level == 2), None)
    has_overview = any(
        heading.level == 2 and heading.title.strip().lower() == "at a glance"
        for heading in headings
    )
    installation = next(
        (
            heading
            for heading in headings
            if heading.level == 2 and heading.title.strip().lower() == "installation"
        ),
        None,
    )
    overview_insert = ""
    overview_fact_ids = [
        fact(facts, field).fact_id
        for field in (
            "product.audience",
            "product.problems_solved",
            "product.capabilities",
            "product.formats",
            "product.compatibility",
            "product.limitations",
        )
    ]
    if not has_overview:
        overview_insert = overview_text(facts, headings) + "\n\n"
    if installation is None:
        overview_insert += (
            "## Installation\n\n" + installation_text(facts, org_repo, base_revision) + "\n\n"
        )
        overview_fact_ids.extend(
            [
                fact(facts, "installation.verified_acquisition").fact_id,
                fact(facts, "product.compatibility").fact_id,
            ]
        )
    if overview_insert:
        char_offset = first_h2.start if first_h2 is not None else len(inner_text)
        byte_offset = len(inner_text[:char_offset].encode("utf-8"))
        operations.append(
            build_operation(
                operation_id="readme.overview-navigation-and-acquisition",
                operation="insert_before",
                source=source,
                start=byte_offset,
                end=byte_offset,
                replacement=overview_insert,
                fact_ids=sorted(set(overview_fact_ids)),
                treatment="additive",
                rationale=(
                    "Put verified audience, purpose, scope, navigation, and any missing source "
                    "acquisition path before secondary repository detail."
                ),
            )
        )

    acquisition = fact(facts, "installation.verified_acquisition")
    acquisition_value = mapping_value(acquisition.value)
    # The "aspose {family} foss" rule: only replace a registry install with source-build when
    # the package is genuinely NOT published (method == "source_build"). A registry-verified
    # package's correct install claim must never be stripped just because the README text
    # happens to match one of these markers -- see foss_coordinate.py and provider.py.
    package_genuinely_not_published = acquisition_value.get("method") == "source_build"

    if installation is not None:
        installation_body = inner_text[installation.heading_end : installation.section_end]
        contains_unverified_package_install = package_genuinely_not_published and any(
            marker in installation_body
            for marker in ("<dependency>", "implementation 'org.", 'implementation "org.')
        )
        if contains_unverified_package_install:
            start = len(inner_text[: installation.heading_end].encode("utf-8"))
            end = len(inner_text[: installation.section_end].encode("utf-8"))
            replacement = "\n" + installation_text(facts, org_repo, base_revision) + "\n\n"
            operations.append(
                build_operation(
                    operation_id="readme.installation.verified-source-replacement",
                    operation="replace",
                    source=source,
                    start=start,
                    end=end,
                    replacement=replacement,
                    fact_ids=[
                        fact(facts, "installation.coordinates").fact_id,
                        fact(facts, "installation.verified_acquisition").fact_id,
                        fact(facts, "product.compatibility").fact_id,
                    ],
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Replace an unverified registry-install claim with the source-build path "
                        "that was executed for this immutable revision."
                    ),
                )
            )

    example = fact(facts, "example.minimal")
    example_value = example.value if isinstance(example.value, dict) else {}
    exact_code = str(example_value.get("code", "")).rstrip()
    if exact_code and exact_code not in inner_text:
        target = next(
            (
                heading
                for heading in headings
                if heading.level == 2 and heading.title.strip().lower() in {"quick start", "usage"}
            ),
            None,
        )
        if target is not None:
            byte_offset = len(inner_text[: target.heading_end].encode("utf-8"))
            operations.append(
                build_operation(
                    operation_id="readme.example.insert-verified-minimal",
                    operation="insert_after",
                    source=source,
                    start=byte_offset,
                    end=byte_offset,
                    replacement="\n" + example_text(facts, base_revision) + "\n\n",
                    fact_ids=[example.fact_id],
                    treatment="additive",
                    rationale=(
                        "Lead the usage section with the exact minimal example compiled against "
                        "the verified source build."
                    ),
                )
            )

    callout = _PROMOTIONAL_CALLOUT.search(inner_text)
    if callout is not None:
        start = len(inner_text[: callout.start()].encode("utf-8"))
        end = len(inner_text[: callout.end()].encode("utf-8"))
        operations.append(
            build_operation(
                operation_id="readme.opening.remove-promotional-callout",
                operation="remove",
                source=source,
                start=start,
                end=end,
                replacement="",
                fact_ids=[fact(facts, "relationship.commercial_foss").fact_id],
                treatment="authoritative_fact_correction",
                rationale=(
                    "Keep the first screen product-first; the existing relationship section "
                    "continues to carry restrained commercial context."
                ),
            )
        )

    if package_genuinely_not_published:
        maven_badge = _MAVEN_CENTRAL_BADGE.search(inner_text)
        if maven_badge is not None:
            start = len(inner_text[: maven_badge.start()].encode("utf-8"))
            end = len(inner_text[: maven_badge.end()].encode("utf-8"))
            operations.append(
                build_operation(
                    operation_id="readme.installation.remove-unverified-registry-badge",
                    operation="remove",
                    source=source,
                    start=start,
                    end=end,
                    replacement="",
                    fact_ids=[acquisition.fact_id],
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Remove a package-registry availability badge when the selected verified "
                        "acquisition method is a source build."
                    ),
                )
            )

    release = fact(facts, "release.state")
    release_value = first_mapping(release.value)
    selected_version = str(release_value.get("version", "")).strip()
    declared_version = _DECLARED_VERSION.search(inner_text)
    if (
        declared_version is not None
        and selected_version
        and declared_version.group(1).strip() != selected_version
    ):
        start = len(inner_text[: declared_version.start(1)].encode("utf-8"))
        end = len(inner_text[: declared_version.end(1)].encode("utf-8"))
        operations.append(
            build_operation(
                operation_id="readme.release.correct-manifest-version",
                operation="replace",
                source=source,
                start=start,
                end=end,
                replacement=selected_version,
                fact_ids=[release.fact_id],
                treatment="authoritative_fact_correction",
                rationale=(
                    "Align the stated current version with the immutable revision's manifest."
                ),
            )
        )

    rendered_inner = apply_document_operations(source, operations).decode("utf-8")
    facts_hash = facts.canonical_hash()
    candidate = render_presentation_span(rendered_inner, facts_hash)
    plan = ReadmeDocumentPlanV1(
        org_repo=org_repo,
        immutable_base_revision=base_revision,
        facts_hash=facts_hash,
        template_sha256=document_template_hash(),
        source_sha256=sha256_hex(source_text),
        adoption=PresentationSpanAdoptionV1(
            already_adopted=existing is not None,
            source_document_sha256=sha256_hex(source_text),
            source_inner_sha256=sha256_hex(source),
            source_inner_bytes=len(source),
            preservation_check="byte_identical",
        ),
        operations=operations,
        candidate_sha256=sha256_hex(candidate),
    )
    return candidate, plan
