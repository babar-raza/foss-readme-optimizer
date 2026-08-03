"""Tests for immutable .NET 3D format-direction corroboration."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.dotnet_3d_format_functionality import (
    corroborate_dotnet_3d_format_directions,
    dotnet_3d_format_source,
)


def test_corroborates_only_declared_tested_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        _record("Obj", "import", "ObjReader.cs"),
        _record("Obj", "export", "ObjWriter.cs"),
        _record("Stl", "import", "StlReader.cs"),
        _record("Stl", "export", "StlWriter.cs"),
    ]

    result = corroborate_dotnet_3d_format_directions(
        tmp_path, source_revision=revision, formats=records
    )

    assert [item.functional for item in result] == [True, True, True, None]
    source = dotnet_3d_format_source(tmp_path, source_revision=revision)
    assert source is not None
    assert source.source_revision == revision
    assert set(source.source_files) == {
        "src/main/Aspose.ThreeD/Aspose/ThreeD/FileFormat.cs",
        "src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs",
        "src/test/Aspose.ThreeD.Tests/FileIOTests.cs",
    }
    assert len(source.canonical_sha256()) == 64


def test_rejects_wrong_revision_dirty_tree_and_missing_native_record(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        _record("Obj", "import", "ObjReader.cs"),
        _record("Obj", "import", "MissingReader.cs"),
    ]

    wrong = corroborate_dotnet_3d_format_directions(
        tmp_path, source_revision="0" * 40, formats=records
    )
    (tmp_path / "src/test/Aspose.ThreeD.Tests/FileIOTests.cs").write_text(
        "// changed\n", encoding="utf-8"
    )
    dirty = corroborate_dotnet_3d_format_directions(
        tmp_path, source_revision=revision, formats=records
    )

    assert [item.functional for item in wrong] == [None, None]
    assert [item.functional for item in dirty] == [None, None]


def _record(name: str, direction: str, source: str) -> AsposeOrgFormatEvidenceV1:
    return AsposeOrgFormatEvidenceV1(
        format=name,
        direction=direction,
        file=f"src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/{source}",
        line=1,
    )


def _seed_repository(root: Path) -> str:
    _write(
        root / "src/main/Aspose.ThreeD/Aspose/ThreeD/FileFormat.cs",
        """
internal class ObjFormat : FileFormat
{
    public ObjFormat() : base(
        ".obj", new[] { ".obj" }, new Version(1, 0), true, true,
        FileContentType.ASCII, new FileFormatType(".obj")) { }
}
internal class StlFormat : FileFormat
{
    public StlFormat() : base(
        ".stl", new[] { ".stl" }, new Version(1, 0), false, true,
        FileContentType.Binary, new FileFormatType(".stl")) { }
}
""".lstrip(),
    )
    _write(
        root / "src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs",
        """
public class Scene {
    public void Open(Stream stream) {
        var importer = Formats.IOService.Instance.CreateImporter(format);
        importer.Import(stream, options);
    }
    public void Save(Stream stream) {
        var exporter = Formats.IOService.Instance.CreateExporter(format);
        exporter.Export(this, stream, options);
    }
}
""".lstrip(),
    )
    _write(
        root / "src/test/Aspose.ThreeD.Tests/FileIOTests.cs",
        """
[Fact]
public void LoadObj() { var options = new ObjLoadOptions(); scene.Open(stream); }
[Fact]
public void SaveObj() { var options = new ObjSaveOptions(); scene.Save(stream); }
[Fact]
public void LoadStl() { var options = new StlLoadOptions(); scene.Open(stream); }
""".lstrip(),
    )
    for source in ("ObjReader.cs", "ObjWriter.cs", "StlReader.cs", "StlWriter.cs"):
        _write(root / f"src/main/Aspose.ThreeD/Aspose/ThreeD/Formats/{source}", "class X {}\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Readme Agent Test",
            "-c",
            "user.email=readme-agent@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=root,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
