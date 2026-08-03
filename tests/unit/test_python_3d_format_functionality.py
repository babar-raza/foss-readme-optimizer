"""Tests for bounded Python 3D format-direction corroboration."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_3d_format_functionality import (
    corroborate_python_3d_format_directions,
)


def test_corroborates_supported_directions_only(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        _record("Obj", "import", "obj", "Obj"),
        _record("Obj", "export", "obj", "Obj"),
        _record("Gltf", "import", "gltf", "Gltf"),
        _record("Gltf", "export", "gltf", "Gltf"),
        _record("Stl", "import", "stl", "Stl"),
        _record("Stl", "export", "stl", "Stl"),
        _record("ThreeMf", "import", "threemf", "ThreeMf"),
        _record("MICROSOFT_3MF", "export", "threemf", "ThreeMf"),
    ]

    result = corroborate_python_3d_format_directions(
        tmp_path, source_revision=revision, formats=records
    )

    assert [item.functional for item in result] == [True, None, True, True, True, True, True, True]


def test_rejects_wrong_revision_enum_only_and_nonimplementation_record(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        _record("Gltf", "import", "gltf", "Gltf"),
        AsposeOrgFormatEvidenceV1(
            format="GLTF", direction="enum_only", file="aspose/threed/FileFormat.py", line=1
        ),
        AsposeOrgFormatEvidenceV1(
            format="Gltf",
            direction="export",
            file="aspose/threed/formats/GltfSaveOptions.py",
            line=1,
        ),
    ]

    wrong_revision = corroborate_python_3d_format_directions(
        tmp_path, source_revision="0" * 40, formats=records
    )
    correct_revision = corroborate_python_3d_format_directions(
        tmp_path, source_revision=revision, formats=records
    )

    assert [item.functional for item in wrong_revision] == [None, None, None]
    assert [item.functional for item in correct_revision[:3]] == [True, None, None]
    assert any(
        item.format == "Gltf" and item.direction == "export" and item.functional is True
        for item in correct_revision[3:]
    )


def test_rejects_missing_matching_test(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted_test="gltf_export")
    record = _record("Gltf", "export", "gltf", "Gltf")

    result = corroborate_python_3d_format_directions(
        tmp_path, source_revision=revision, formats=[record]
    )

    assert result[0].functional is None


def test_rejects_missing_concrete_implementation(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted_source="stl_import")
    record = _record("Stl", "import", "stl", "Stl")

    result = corroborate_python_3d_format_directions(
        tmp_path, source_revision=revision, formats=[record]
    )

    assert result[0].functional is None


def test_rejects_dirty_tree_even_when_head_matches(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    record = _record("Stl", "import", "stl", "Stl")
    (tmp_path / "tests/test_stl_import.py").write_text("# evidence removed\n", encoding="utf-8")

    result = corroborate_python_3d_format_directions(
        tmp_path, source_revision=revision, formats=[record]
    )

    assert result[0].functional is None


def test_adds_missing_functional_records_from_source_and_tests(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_3d_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[
            AsposeOrgFormatEvidenceV1(
                format="MICROSOFT_3MF",
                direction="detect",
                file="aspose/threed/FileFormat.py",
                line=1,
            )
        ],
    )

    functional = {(item.format, item.direction) for item in result if item.functional is True}
    assert ("ThreeMf", "import") in functional
    assert ("ThreeMf", "export") in functional
    assert ("Obj", "import") in functional
    assert ("Obj", "export") not in functional


def _record(
    format_name: str, direction: str, package: str, prefix: str
) -> AsposeOrgFormatEvidenceV1:
    role = "Importer" if direction == "import" else "Exporter"
    return AsposeOrgFormatEvidenceV1(
        format=format_name,
        direction=direction,
        file=f"aspose/threed/formats/{package}/{prefix}{role}.py",
        line=1,
    )


def _seed_repository(
    root: Path, *, omitted_test: str | None = None, omitted_source: str | None = None
) -> str:
    _write(
        root / "aspose/threed/FileFormat.py",
        """
class FileFormat:
    @staticmethod
    def get_format_by_extension(extension_name):
        if extension_name == 'obj':
            from .formats.obj.ObjFormat import ObjFormat
            return ObjFormat()
        if extension_name == 'gltf':
            from .formats.gltf.GltfFormat import GltfFormat
            return GltfFormat()
        if extension_name == 'stl':
            from .formats.stl.StlFormat import StlFormat
            return StlFormat()
        if extension_name == '3mf':
            from .formats.threemf.ThreeMfFormat import ThreeMfFormat
            return ThreeMfFormat()
        return None
""".lstrip(),
    )
    _write(
        root / "aspose/threed/Scene.py",
        """
class Scene:
    def open(self, file_name):
        detected = FileFormat.get_format_by_extension(file_name)
        importer = io_service.create_importer(detected)
        importer.import_scene(self, stream, options)

    def save(self, file_name):
        detected = FileFormat.get_format_by_extension(file_name)
        exporter = io_service.create_exporter(detected)
        exporter.export(self, stream, options)
""".lstrip(),
    )
    for package, prefix, can_export in (
        ("obj", "Obj", False),
        ("gltf", "Gltf", True),
        ("stl", "Stl", True),
        ("threemf", "ThreeMf", True),
    ):
        _write(
            root / f"aspose/threed/formats/{package}/{prefix}Format.py",
            f"""
class {prefix}Format:
    @property
    def can_import(self):
        return True

    @property
    def can_export(self):
        return {can_export!r}
""".lstrip(),
        )
        if omitted_source != f"{package}_import":
            _write(
                root / f"aspose/threed/formats/{package}/{prefix}Importer.py",
                f"class {prefix}Importer:\n"
                "    def import_scene(self, scene, stream, options):\n"
                "        return scene\n",
            )
        if omitted_source != f"{package}_export":
            _write(
                root / f"aspose/threed/formats/{package}/{prefix}Exporter.py",
                f"class {prefix}Exporter:\n"
                "    def export(self, scene, stream, options):\n"
                "        return stream\n",
            )
        for direction, call in (("import", "import_scene"), ("export", "export")):
            if omitted_test == f"{package}_{direction}":
                continue
            _write(
                root / f"tests/test_{package}_{direction}.py",
                f"def test_{package}_{direction}():\n"
                f"    {prefix}{'Importer' if direction == 'import' else 'Exporter'}().{call}()\n",
            )
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
