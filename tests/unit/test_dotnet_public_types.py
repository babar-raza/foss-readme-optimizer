"""Tests for source-derived .NET public type and namespace resolution."""

from pathlib import Path

from readme_agent.ecosystems.dotnet_public_types import (
    normalize_dotnet_public_type_usings,
    public_dotnet_type_index,
)


def _write_type(root: Path, relative: str, namespace: str, name: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"namespace {namespace}\n{{\n    public class {name} {{}}\n}}\n",
        encoding="utf-8",
    )


def test_indexes_exact_public_namespaces_and_ignores_test_sources(tmp_path: Path) -> None:
    _write_type(tmp_path, "src/Scene.cs", "Aspose.ThreeD", "Scene")
    _write_type(tmp_path, "src/Entities/Box.cs", "Aspose.ThreeD.Entities", "Box")
    _write_type(tmp_path, "tests/Box.cs", "Aspose.Tests", "Box")

    index = public_dotnet_type_index(tmp_path)

    assert index["Scene"].qualified_name == "Aspose.ThreeD.Scene"
    assert index["Box"].qualified_name == "Aspose.ThreeD.Entities.Box"


def test_adds_only_missing_namespace_for_unqualified_public_type(tmp_path: Path) -> None:
    _write_type(tmp_path, "src/Scene.cs", "Aspose.ThreeD", "Scene")
    _write_type(tmp_path, "src/Entities/Box.cs", "Aspose.ThreeD.Entities", "Box")
    source = "using Aspose.ThreeD;\nvar scene = new Scene();\nvar box = new Box(1, 1, 1);\n"

    normalized = normalize_dotnet_public_type_usings(tmp_path, source)

    assert normalized == "using Aspose.ThreeD.Entities;\n" + source


def test_does_not_infer_types_from_strings_or_qualified_names(tmp_path: Path) -> None:
    _write_type(tmp_path, "src/Entities/Box.cs", "Aspose.ThreeD.Entities", "Box")
    source = 'var label = "Box";\nvar box = new Aspose.ThreeD.Entities.Box(1, 1, 1);\n'

    assert normalize_dotnet_public_type_usings(tmp_path, source) == source


def test_ambiguous_public_type_is_not_auto_imported(tmp_path: Path) -> None:
    _write_type(tmp_path, "src/One/Box.cs", "Aspose.One", "Box")
    _write_type(tmp_path, "src/Two/Box.cs", "Aspose.Two", "Box")

    assert normalize_dotnet_public_type_usings(tmp_path, "var box = new Box();\n") == (
        "var box = new Box();\n"
    )
