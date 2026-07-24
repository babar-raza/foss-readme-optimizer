"""Render a complete fact-backed README through bounded document operations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_plan import (
    DocumentOperation,
    PresentationSpanAdoptionV1,
    ProtectedContentTreatment,
    ReadmeDocumentOperationV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.readme.markers import find_presentation_span, render_presentation_span

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE_ROOT = _PROJECT_ROOT / "templates" / "readme"
_DOCUMENT_TEMPLATE_NAMES = (
    "product-overview-and-navigation.md",
    "verified-minimal-example.md",
    "verified-source-acquisition.md",
)
_PROMOTIONAL_CALLOUT = re.compile(
    r"(?m)^>[^\n]*(?:products\.aspose\.org)[^\n]*(?:products\.aspose\.com)[^\n]*\n(?:\n)?",
    re.IGNORECASE,
)
_MAVEN_CENTRAL_BADGE = re.compile(r"(?m)^\[!\[[^\]]*Maven Central[^\]]*\]\([^\n]*\)\]\([^\n]*\)\n")
_DECLARED_VERSION = re.compile(r"\*\*Version\s+([^*]+)\*\*")


@dataclass(frozen=True)
class _Heading:
    level: int
    title: str
    start: int
    heading_end: int
    section_end: int


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _load_template(name: str) -> str:
    return (_TEMPLATE_ROOT / name).read_text(encoding="utf-8")


def document_template_hash() -> str:
    """Hash every fill-and-match input used by the document renderer."""

    digest = hashlib.sha256()
    for name in _DOCUMENT_TEMPLATE_NAMES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update((_TEMPLATE_ROOT / name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _headings(text: str) -> list[_Heading]:
    tokens = MarkdownIt("commonmark").parse(text)
    offsets = _line_offsets(text)
    raw: list[tuple[int, str, int, int]] = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        title = tokens[index + 1].content if index + 1 < len(tokens) else ""
        level = int(token.tag.removeprefix("h"))
        start_line, end_line = token.map
        raw.append((level, title, offsets[start_line], offsets[end_line]))
    headings = []
    for index, (level, title, start, heading_end) in enumerate(raw):
        section_end = len(text)
        for later_level, _, later_start, _ in raw[index + 1 :]:
            if later_level <= level:
                section_end = later_start
                break
        headings.append(_Heading(level, title, start, heading_end, section_end))
    return headings


def _fact(facts: ProductFactsV2, field: str):
    return facts.selected_fact(field)


def _sentence_list(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item).rstrip(".") + "." for item in value)
    return str(value)


def _text_value(value: object) -> str:
    if isinstance(value, list):
        return _sentence_list(value)
    return str(value)


def _mapping_value(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return {}


def _first_mapping(value: object) -> dict:
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), {})
    return _mapping_value(value)


def _github_anchor(title: str) -> str:
    lowered = title.strip().lower()
    lowered = re.sub(r"[^\w\s-]", "", lowered)
    return re.sub(r"[\s-]+", "-", lowered).strip("-")


def _operation(
    *,
    operation_id: str,
    operation: DocumentOperation,
    source: bytes,
    start: int,
    end: int,
    replacement: str,
    fact_ids: list[str],
    treatment: ProtectedContentTreatment,
    rationale: str,
) -> ReadmeDocumentOperationV1:
    replacement_bytes = replacement.encode("utf-8")
    return ReadmeDocumentOperationV1(
        operation_id=operation_id,
        operation=operation,
        source_byte_start=start,
        source_byte_end=end,
        expected_sha256=_sha256(source[start:end]),
        replacement_text=replacement,
        replacement_sha256=_sha256(replacement_bytes),
        fact_ids=fact_ids,
        protected_content_treatment=treatment,
        rationale=rationale,
        validators=[
            "source_span_hash",
            "fact_citations",
            "protected_content",
            "document_reconstruction",
            "independent_verifier",
        ],
        rollback="Restore the exact immutable source bytes for this operation.",
        stop_conditions=[
            "immutable source revision changed",
            "source span checksum changed",
            "a cited fact is no longer selected and accepted",
            "protected content outside an authoritative correction would be lost",
        ],
    )


def _installation_text(
    facts: ProductFactsV2,
    org_repo: str,
    source_revision: str,
) -> str:
    compatibility = _fact(facts, "product.compatibility")
    value = _mapping_value(compatibility.value)
    return (
        _load_template("verified-source-acquisition.md")
        .format(
            org_repo=org_repo,
            repository_name=org_repo.split("/", 1)[1],
            source_revision=source_revision,
            minimum_runtime=value.get("minimum_runtime", "unknown"),
        )
        .strip()
    )


def _example_text(facts: ProductFactsV2, source_revision: str) -> str:
    example = _fact(facts, "example.minimal")
    value = example.value if isinstance(example.value, dict) else {}
    return (
        _load_template("verified-minimal-example.md")
        .format(
            language=value.get("language", "text"),
            code=str(value.get("code", "")).rstrip(),
            source_revision=source_revision,
        )
        .strip()
    )


def _overview_text(facts: ProductFactsV2, headings: list[_Heading]) -> str:
    compatibility = _fact(facts, "product.compatibility")
    compatibility_value = _mapping_value(compatibility.value)
    navigation = "\n".join(
        f"- [{heading.title}](#{_github_anchor(heading.title)})"
        for heading in headings
        if heading.level == 2
        and heading.title.strip().lower() not in {"at a glance", "in this readme"}
    )
    return (
        _load_template("product-overview-and-navigation.md")
        .format(
            audience=_text_value(_fact(facts, "product.audience").value),
            problem=_text_value(_fact(facts, "product.problems_solved").value),
            capabilities=_sentence_list(_fact(facts, "product.capabilities").value),
            formats=_sentence_list(_fact(facts, "product.formats").value),
            minimum_runtime=compatibility_value.get("minimum_runtime", "unknown"),
            limitations=_text_value(_fact(facts, "product.limitations").value),
            navigation=navigation or "- Continue with the repository guidance below.",
        )
        .strip()
    )


def apply_document_operations(source: bytes, operations: list[ReadmeDocumentOperationV1]) -> bytes:
    rendered = source
    for operation in sorted(
        operations,
        key=lambda item: (item.source_byte_start, item.source_byte_end),
        reverse=True,
    ):
        current = rendered[operation.source_byte_start : operation.source_byte_end]
        if _sha256(current) != operation.expected_sha256:
            raise ValueError(f"source span changed for {operation.operation_id}")
        rendered = (
            rendered[: operation.source_byte_start]
            + operation.replacement_text.encode("utf-8")
            + rendered[operation.source_byte_end :]
        )
    return rendered


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
    headings = _headings(inner_text)
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
        _fact(facts, field).fact_id
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
        overview_insert = _overview_text(facts, headings) + "\n\n"
    if installation is None:
        overview_insert += (
            "## Installation\n\n" + _installation_text(facts, org_repo, base_revision) + "\n\n"
        )
        overview_fact_ids.extend(
            [
                _fact(facts, "installation.verified_acquisition").fact_id,
                _fact(facts, "product.compatibility").fact_id,
            ]
        )
    if overview_insert:
        char_offset = first_h2.start if first_h2 is not None else len(inner_text)
        byte_offset = len(inner_text[:char_offset].encode("utf-8"))
        operations.append(
            _operation(
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

    if installation is not None:
        installation_body = inner_text[installation.heading_end : installation.section_end]
        contains_unverified_package_install = any(
            marker in installation_body
            for marker in ("<dependency>", "implementation 'org.", 'implementation "org.')
        )
        if contains_unverified_package_install:
            start = len(inner_text[: installation.heading_end].encode("utf-8"))
            end = len(inner_text[: installation.section_end].encode("utf-8"))
            replacement = "\n" + _installation_text(facts, org_repo, base_revision) + "\n\n"
            operations.append(
                _operation(
                    operation_id="readme.installation.verified-source-replacement",
                    operation="replace",
                    source=source,
                    start=start,
                    end=end,
                    replacement=replacement,
                    fact_ids=[
                        _fact(facts, "installation.coordinates").fact_id,
                        _fact(facts, "installation.verified_acquisition").fact_id,
                        _fact(facts, "product.compatibility").fact_id,
                    ],
                    treatment="authoritative_fact_correction",
                    rationale=(
                        "Replace an unverified registry-install claim with the source-build path "
                        "that was executed for this immutable revision."
                    ),
                )
            )

    example = _fact(facts, "example.minimal")
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
                _operation(
                    operation_id="readme.example.insert-verified-minimal",
                    operation="insert_after",
                    source=source,
                    start=byte_offset,
                    end=byte_offset,
                    replacement="\n" + _example_text(facts, base_revision) + "\n\n",
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
            _operation(
                operation_id="readme.opening.remove-promotional-callout",
                operation="remove",
                source=source,
                start=start,
                end=end,
                replacement="",
                fact_ids=[_fact(facts, "relationship.commercial_foss").fact_id],
                treatment="authoritative_fact_correction",
                rationale=(
                    "Keep the first screen product-first; the existing relationship section "
                    "continues to carry restrained commercial context."
                ),
            )
        )

    acquisition = _fact(facts, "installation.verified_acquisition")
    acquisition_value = _mapping_value(acquisition.value)
    if acquisition_value.get("method") == "source_build":
        maven_badge = _MAVEN_CENTRAL_BADGE.search(inner_text)
        if maven_badge is not None:
            start = len(inner_text[: maven_badge.start()].encode("utf-8"))
            end = len(inner_text[: maven_badge.end()].encode("utf-8"))
            operations.append(
                _operation(
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

    release = _fact(facts, "release.state")
    release_value = _first_mapping(release.value)
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
            _operation(
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
        source_sha256=_sha256(source_text),
        adoption=PresentationSpanAdoptionV1(
            already_adopted=existing is not None,
            source_document_sha256=_sha256(source_text),
            source_inner_sha256=_sha256(source),
            source_inner_bytes=len(source),
            preservation_check="byte_identical",
        ),
        operations=operations,
        candidate_sha256=_sha256(candidate),
    )
    return candidate, plan
