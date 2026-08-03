"""Corroborate bounded Python 3D format directions from repository source and tests."""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1


@dataclass(frozen=True)
class _FormatSpec:
    aliases: tuple[str, ...]
    extension: str
    package: str
    class_prefix: str

    @property
    def format_source(self) -> str:
        return f"aspose/threed/formats/{self.package}/{self.class_prefix}Format.py"

    def implementation_source(self, direction: str) -> str:
        role = "Importer" if direction == "import" else "Exporter"
        return f"aspose/threed/formats/{self.package}/{self.class_prefix}{role}.py"


_SPECS = (
    _FormatSpec(("obj", "wavefrontobj"), "obj", "obj", "Obj"),
    _FormatSpec(("gltf", "gltf2", "glb"), "gltf", "gltf", "Gltf"),
    _FormatSpec(("stl", "stlascii", "stlbinary"), "stl", "stl", "Stl"),
    _FormatSpec(("3mf", "threemf", "microsoft3mf"), "3mf", "threemf", "ThreeMf"),
)
_REVISION = re.compile(r"[0-9a-f]{40}")


def corroborate_python_3d_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Emit only source-and-test-proven 3D import/export records."""
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return formats

    file_format = _parse(root / "aspose/threed/FileFormat.py")
    scene = _parse(root / "aspose/threed/Scene.py")
    if file_format is None or scene is None:
        return formats

    results: list[AsposeOrgFormatEvidenceV1] = []
    for evidence in formats:
        if evidence.functional is not None or evidence.direction not in {"import", "export"}:
            results.append(evidence)
            continue
        spec = _spec_for(evidence.format)
        if spec is None or evidence.file != spec.implementation_source(evidence.direction):
            results.append(evidence)
            continue
        if _direction_is_corroborated(root, spec, evidence.direction, file_format, scene):
            results.append(evidence.model_copy(update={"functional": True}))
        else:
            results.append(evidence)
    for spec in _SPECS:
        for direction in ("import", "export"):
            if _has_functional_record(results, spec, direction):
                continue
            if not _direction_is_corroborated(root, spec, direction, file_format, scene):
                continue
            implementation = _parse(root / spec.implementation_source(direction))
            if implementation is None:
                continue
            role = "Importer" if direction == "import" else "Exporter"
            method = "import_scene" if direction == "import" else "export"
            owner_method = _class_method(implementation, f"{spec.class_prefix}{role}", method)
            if owner_method is None:
                continue
            results.append(
                AsposeOrgFormatEvidenceV1(
                    format=spec.class_prefix,
                    direction=direction,
                    file=spec.implementation_source(direction),
                    line=owner_method.lineno,
                    functional=True,
                )
            )
    return results


def _has_functional_record(
    formats: list[AsposeOrgFormatEvidenceV1], spec: _FormatSpec, direction: str
) -> bool:
    return any(
        _spec_for(item.format) == spec
        and item.direction in {direction, "both"}
        and item.functional is True
        for item in formats
    )


def _revision_matches(root: Path, expected: str) -> bool:
    if _REVISION.fullmatch(expected) is None or not (root / ".git").exists():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.stdout.strip().lower() == expected and not status.stdout.strip()


def _spec_for(format_name: str) -> _FormatSpec | None:
    normalized = _normalized(format_name)
    return next((spec for spec in _SPECS if normalized in spec.aliases), None)


def _direction_is_corroborated(
    root: Path,
    spec: _FormatSpec,
    direction: str,
    file_format: ast.Module,
    scene: ast.Module,
) -> bool:
    implementation = _parse(root / spec.implementation_source(direction))
    format_source = _parse(root / spec.format_source)
    if implementation is None or format_source is None:
        return False
    role = "Importer" if direction == "import" else "Exporter"
    implementation_method = "import_scene" if direction == "import" else "export"
    capability_method = "can_import" if direction == "import" else "can_export"
    scene_method = "open" if direction == "import" else "save"
    scene_calls = (
        {"get_format_by_extension", "create_importer", "import_scene"}
        if direction == "import"
        else {"get_format_by_extension", "create_exporter", "export"}
    )
    return all(
        (
            _class_method_has_body(
                implementation, f"{spec.class_prefix}{role}", implementation_method
            ),
            _property_returns_true(format_source, f"{spec.class_prefix}Format", capability_method),
            _file_format_maps_extension(file_format, spec),
            _method_calls(scene, "Scene", scene_method).issuperset(scene_calls),
            _has_matching_test(root, spec, direction),
        )
    )


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError):
        return None


def _class_method_has_body(module: ast.Module, class_name: str, method_name: str) -> bool:
    method = _class_method(module, class_name, method_name)
    return method is not None and any(not isinstance(node, ast.Pass) for node in method.body)


def _property_returns_true(module: ast.Module, class_name: str, method_name: str) -> bool:
    method = _class_method(module, class_name, method_name)
    return method is not None and any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Constant)
        and node.value.value is True
        for node in ast.walk(method)
    )


def _class_method(
    module: ast.Module, class_name: str, method_name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return next(
                (
                    item
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ),
                None,
            )
    return None


def _file_format_maps_extension(module: ast.Module, spec: _FormatSpec) -> bool:
    method = _class_method(module, "FileFormat", "get_format_by_extension")
    if method is None:
        return False
    class_name = f"{spec.class_prefix}Format"
    has_import = any(
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith(f"formats.{spec.package}.{class_name}")
        and any(alias.name == class_name for alias in node.names)
        for node in ast.walk(method)
    )
    has_call = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == class_name
        for node in ast.walk(method)
    )
    has_extension = any(
        isinstance(node, ast.Constant) and node.value == spec.extension for node in ast.walk(method)
    )
    return has_import and has_call and has_extension


def _method_calls(module: ast.Module, class_name: str, method_name: str) -> set[str]:
    method = _class_method(module, class_name, method_name)
    if method is None:
        return set()
    return {
        node.func.attr
        for node in ast.walk(method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def _has_matching_test(root: Path, spec: _FormatSpec, direction: str) -> bool:
    required_calls = {"open", "import_scene"} if direction == "import" else {"save", "export"}
    for path in sorted((root / "tests").glob("test_*.py")):
        module = _parse(path)
        if module is None or not _module_mentions_format(module, spec):
            continue
        calls = {
            node.func.attr
            for node in ast.walk(module)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        if calls & required_calls:
            return True
    return False


def _module_mentions_format(module: ast.Module, spec: _FormatSpec) -> bool:
    values: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Name):
            values.add(_normalized(node.id))
        elif isinstance(node, ast.Attribute):
            values.add(_normalized(node.attr))
        elif isinstance(node, ast.alias):
            values.add(_normalized(node.name))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(_normalized(node.value))
    return any(any(alias in value for alias in spec.aliases) for value in values)


def _normalized(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())
