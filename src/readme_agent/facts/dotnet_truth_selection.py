"""Select bounded visitor-facing facts from current-revision .NET evidence."""

from __future__ import annotations

from readme_agent.facts.dotnet_capability_distillation import (
    distilled_dotnet_capability_entries,
)
from readme_agent.facts.dotnet_repository_evidence_schema import DotnetRepositoryEvidenceCatalogV1
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id


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
    capability_entries = distilled_dotnet_capability_entries(catalog.api_types)
    if capability_entries:
        candidates.append(
            _fact(
                "product.capabilities",
                "dotnet-public-api",
                [capability for _, capability in capability_entries],
                source_location=";".join(
                    _repository_location(
                        record.source_path,
                        record.source_line,
                        record.source_sha256,
                    )
                    for record, _ in capability_entries
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
