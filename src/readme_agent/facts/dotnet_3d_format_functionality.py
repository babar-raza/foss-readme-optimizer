"""Corroborate .NET 3D format directions from immutable repository source and tests."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_FILE_FORMAT = "src/main/Aspose.ThreeD/Aspose/ThreeD/FileFormat.cs"
_SCENE = "src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs"
_FILE_IO_TESTS = "src/test/Aspose.ThreeD.Tests/FileIOTests.cs"


@dataclass(frozen=True)
class DotNet3DFormatSourceV1:
    """Content identity of the exact repository sources used for corroboration."""

    source_revision: str
    source_files: dict[str, str]

    def canonical_sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.source_revision.encode("ascii"))
        digest.update(b"\0")
        for path, checksum in sorted(self.source_files.items()):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(checksum.encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()


@dataclass(frozen=True)
class _FormatSpec:
    aliases: tuple[str, ...]
    class_name: str
    load_options: str
    save_options: str


_SPECS = (
    _FormatSpec(("obj", "wavefrontobj"), "ObjFormat", "ObjLoadOptions", "ObjSaveOptions"),
    _FormatSpec(("stl",), "StlFormat", "StlLoadOptions", "StlSaveOptions"),
    _FormatSpec(("gltf", "glb", "gltf2"), "GltfFormat", "GltfLoadOptions", "GltfSaveOptions"),
    _FormatSpec(("fbx",), "FbxFormat", "FbxLoadOptions", "FbxSaveOptions"),
    _FormatSpec(
        ("3mf", "threemf", "microsoft3mf"),
        "Microsoft3MFFormat",
        "BasicLoadOptions",
        "Microsoft3MFSaveOptions",
    ),
    _FormatSpec(("collada", "dae"), "ColladaFormat", "BasicLoadOptions", "ColladaSaveOptions"),
    _FormatSpec(("ply",), "PlyFormat", "PlyLoadOptions", "PlySaveOptions"),
)


def dotnet_3d_format_source(
    repository_root: Path, *, source_revision: str
) -> DotNet3DFormatSourceV1 | None:
    """Return the revision/path/hash receipt only for an exact clean source tree."""

    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return None
    files: dict[str, str] = {}
    for relative_path in (_FILE_FORMAT, _SCENE, _FILE_IO_TESTS):
        path = root / relative_path
        try:
            payload = path.read_bytes()
        except OSError:
            return None
        files[relative_path] = hashlib.sha256(payload).hexdigest()
    if not _revision_matches(root, source_revision):
        return None
    return DotNet3DFormatSourceV1(source_revision=source_revision, source_files=files)


def corroborate_dotnet_3d_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Set functional true only when declaration, public API, and native tests agree."""

    root = repository_root.resolve()
    source = dotnet_3d_format_source(root, source_revision=source_revision)
    if source is None:
        return formats
    file_format = _read(root / _FILE_FORMAT)
    scene = _read(root / _SCENE)
    tests = _read(root / _FILE_IO_TESTS)
    if file_format is None or scene is None or tests is None:
        return formats

    result: list[AsposeOrgFormatEvidenceV1] = []
    for evidence in formats:
        if evidence.functional is not None or evidence.direction not in {"import", "export"}:
            result.append(evidence)
            continue
        spec = _spec_for(evidence.format)
        evidence_path = root / evidence.file
        if spec is None or not evidence_path.is_file():
            result.append(evidence)
            continue
        if _direction_is_corroborated(spec, evidence.direction, file_format, scene, tests):
            result.append(evidence.model_copy(update={"functional": True}))
        else:
            result.append(evidence)
    if dotnet_3d_format_source(root, source_revision=source_revision) != source:
        return formats
    return result


def _revision_matches(root: Path, expected: str) -> bool:
    if _REVISION.fullmatch(expected) is None or not (root / ".git").exists():
        return False
    try:
        revision = subprocess.run(
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
    return revision.stdout.strip().casefold() == expected.casefold() and not status.stdout.strip()


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _spec_for(format_name: str) -> _FormatSpec | None:
    normalized = "".join(character for character in format_name.casefold() if character.isalnum())
    return next((spec for spec in _SPECS if normalized in spec.aliases), None)


def _direction_is_corroborated(
    spec: _FormatSpec,
    direction: str,
    file_format: str,
    scene: str,
    tests: str,
) -> bool:
    capabilities = _declared_capabilities(file_format, spec.class_name)
    if capabilities is None:
        return False
    can_export, can_import = capabilities
    if direction == "import":
        return (
            can_import
            and _scene_supports_import(scene)
            and _tests_direction(tests, spec, direction)
        )
    return can_export and _scene_supports_export(scene) and _tests_direction(tests, spec, direction)


def _declared_capabilities(source: str, class_name: str) -> tuple[bool, bool] | None:
    class_match = re.search(
        rf"\bclass\s+{re.escape(class_name)}\s*:\s*FileFormat\b(?P<body>.*?)(?=\n\s*(?:internal|public|private|protected)\s+class\s+|\Z)",
        source,
        flags=re.DOTALL,
    )
    if class_match is None:
        return None
    constructor = re.search(
        rf"\b{re.escape(class_name)}\s*\(\s*\)\s*:\s*base\(.*?\b(true|false)\s*,\s*(true|false)\s*,\s*FileContentType\.",
        class_match.group("body"),
        flags=re.DOTALL | re.IGNORECASE,
    )
    if constructor is None:
        return None
    return constructor.group(1).casefold() == "true", constructor.group(2).casefold() == "true"


def _scene_supports_import(source: str) -> bool:
    return all(
        token in source
        for token in ("public void Open(", "CreateImporter(format)", "importer.Import(")
    )


def _scene_supports_export(source: str) -> bool:
    return all(
        token in source
        for token in ("public void Save(", "CreateExporter(format)", "exporter.Export(")
    )


def _tests_direction(source: str, spec: _FormatSpec, direction: str) -> bool:
    option = spec.load_options if direction == "import" else spec.save_options
    call = "scene.Open(" if direction == "import" else "scene.Save("
    return any(option in block and call in block for block in source.split("[Fact]"))
