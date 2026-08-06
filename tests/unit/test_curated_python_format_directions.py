"""Prove repository-source Python format-direction collection."""

from pathlib import Path

from readme_agent.facts.curated_python_evidence import python_source_format_directions


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_collects_import_and_export_implementations_with_bounded_details(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "package/ObjImporter.py",
        """
class ObjImporter:
    def supports_format(self, file_format):
        return isinstance(file_format, ObjFormat)

    def import_scene(self, scene, stream, options):
        return self._read(stream)
""",
    )
    _write(
        tmp_path,
        "package/ObjExporter.py",
        """
class ObjExporter:
    def supports_format(self, file_format):
        return isinstance(file_format, ObjFormat)

    def export(self, scene, stream, options):
        return self._write(scene, stream)
""",
    )

    result = python_source_format_directions(tmp_path)

    assert result is not None
    value, locations = result
    assert locations == ["package/ObjExporter.py", "package/ObjImporter.py"]
    assert [(item["format"], item["direction"]) for item in value["directions"]] == [
        ("OBJ", "output"),
        ("OBJ", "input"),
    ]
    imported = next(item for item in value["directions"] if item["direction"] == "input")
    assert imported["material_library_support"] is False


def test_ignores_abstract_or_unimplemented_direction(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "package/StlExporter.py",
        """
class StlExporter:
    def supports_format(self, file_format):
        return isinstance(file_format, StlFormat)

    def export(self, scene, stream, options):
        raise NotImplementedError
""",
    )

    assert python_source_format_directions(tmp_path) is None
