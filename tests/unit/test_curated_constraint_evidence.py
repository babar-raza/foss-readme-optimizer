"""Verify source-derived curated constraint evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.facts.curated_constraint_evidence import source_limitations


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _repository(root: Path, *, registrations: str | None = None) -> None:
    _write(root, "README.md", "Everything is implemented, including COLLADA.\n")
    _write(
        root,
        "src/pkg/Scene.py",
        "class Scene:\n"
        "    def save(self, io_service):\n"
        "        return io_service.create_exporter('collada')\n"
        "    def render(self):\n"
        "        raise NotImplementedError('render is not implemented')\n"
        "    def helper(self):\n"
        "        raise NotImplementedError('helper is not implemented')\n",
    )
    _write(
        root,
        "src/pkg/entities/Mesh.py",
        "class Mesh:\n"
        + "".join(
            f"    def {name}(self):\n"
            f"        raise NotImplementedError('{name} is not implemented')\n"
            for name in ("do_boolean", "union", "difference", "intersect")
        ),
    )
    _write(
        root,
        "src/pkg/entities/NurbsCurve.py",
        "class NurbsCurve:\n"
        "    def evaluate(self):\n"
        "        raise NotImplementedError('NURBS curve evaluation is not implemented')\n",
    )
    _write(
        root,
        "src/pkg/entities/NurbsSurface.py",
        "class NurbsSurface:\n"
        "    def to_mesh(self):\n"
        "        raise NotImplementedError('NURBS surface conversion is not implemented')\n",
    )
    _write(
        root,
        "src/pkg/render/Renderer.py",
        "class Renderer:\n"
        "    def render(self):\n"
        "        raise NotImplementedError('Renderer.render is not implemented')\n",
    )
    _write(
        root,
        "src/pkg/formats/Exporter.py",
        "class Exporter:\n"
        "    def supports_format(self, value):\n"
        "        raise NotImplementedError('format check is not implemented')\n",
    )
    _write(
        root,
        "src/pkg/formats/IOService.py",
        "class IOService:\n"
        "    def create_exporter(self, value):\n"
        "        for exporter in self._exporters:\n"
        "            if exporter.supports_format(value):\n"
        "                return exporter\n",
    )
    _write(
        root,
        "src/pkg/formats/__init__.py",
        registrations or "io.register_plugin(FbxPlugin())\nio.register_plugin(ColladaPlugin())\n",
    )
    _write(
        root,
        "src/pkg/formats/fbx/FbxExporter.py",
        "class FbxExporter(Exporter):\n"
        "    def save(self):\n"
        "        raise NotImplementedError('FBX export is not implemented')\n",
    )
    _write(
        root,
        "src/pkg/formats/fbx/FbxPlugin.py",
        "class FbxPlugin:\n    def create(self):\n        return FbxExporter()\n",
    )
    _write(
        root,
        "src/pkg/formats/collada/ColladaExporter.py",
        "class ColladaExporter(Exporter):\n"
        "    def supports_format(self, value):\n"
        "        return value == 'collada'\n"
        "    def export(self):\n"
        "        return True\n",
    )
    _write(
        root,
        "src/pkg/formats/collada/ColladaPlugin.py",
        "class ColladaPlugin:\n    def create(self):\n        return ColladaExporter()\n",
    )


def test_source_limitations_groups_high_signal_constraints_with_exact_citations(
    tmp_path: Path,
) -> None:
    _repository(tmp_path)

    result = source_limitations(tmp_path)

    assert result is not None
    limitations, locations = result
    assert {item["kind"] for item in limitations} == {
        "rendering_unimplemented",
        "mesh_boolean_unimplemented",
        "nurbs_evaluation_unimplemented",
        "fbx_export_unimplemented",
        "collada_dispatch_blocked",
    }
    assert "README.md" not in locations
    assert "helper is not implemented" not in {item["statement"] for item in limitations}
    for item in limitations:
        assert item["evidence"]
        for evidence in item["evidence"]:
            path = tmp_path / evidence["path"]
            assert path.is_file()
            assert evidence["line"] > 0
            assert evidence["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_collada_dispatch_requires_registration_order(tmp_path: Path) -> None:
    _repository(
        tmp_path,
        registrations="io.register_plugin(ColladaPlugin())\nio.register_plugin(FbxPlugin())\n",
    )

    result = source_limitations(tmp_path)

    assert result is not None
    limitations, _ = result
    assert "collada_dispatch_blocked" not in {item["kind"] for item in limitations}


def test_readme_prose_cannot_create_limitations(tmp_path: Path) -> None:
    _write(tmp_path, "README.md", "FBX export is not implemented.\n")
    _write(tmp_path, "src/pkg/module.py", "VALUE = 'implemented'\n")

    assert source_limitations(tmp_path) is None
