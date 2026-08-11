"""Corroborate Python Cells (spreadsheet) directions from public source and round-trip tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_WORKBOOK_MODULE = "aspose/cells_foss/workbook.py"
_INIT_MODULE = "aspose/cells_foss/__init__.py"
_XLSX_ROUNDTRIP_TEST = "examples/test_cell_protection_locked.py"
_CSV_ROUNDTRIP_TEST = "examples/test_csv_import_export.py"
_JSON_EXPORT_TEST = "examples/test_xlsx_to_json.py"
_MARKDOWN_EXPORT_TEST = "examples/test_xlsx_to_markdown.py"


def corroborate_python_cells_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Replace extractor noise with only source-and-test-proven Cells directions."""

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []
    workbook = _parse_relative(root, _WORKBOOK_MODULE)
    init_module = _parse_relative(root, _INIT_MODULE)
    xlsx_test = _parse_relative(root, _XLSX_ROUNDTRIP_TEST)
    csv_test = _parse_relative(root, _CSV_ROUNDTRIP_TEST)
    json_test = _parse_relative(root, _JSON_EXPORT_TEST)
    markdown_test = _parse_relative(root, _MARKDOWN_EXPORT_TEST)
    if None in (workbook, init_module, xlsx_test, csv_test, json_test, markdown_test):
        return []
    assert workbook is not None and init_module is not None
    assert xlsx_test is not None and csv_test is not None
    assert json_test is not None and markdown_test is not None

    if not _imports_name(init_module, "workbook", "Workbook"):
        return []

    result: list[AsposeOrgFormatEvidenceV1] = []

    save = _unique_method(workbook, "Workbook", "save")
    load = _unique_method(workbook, "Workbook", "_load")
    xlsx_roundtrip = _unique_method(
        xlsx_test, "TestCellProtectionLocked", "test_cell_locked_false_roundtrip"
    )
    if (
        save is not None
        and load is not None
        and xlsx_roundtrip is not None
        and "save" in _called_attributes(xlsx_roundtrip)
        and _constructs_with_argument(xlsx_roundtrip, "Workbook")
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="XLSX",
                direction="export",
                file=_WORKBOOK_MODULE,
                line=save.lineno,
                functional=True,
            )
        )
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="XLSX",
                direction="import",
                file=_WORKBOOK_MODULE,
                line=load.lineno,
                functional=True,
            )
        )

    save_csv = _unique_method(workbook, "Workbook", "save_as_csv")
    load_csv = _unique_method(workbook, "Workbook", "load_csv")
    csv_roundtrip = _unique_method(csv_test, "TestCSVBasicImportExport", "test_csv_roundtrip")
    if (
        save_csv is not None
        and load_csv is not None
        and csv_roundtrip is not None
        and {"save_as_csv", "load_csv"} <= _called_attributes(csv_roundtrip)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="CSV",
                direction="export",
                file=_WORKBOOK_MODULE,
                line=save_csv.lineno,
                functional=True,
            )
        )
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="CSV",
                direction="import",
                file=_WORKBOOK_MODULE,
                line=load_csv.lineno,
                functional=True,
            )
        )

    save_json = _unique_method(workbook, "Workbook", "save_as_json")
    json_export = _unique_method(json_test, "TestXLSXToJSONConversion", "test_sales_report_to_json")
    if (
        save_json is not None
        and json_export is not None
        and "save_as_json" in _called_attributes(json_export)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="JSON",
                direction="export",
                file=_WORKBOOK_MODULE,
                line=save_json.lineno,
                functional=True,
            )
        )

    save_markdown = _unique_method(workbook, "Workbook", "save_as_markdown")
    markdown_export = _unique_method(
        markdown_test, "TestXLSXToMarkdownConversion", "test_convert_all_xlsx_to_markdown"
    )
    if (
        save_markdown is not None
        and markdown_export is not None
        and "save_as_markdown" in _called_attributes(markdown_export)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="MARKDOWN",
                direction="export",
                file=_WORKBOOK_MODULE,
                line=save_markdown.lineno,
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


def _unique_method(module: ast.Module, owner: str, name: str) -> ast.FunctionDef | None:
    class_node = _unique_class(module, owner)
    if class_node is None:
        return None
    matches = [
        node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _imports_name(module: ast.Module, owner: str, name: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == owner
        and any(alias.name == name for alias in node.names)
        for node in module.body
    )


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


def _constructs_with_argument(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(call.func, ast.Name) and call.func.id == name and (call.args or call.keywords)
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
    )
