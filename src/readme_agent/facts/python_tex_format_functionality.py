"""Corroborate Python TeX directions from public source and round-trip tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_INPUT_READER = "src/aspose_tex/_input/reader.py"
_PRESENTATION = "src/aspose_tex/presentation/__init__.py"
_DVI_TEST = "tests/test_e2e_dvi_baseline.py"
_PDF_TEST = "tests/test_presentation_pdf_integration.py"
_SVG_TEST = "tests/test_presentation_svg_integration.py"


def corroborate_python_tex_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Add only source-and-test-proven TeX/DVI/PDF/SVG directions.

    This is a pure-Python from-scratch TeX engine: TEX is read (import) and
    DVI/PDF/SVG are written (export) -- there is no reverse direction for
    any of the three output formats, and no PNG/XPS/HTML export exists
    despite those being common for "Aspose.TeX"-branded products elsewhere
    (confirmed absent from source, not merely unverified). Only Plain TeX
    format loading is implemented; LaTeX (`load_format="latex"`) explicitly
    raises at runtime.
    """

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []

    input_reader = _parse_relative(root, _INPUT_READER)
    presentation = _parse_relative(root, _PRESENTATION)
    dvi_test = _parse_relative(root, _DVI_TEST)
    pdf_test = _parse_relative(root, _PDF_TEST)
    svg_test = _parse_relative(root, _SVG_TEST)

    result: list[AsposeOrgFormatEvidenceV1] = []

    file_input_source = (
        _unique_method(input_reader, "FileInputSource", "read_line")
        if input_reader is not None
        else None
    )
    dvi_device = (
        _unique_method(presentation, "DviDevice", "get_bytes") if presentation is not None else None
    )
    dvi_run = _unique_function(dvi_test, "_run") if dvi_test is not None else None
    if (
        file_input_source is not None
        and dvi_device is not None
        and dvi_run is not None
        and "run" in _called_attributes(dvi_run)
        and {"FileInputSource", "TeXJob", "DviDevice"} <= _name_references(dvi_run)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="TEX",
                direction="import",
                file=_INPUT_READER,
                line=file_input_source.lineno,
                functional=True,
            )
        )
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="DVI",
                direction="export",
                file=_PRESENTATION,
                line=dvi_device.lineno,
                functional=True,
            )
        )

    pdf_device = (
        _unique_method(presentation, "PdfDevice", "get_bytes") if presentation is not None else None
    )
    pdf_hello = (
        _unique_function(pdf_test, "test_texjob_pdf_hello_world") if pdf_test is not None else None
    )
    if (
        pdf_device is not None
        and pdf_hello is not None
        and {"run", "startswith", "endswith"} <= _called_attributes(pdf_hello)
        and {"TeXJob", "PdfDevice", "StringInputSource"} <= _name_references(pdf_hello)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="PDF",
                direction="export",
                file=_PRESENTATION,
                line=pdf_device.lineno,
                functional=True,
            )
        )

    svg_device = (
        _unique_method(presentation, "SvgDevice", "get_bytes") if presentation is not None else None
    )
    svg_hello = (
        _unique_function(svg_test, "test_texjob_svg_hello_world") if svg_test is not None else None
    )
    if (
        svg_device is not None
        and svg_hello is not None
        and {"run", "startswith", "fromstring"} <= _called_attributes(svg_hello)
        and {"TeXJob", "SvgDevice", "StringInputSource"} <= _name_references(svg_hello)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="SVG",
                direction="export",
                file=_PRESENTATION,
                line=svg_device.lineno,
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
