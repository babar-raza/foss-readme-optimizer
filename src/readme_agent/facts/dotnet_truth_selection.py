"""Select bounded visitor-facing facts from current-revision .NET evidence."""

from __future__ import annotations

import re
from collections.abc import Iterable

from readme_agent.facts.dotnet_repository_evidence_schema import (
    DotnetApiTypeEvidenceV1,
    DotnetRepositoryEvidenceCatalogV1,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_MAX_CAPABILITIES = 8
_GENERIC_SUMMARY = re.compile(r"(?i)^represents (?:an? |the )?[a-z0-9_. ]+\.?$")
_CAPABILITY_VERBS = re.compile(
    r"(?i)\b(?:access|build|convert|create|extract|generate|load|manage|parse|process|"
    r"provide|read|render|save|transform|write)\w*\b"
)
_LOW_VALUE_TYPE_SUFFIXES = (
    "collection",
    "enum",
    "eventargs",
    "exception",
    "options",
    "settings",
    "style",
    "type",
)


def _repository_location(path: str, line: int, digest: str) -> str:
    return f"repository://{path}?sha256={digest}#L{line}"


def _fact(
    field: str,
    qualifier: str,
    value: object,
    *,
    source_location: str,
    source_revision: str,
    observed_at: str | None,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, qualifier),
        field=field,
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location=source_location,
            source_revision=source_revision,
            retrieved_at=observed_at,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=SURFACE_DEPENDENCIES[field],
    )


def _capability_score(record: DotnetApiTypeEvidenceV1) -> tuple[int, int, int, str]:
    summary = (record.summary or "").strip()
    return (
        0 if summary and not _GENERIC_SUMMARY.fullmatch(summary) else 1,
        -len(_CAPABILITY_VERBS.findall(summary)),
        1 if record.name.casefold().endswith(_LOW_VALUE_TYPE_SUFFIXES) else 0,
        record.qualified_name.casefold(),
    )


def _capability_records(
    records: Iterable[DotnetApiTypeEvidenceV1],
) -> list[DotnetApiTypeEvidenceV1]:
    selected: list[DotnetApiTypeEvidenceV1] = []
    seen: set[str] = set()
    for record in sorted(records, key=_capability_score):
        summary = (record.summary or "").strip()
        if not summary or _GENERIC_SUMMARY.fullmatch(summary):
            continue
        normalized = summary.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        selected.append(record)
        if len(selected) >= _MAX_CAPABILITIES:
            break
    if selected:
        return selected
    return sorted(records, key=_capability_score)[:_MAX_CAPABILITIES]


def _capability_value(record: DotnetApiTypeEvidenceV1) -> str:
    summary = (record.summary or "").strip()
    if summary:
        return summary
    return f"Provides the {record.qualified_name} public API."


def _format_values(catalog: DotnetRepositoryEvidenceCatalogV1) -> list[str]:
    values: list[str] = []
    for record in catalog.formats:
        directions = ("import", "export") if record.direction == "both" else (record.direction,)
        for direction in directions:
            prefix = "Input format" if direction == "import" else "Output format"
            value = f"{prefix}: {record.format}"
            if value not in values:
                values.append(value)
    return values


def dotnet_repository_truth_candidates(
    catalog: DotnetRepositoryEvidenceCatalogV1,
    *,
    observed_at: str | None,
) -> list[FactRecordV2]:
    """Return only claims directly supported by the immutable .NET catalog."""

    candidates: list[FactRecordV2] = [
        _fact(
            "product.audience",
            "dotnet-product-root",
            ["Developers using .NET."],
            source_location=(
                f"repository://{catalog.selected_manifest_path}"
                f"?inventory_sha256={catalog.inventory_sha256}"
                f"&root_role_sha256={catalog.root_role_sha256}"
            ),
            source_revision=catalog.source_revision,
            observed_at=observed_at,
        )
    ]
    capability_records = _capability_records(catalog.api_types)
    if capability_records:
        candidates.append(
            _fact(
                "product.capabilities",
                "dotnet-public-api",
                [_capability_value(record) for record in capability_records],
                source_location=";".join(
                    _repository_location(
                        record.source_path,
                        record.source_line,
                        record.source_sha256,
                    )
                    for record in capability_records
                ),
                source_revision=catalog.source_revision,
                observed_at=observed_at,
            )
        )
    format_values = _format_values(catalog)
    if format_values:
        candidates.append(
            _fact(
                "product.formats",
                "dotnet-functional-formats",
                format_values,
                source_location=";".join(
                    _repository_location(
                        record.source_path,
                        record.source_line,
                        record.source_sha256,
                    )
                    for record in catalog.formats
                ),
                source_revision=catalog.source_revision,
                observed_at=observed_at,
            )
        )
    return candidates
