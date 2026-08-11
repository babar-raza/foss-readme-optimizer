"""Corroborate Python Slides directions from public source and round-trip tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_OPC_PACKAGE = "aspose/slides_foss/_internal/opc/opc_package.py"
_PRESENTATION = "aspose/slides_foss/Presentation.py"
_MARKDOWN_WRITER = "aspose/slides_foss/_internal/export/markdown/writers.py"
_PPTX_ROUNDTRIP_TEST = "tests/conftest.py"
_MARKDOWN_EXPORT_TEST = "tests/test_markdown_export.py"


def corroborate_python_slides_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Replace extractor noise with only source-and-test-proven Slides directions.

    Only PPTX (import+export) and Markdown (export only) are corroborated.
    Every other SaveFormat/SourceFormat enum member (PDF, HTML, HTML5, XPS,
    TIFF, SWF, GIF, XML, ODP, PPT, PPS, POT, FODP, OTP) is declared in the
    enum but has no working exporter/loader anywhere in source -- confirmed
    absent, not merely unverified -- and the project's own README documents
    this under "Limitations". PPT and ODP import are also not genuinely
    wired despite SourceFormat detection matching their extensions: the only
    loader (OpcPackage.open) unconditionally treats input as a ZIP/OPC
    package, which a real legacy .ppt (OLE2/CFB) is not, and no ODP-specific
    parser exists.
    """

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []

    opc_package = _parse_relative(root, _OPC_PACKAGE)
    presentation = _parse_relative(root, _PRESENTATION)
    markdown_writer = _parse_relative(root, _MARKDOWN_WRITER)
    pptx_test = _parse_relative(root, _PPTX_ROUNDTRIP_TEST)
    markdown_test = _parse_relative(root, _MARKDOWN_EXPORT_TEST)

    result: list[AsposeOrgFormatEvidenceV1] = []

    opc_open = (
        _unique_method(opc_package, "OpcPackage", "open") if opc_package is not None else None
    )
    presentation_save = (
        _unique_method(presentation, "Presentation", "save") if presentation is not None else None
    )
    pptx_fixture = _unique_function(pptx_test, "tmp_pptx") if pptx_test is not None else None
    if (
        opc_open is not None
        and presentation_save is not None
        and pptx_fixture is not None
        and "save" in _called_attributes(pptx_fixture)
        and "Presentation" in _name_references(pptx_fixture)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="PPTX",
                direction="import",
                file=_OPC_PACKAGE,
                line=opc_open.lineno,
                functional=True,
            )
        )
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="PPTX",
                direction="export",
                file=_PRESENTATION,
                line=presentation_save.lineno,
                functional=True,
            )
        )

    md_writer_function = (
        _unique_function(markdown_writer, "save_presentation_to_markdown")
        if markdown_writer is not None
        else None
    )
    md_export_test = (
        _unique_function(markdown_test, "test_save_to_file_path")
        if markdown_test is not None
        else None
    )
    if (
        md_writer_function is not None
        and md_export_test is not None
        and "save" in _called_attributes(md_export_test)
        and "Presentation" in _name_references(md_export_test)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="MD",
                direction="export",
                file=_MARKDOWN_WRITER,
                line=md_writer_function.lineno,
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


def _unique_method(module: ast.Module, owner: str, name: str) -> ast.FunctionDef | None:
    class_node = _unique_class(module, owner)
    if class_node is None:
        return None
    matches = [
        node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == name
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
