"""Tests for bounded .NET evidence-to-fact selection."""

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatExtractionV1
from readme_agent.facts.dotnet_repository_evidence_schema import (
    AsposeOrgDotnetExtractionV1,
    DotnetApiTypeEvidenceV1,
    DotnetFormatEvidenceV1,
    DotnetRepositoryEvidenceCatalogV1,
)
from readme_agent.facts.dotnet_truth_selection import dotnet_repository_truth_candidates


def _api_type(name: str, summary: str) -> DotnetApiTypeEvidenceV1:
    return DotnetApiTypeEvidenceV1(
        evidence_id=f"api-{name.casefold()}",
        origin="local_lexer",
        name=name,
        qualified_name=f"Aspose.Cells_FOSS.{name}",
        kind="class",
        summary=summary,
        source_path=f"src/Product/{name}.cs",
        source_line=3,
        source_sha256="a" * 64,
    )


def _catalog() -> DotnetRepositoryEvidenceCatalogV1:
    return DotnetRepositoryEvidenceCatalogV1(
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
        source_revision="b" * 40,
        inventory_sha256="c" * 64,
        selected_manifest_path="src/Product/Product.csproj",
        selected_product_root="src/Product",
        root_role_sha256="d" * 64,
        api_extraction=AsposeOrgDotnetExtractionV1(
            status="unavailable",
            completeness="unavailable",
            detail="fixture uses repository evidence",
        ),
        api_types=(
            _api_type("AutoFilter", "Represents auto filter."),
            _api_type("Cells", "Provides access to worksheet cells, rows, and columns."),
            _api_type("Workbook", "Loads, creates, calculates, and saves workbooks."),
        ),
        format_extraction=AsposeOrgFormatExtractionV1(
            status="unavailable",
            detail="fixture format records are repository-bound",
        ),
        formats=(
            DotnetFormatEvidenceV1(
                evidence_id="format-xlsx",
                format="XLSX",
                direction="both",
                source_path="src/Product/Workbook.cs",
                source_line=20,
                source_sha256="e" * 64,
            ),
        ),
        readiness="partial",
    )


def test_dotnet_truth_uses_detailed_public_api_and_directional_formats() -> None:
    candidates = dotnet_repository_truth_candidates(
        _catalog(),
        observed_at="2026-08-04T00:00:00+00:00",
    )
    by_field = {candidate.field: candidate for candidate in candidates}

    assert by_field["product.audience"].value == ["Developers using .NET."]
    assert by_field["product.capabilities"].value == [
        "Loads, creates, calculates, and saves workbooks.",
        "Provides access to worksheet cells, rows, and columns.",
    ]
    assert by_field["product.formats"].value == [
        "Input format: XLSX",
        "Output format: XLSX",
    ]
    assert "product.limitations" not in by_field
    assert all(candidate.verification_state == "verified" for candidate in candidates)
    assert all(candidate.source.source_revision == "b" * 40 for candidate in candidates)


def test_dotnet_truth_falls_back_to_public_type_identity_without_doc_claims() -> None:
    catalog = _catalog().model_copy(
        update={"api_types": (_api_type("Workbook", "Represents workbook."),)}
    )

    candidates = dotnet_repository_truth_candidates(catalog, observed_at=None)
    capability = next(item for item in candidates if item.field == "product.capabilities")

    assert capability.value == ["Represents workbook."]
    assert "src/Product/Workbook.cs" in capability.source.location
