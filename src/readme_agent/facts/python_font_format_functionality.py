"""Corroborate Python Font directions from public source and round-trip tests."""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_Direction = Literal["import", "export", "both", "detect", "enum_only", "none"]

_REVISION = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class _Proof:
    format_name: str
    direction: _Direction
    source_file: str
    class_name: str
    method_name: str
    test_file: str
    test_owner: str | None
    test_name: str
    required_calls: frozenset[str]
    required_names: frozenset[str]


_TTF = "src/aspose_font/ttf/font.py"
_CFF = "src/aspose_font/cff/font.py"
_TYPE1 = "src/aspose_font/type1/font.py"
_WOFF = "src/aspose_font/woff/woff1.py"
_WOFF2 = "src/aspose_font/woff/woff2.py"
_EOT = "src/aspose_font/eot/font.py"

_SERIALIZER_TESTS = "tests/test_serializer.py"
_LOADER_TESTS = "tests/test_loader.py"
_WOFF_TESTS = "tests/test_woff.py"

_PROOFS: tuple[_Proof, ...] = (
    _Proof(
        "TTF",
        "import",
        _TTF,
        "TtfFont",
        "_from_reader",
        _SERIALIZER_TESTS,
        None,
        "test_ttf_save_roundtrip",
        frozenset({"open", "save"}),
        frozenset({"FontLoader"}),
    ),
    _Proof(
        "TTF",
        "export",
        _TTF,
        "TtfFont",
        "to_bytes",
        _SERIALIZER_TESTS,
        None,
        "test_ttf_save_roundtrip",
        frozenset({"open", "save"}),
        frozenset({"FontLoader"}),
    ),
    _Proof(
        "OTF",
        "import",
        _TTF,
        "TtfFont",
        "_from_reader",
        _LOADER_TESTS,
        "TestLoaderMagicDetection",
        "test_otf_magic_detected",
        frozenset({"open"}),
        frozenset({"FontLoader", "TtfFont", "FontType"}),
    ),
    _Proof(
        "CFF",
        "import",
        _CFF,
        "CffFont",
        "_from_bytes",
        _SERIALIZER_TESTS,
        None,
        "test_cff_save_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "CffFont", "FontType"}),
    ),
    _Proof(
        "CFF",
        "export",
        _CFF,
        "CffFont",
        "to_bytes",
        _SERIALIZER_TESTS,
        None,
        "test_cff_save_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "CffFont", "FontType"}),
    ),
    _Proof(
        "TYPE1",
        "import",
        _TYPE1,
        "Type1Font",
        "_from_source",
        _SERIALIZER_TESTS,
        None,
        "test_type1_pfb_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "Type1Font", "FontType"}),
    ),
    _Proof(
        "TYPE1",
        "export",
        _TYPE1,
        "Type1Font",
        "to_bytes",
        _SERIALIZER_TESTS,
        None,
        "test_type1_pfb_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "Type1Font", "FontType"}),
    ),
    _Proof(
        "TYPE1_PFA",
        "import",
        _TYPE1,
        "Type1Font",
        "_from_source",
        _LOADER_TESTS,
        "TestLoaderMagicDetection",
        "test_pfa_magic_detected",
        frozenset({"open"}),
        frozenset({"FontLoader", "Type1Font"}),
    ),
    _Proof(
        "WOFF",
        "import",
        _WOFF,
        "WoffFont",
        "_from_reader",
        _WOFF_TESTS,
        None,
        "test_woff_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "WoffFont"}),
    ),
    _Proof(
        "WOFF",
        "export",
        _WOFF,
        "WoffFont",
        "to_bytes",
        _WOFF_TESTS,
        None,
        "test_woff_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "WoffFont"}),
    ),
    _Proof(
        "WOFF2",
        "import",
        _WOFF2,
        "Woff2Font",
        "_from_reader",
        _WOFF_TESTS,
        None,
        "test_woff2_project_generated_roundtrip",
        frozenset({"open", "convert", "to_bytes"}),
        frozenset({"FontLoader", "FontConverter", "Woff2Font", "FontType"}),
    ),
    _Proof(
        "WOFF2",
        "export",
        _WOFF2,
        "Woff2Font",
        "to_bytes",
        _WOFF_TESTS,
        None,
        "test_woff2_project_generated_roundtrip",
        frozenset({"open", "convert", "to_bytes"}),
        frozenset({"FontLoader", "FontConverter", "Woff2Font", "FontType"}),
    ),
    _Proof(
        "EOT",
        "import",
        _EOT,
        "EotFont",
        "_from_reader",
        _SERIALIZER_TESTS,
        None,
        "test_eot_save_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "EotFont", "FontType"}),
    ),
    _Proof(
        "EOT",
        "export",
        _EOT,
        "EotFont",
        "to_bytes",
        _SERIALIZER_TESTS,
        None,
        "test_eot_save_roundtrip",
        frozenset({"to_bytes", "open"}),
        frozenset({"FontLoader", "EotFont", "FontType"}),
    ),
)


def corroborate_python_font_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Add only source-and-test-proven font format records.

    Standalone OTF export and Type1 PFA export are deliberately not
    corroborated: the real round-trip evidence for OTF export only exercises
    it wrapped inside an EOT container, and the PFA export test never
    re-parses its own output -- neither is a closed round trip on its own.
    """

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []

    module_cache: dict[str, ast.Module | None] = {}

    def parsed(relative_path: str) -> ast.Module | None:
        if relative_path not in module_cache:
            module_cache[relative_path] = _parse_relative(root, relative_path)
        return module_cache[relative_path]

    result: list[AsposeOrgFormatEvidenceV1] = []
    for proof in _PROOFS:
        source_module = parsed(proof.source_file)
        test_module = parsed(proof.test_file)
        if source_module is None or test_module is None:
            continue
        owner = _unique_class(source_module, proof.class_name)
        method = _unique_method_in_class(owner, proof.method_name) if owner is not None else None
        if method is None:
            continue
        test_node: ast.AST | None
        if proof.test_owner is None:
            test_node = _unique_function(test_module, proof.test_name)
        else:
            test_class = _unique_class(test_module, proof.test_owner)
            test_node = (
                _unique_method_in_class(test_class, proof.test_name)
                if test_class is not None
                else None
            )
        if test_node is None:
            continue
        if not (proof.required_calls <= _called_attributes(test_node)):
            continue
        if not (proof.required_names <= _name_references(test_node)):
            continue
        result.append(
            AsposeOrgFormatEvidenceV1(
                format=proof.format_name,
                direction=proof.direction,
                file=proof.source_file,
                line=method.lineno,
                functional=True,
            )
        )

    if not _revision_matches(root, source_revision):
        return []
    return result


def _revision_matches(root: Path, expected: str) -> bool:
    if _REVISION.fullmatch(expected) is None or not (root / ".git").is_dir():
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


def _parse_relative(root: Path, relative_path: str) -> ast.Module | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
        return ast.parse(candidate.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError, ValueError):
        return None


def _unique_class(module: ast.Module, name: str) -> ast.ClassDef | None:
    matches = [node for node in module.body if isinstance(node, ast.ClassDef) and node.name == name]
    return matches[0] if len(matches) == 1 else None


def _unique_function(module: ast.Module, name: str) -> ast.FunctionDef | None:
    matches = [
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _unique_method_in_class(owner: ast.ClassDef | None, name: str) -> ast.FunctionDef | None:
    if owner is None:
        return None
    matches = [
        node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _name_references(node: ast.AST) -> set[str]:
    return {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }
