"""Corroborate Python HTML directions from public source and round-trip tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_HTML_DOCUMENT = "src/aspose_html/html_document.py"
_DOM_DOCUMENT = "src/aspose_html/dom/_document.py"
_FILE_IO_TESTS = "tests/test_file_io.py"


def corroborate_python_html_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Replace extractor noise with only source-and-test-proven HTML directions."""

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []
    html_document = _parse_relative(root, _HTML_DOCUMENT)
    dom_document = _parse_relative(root, _DOM_DOCUMENT)
    tests = _parse_relative(root, _FILE_IO_TESTS)
    package = _parse_relative(root, "src/aspose_html/__init__.py")
    dom_package = _parse_relative(root, "src/aspose_html/dom/__init__.py")
    if None in (html_document, dom_document, tests, package, dom_package):
        return []
    assert html_document is not None and dom_document is not None and tests is not None
    assert package is not None and dom_package is not None

    result: list[AsposeOrgFormatEvidenceV1] = []
    load = _unique_method(html_document, "HTMLDocument", "load")
    load_test = _unique_function(tests, "test_load_returns_document")
    if (
        load is not None
        and _has_classmethod(load)
        and load_test is not None
        and _imports_name(package, "aspose_html.html_document", "HTMLDocument")
        and {"write_bytes", "load"} <= _called_attributes(load_test)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="HTML",
                direction="import",
                file=_HTML_DOCUMENT,
                line=load.lineno,
                functional=True,
            )
        )

    save = _unique_method(dom_document, "Document", "save")
    save_test = _unique_function(tests, "test_save_round_trip")
    if (
        save is not None
        and save_test is not None
        and _imports_name(dom_package, "aspose_html.dom._document", "Document")
        and {"parse", "save", "read_text", "get_elements_by_tag_name"}
        <= _called_attributes(save_test)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="HTML",
                direction="export",
                file=_DOM_DOCUMENT,
                line=save.lineno,
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


def _unique_function(module: ast.Module, name: str) -> ast.FunctionDef | None:
    matches = [
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _has_classmethod(node: ast.FunctionDef) -> bool:
    return any(
        isinstance(item, ast.Name) and item.id == "classmethod" for item in node.decorator_list
    )


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
