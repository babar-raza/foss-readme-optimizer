"""Tests for bounded .NET evidence-to-fact selection."""

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatExtractionV1
from readme_agent.facts.dotnet_repository_evidence_schema import (
    AsposeOrgDotnetExtractionV1,
    DotnetApiTypeEvidenceV1,
    DotnetFormatEvidenceV1,
    DotnetRepositoryEvidenceCatalogV1,
)
from readme_agent.facts.dotnet_truth_selection import dotnet_repository_truth_candidates


def _api_type(
    name: str,
    summary: str,
    *,
    source_path: str | None = None,
) -> DotnetApiTypeEvidenceV1:
    return DotnetApiTypeEvidenceV1(
        evidence_id=f"api-{name.casefold()}",
        origin="local_lexer",
        name=name,
        qualified_name=f"Aspose.Cells_FOSS.{name}",
        kind="class",
        summary=summary,
        source_path=source_path or f"src/Product/{name}.cs",
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
        "Load, create, calculate, and save workbooks.",
        "Access worksheet cells, rows, and columns.",
    ]
    assert by_field["product.formats"].value == [
        "Input format: XLSX",
        "Output format: XLSX",
    ]
    assert "product.limitations" not in by_field
    assert all(candidate.verification_state == "verified" for candidate in candidates)
    assert all(candidate.source.source_revision == "b" * 40 for candidate in candidates)


def test_dotnet_truth_does_not_promote_type_identity_without_visitor_capability() -> None:
    catalog = _catalog().model_copy(
        update={"api_types": (_api_type("Workbook", "Represents workbook."),)}
    )

    candidates = dotnet_repository_truth_candidates(catalog, observed_at=None)
    assert all(item.field != "product.capabilities" for item in candidates)


def test_dotnet_truth_distills_xml_docs_and_rejects_internal_types() -> None:
    catalog = _catalog().model_copy(
        update={
            "api_types": (
                _api_type(
                    "Images",
                    "Provides static factory methods for creating Image instances.",
                ),
                _api_type("FontUtilities", "Provides font management utilities for a document."),
                _api_type("NotesSlideManager", "Manages notes slide operations for a slide."),
                _api_type(
                    "CellFormat",
                    "Represents the formatting properties of a table cell, providing access to "
                    "fill formatting and border line formats.",
                ),
                _api_type(
                    "OpcPackage",
                    "Manages an Open Packaging Conventions (OPC) package.",
                    source_path="src/Product/Internal/Opc/OpcPackage.cs",
                ),
                _api_type(
                    "DocumentReaderPluginLoadException",
                    "Thrown during document load, when a plugin cannot be loaded.",
                ),
            )
        }
    )

    candidates = dotnet_repository_truth_candidates(catalog, observed_at=None)
    capability = next(item for item in candidates if item.field == "product.capabilities")

    assert set(capability.value) == {
        "Access table cell formatting properties.",
        "Manage font resources.",
        "Create Image instances.",
        "Manage notes slide operations for a slide.",
    }
    assert "Internal/Opc" not in capability.source.location


def test_dotnet_truth_turns_mapi_reader_writer_evidence_into_public_action() -> None:
    catalog = _catalog().model_copy(
        update={
            "api_types": (
                _api_type(
                    "CommonMessagePropertyId",
                    "Common MAPI property identifiers used by the MSG reader and writer for core "
                    "message semantics, body fields, transport headers, and attachments.",
                ),
            )
        }
    )

    candidates = dotnet_repository_truth_candidates(catalog, observed_at=None)
    capability = next(item for item in candidates if item.field == "product.capabilities")

    assert capability.value == ["Read and write MSG message properties."]


def test_dotnet_truth_distills_format_and_transform_actions_without_xml_doc_scaffolding() -> None:
    catalog = _catalog().model_copy(
        update={
            "api_types": (
                _api_type(
                    "PdfBookmarkEditor",
                    "Facade for bookmark manipulation: create, extract, delete bookmarks.",
                ),
                _api_type(
                    "Workbook",
                    "Represents the root spreadsheet object used to create, load, modify, and "
                    "save an XLSX workbook.",
                ),
                _api_type(
                    "Transform",
                    "A transform contains information that allow access to object's "
                    "translate/scale/rotation or transform matrix at minimum cost.",
                ),
                _api_type(
                    "DocumentDevice",
                    "Default DocumentDevice implementation that saves the document as a PDF "
                    "(Document.Save round-trip).",
                ),
            )
        }
    )

    candidates = dotnet_repository_truth_candidates(catalog, observed_at=None)
    capability = next(item for item in candidates if item.field == "product.capabilities")

    assert set(capability.value) == {
        "Save the document as a PDF.",
        "Transform objects with translation, scaling, rotation, and matrices.",
        "Create, extract, and delete bookmarks.",
        "Create, load, modify, and save an XLSX workbook.",
    }
    assert all("Facade for" not in item for item in capability.value)
