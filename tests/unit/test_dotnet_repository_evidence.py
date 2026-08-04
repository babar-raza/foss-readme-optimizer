"""Tests for current-revision .NET repository evidence catalogs."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.aspose_org_format_contract import (
    ASPOSE_ORG_FORMATS_RELATIVE_PATH,
    AsposeOrgFormatEvidenceV1,
    AsposeOrgFormatExtractionV1,
    canonical_dependency_sha256,
)
from readme_agent.facts.dotnet_repository_evidence import build_dotnet_repository_evidence
from readme_agent.facts.dotnet_repository_evidence_schema import (
    AsposeOrgDotnetExtractionV1,
)
from readme_agent.facts.root_role_schema import (
    PackageRootRoleInventoryV1,
    PackageRootRoleV1,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(root: Path) -> RepositorySnapshotV1:
    readme = root / "README.md"
    digest = hashlib.sha256(readme.read_bytes()).hexdigest()
    return RepositorySnapshotV1(
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        readme_path="README.md",
        readme_sha256=digest,
        inventory_sha256="b" * 64,
        captured_at="2026-08-04T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/repo.git",
            git_tree_sha256="b" * 64,
        ),
    )


def _roles(manifest: str = "src/Product/Product.csproj") -> PackageRootRoleInventoryV1:
    return PackageRootRoleInventoryV1(
        org_repo="aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
        source_revision="a" * 40,
        selection_state="selected",
        selected_product_manifest_path=manifest,
        selection_rationale=["the product assembly owns the Aspose.Cells namespace"],
        roots=[
            PackageRootRoleV1(
                path=str(Path(manifest).parent).replace("\\", "/"),
                ecosystem="dotnet",
                manifest_path=manifest,
                role="product",
                confidence=1.0,
                rationale=["source-declared product identity"],
            )
        ],
    )


def _format_result() -> AsposeOrgFormatExtractionV1:
    files = {ASPOSE_ORG_FORMATS_RELATIVE_PATH: "c" * 64}
    return AsposeOrgFormatExtractionV1(
        status="available",
        formats=[
            AsposeOrgFormatEvidenceV1(
                format="XLSX",
                direction="both",
                file="src/Product/Workbook.cs",
                line=4,
                functional=True,
            ),
            AsposeOrgFormatEvidenceV1(
                format="XLS",
                direction="detect",
                file="src/Product/Workbook.cs",
                line=4,
                functional=True,
            ),
            AsposeOrgFormatEvidenceV1(
                format="CSV",
                direction="export",
                file="src/Product/Workbook.cs",
                line=4,
                functional=False,
            ),
        ],
        extractor_revision="d" * 40,
        extractor_sha256="c" * 64,
        dependency_sha256=canonical_dependency_sha256(files),
        dependency_files=files,
        detail="fixture extraction",
    )


def _write_repository(root: Path) -> None:
    (root / "src" / "Product").mkdir(parents=True)
    (root / "src" / "Product" / "Product.csproj").write_text("<Project />", encoding="utf-8")
    (root / "src" / "Product" / "Workbook.cs").write_text(
        "namespace Aspose.Cells;\npublic class Workbook\n{\n"
        "  public void Save() { throw new NotSupportedException(); }\n}\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Cells\n\n```csharp\nvar workbook = new Workbook();\nworkbook.Save();\n```\n",
        encoding="utf-8",
    )


def test_catalog_falls_back_to_local_types_and_binds_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repository(tmp_path)
    monkeypatch.setattr(
        "readme_agent.facts.dotnet_repository_evidence.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    result = build_dotnet_repository_evidence(
        _snapshot(tmp_path),
        _roles(),
        family="cells",
        api_extractor=lambda *_args, **_kwargs: AsposeOrgDotnetExtractionV1(
            status="unavailable",
            completeness="unavailable",
            detail="sibling unavailable",
        ),
        format_extractor=lambda *_args, **_kwargs: _format_result(),
    )

    assert result.readiness == "ready"
    assert [(item.qualified_name, item.origin) for item in result.api_types] == [
        ("Aspose.Cells.Workbook", "local_lexer")
    ]
    assert [(item.format, item.direction) for item in result.formats] == [("XLSX", "both")]
    assert len(result.examples) == 1
    assert (
        result.examples[0].code_sha256
        == hashlib.sha256(result.examples[0].code.encode("utf-8")).hexdigest()
    )
    assert [(item.kind, item.source_line) for item in result.boundaries] == [("not_supported", 4)]
    assert result.canonical_hash() == result.canonical_hash()
    assert "sibling unavailable" in result.observations[0]


def test_catalog_rejects_root_roles_from_another_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repository(tmp_path)
    monkeypatch.setattr(
        "readme_agent.facts.dotnet_repository_evidence.verify_repository_snapshot",
        lambda _snapshot: None,
    )
    roles = _roles().model_copy(update={"source_revision": "e" * 40})

    with pytest.raises(ValueError, match="do not match"):
        build_dotnet_repository_evidence(_snapshot(tmp_path), roles, family="cells")


def test_catalog_supports_product_root_outside_src(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "Words" / "Code").mkdir(parents=True)
    (tmp_path / "Words" / "Code" / "Words.csproj").write_text("<Project />", encoding="utf-8")
    (tmp_path / "Words" / "Code" / "Document.cs").write_text(
        "namespace Aspose.Words;\npublic class Document {}\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# Words\n", encoding="utf-8")
    monkeypatch.setattr(
        "readme_agent.facts.dotnet_repository_evidence.verify_repository_snapshot",
        lambda _snapshot: None,
    )
    roles = _roles("Words/Code/Words.csproj")

    result = build_dotnet_repository_evidence(
        _snapshot(tmp_path),
        roles,
        family="words",
        api_extractor=lambda *_args, **_kwargs: AsposeOrgDotnetExtractionV1(
            status="unavailable", completeness="unavailable", detail="not configured"
        ),
        format_extractor=lambda *_args, **_kwargs: AsposeOrgFormatExtractionV1(
            status="unavailable", detail="not configured"
        ),
    )

    assert result.selected_product_root == "Words/Code"
    assert result.readiness == "partial"
    assert [item.qualified_name for item in result.api_types] == ["Aspose.Words.Document"]
