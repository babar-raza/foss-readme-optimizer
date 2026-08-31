"""Corroborate Python Note directions from public source, tests, and packaging metadata."""

from __future__ import annotations

import ast
import re
import subprocess
import tomllib
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_MODEL_MODULE = "src/aspose/note/model.py"
_DOCUMENT_BASICS_TESTS = "tests/test_aspose_note_dom_document.py"
_SAVE_OPTIONS_TESTS = "tests/test_aspose_note_save_options.py"
_PYPROJECT = "pyproject.toml"


def corroborate_python_note_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Replace extractor noise with only source-and-test-proven Note directions.

    `.one` input and PDF export are the repository's only two directions
    (`Document.Save()` itself raises `UnsupportedSaveFormatException` for anything but
    `SaveFormat.Pdf` -- there is no broader export surface to under-claim). PDF export's
    own proving test (`test_save_pdf_with_pdfsaveoptions`) is wrapped in
    `@unittest.skipUnless(HAS_REPORTLAB, ...)`, so structural presence alone doesn't prove
    the test actually *runs* in every environment -- unlike the sibling HTML corroborator,
    this one additionally requires `pyproject.toml` to declare a real, versioned `pdf`
    optional-dependency group naming `reportlab`, so acceptance rests on three independent
    signals (real implementation, a real test that would prove it, a real installable
    dependency declaration), not structural presence alone.
    """

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []
    model = _parse_relative(root, _MODEL_MODULE)
    document_tests = _parse_relative(root, _DOCUMENT_BASICS_TESTS)
    save_tests = _parse_relative(root, _SAVE_OPTIONS_TESTS)
    if None in (model, document_tests, save_tests):
        return []
    assert model is not None and document_tests is not None and save_tests is not None

    result: list[AsposeOrgFormatEvidenceV1] = []

    load = _unique_method(model, "Document", "__init__")
    load_test = _unique_method_in_any_class(document_tests, "test_construct_from_path")
    if (
        load is not None
        and load_test is not None
        and {"FirstChild", "LastChild"} <= _accessed_attributes(load_test)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="OneNote",
                direction="import",
                file=_MODEL_MODULE,
                line=load.lineno,
                functional=True,
            )
        )

    save = _unique_method(model, "Document", "Save")
    save_test = _unique_method_in_any_class(save_tests, "test_save_pdf_with_pdfsaveoptions")
    if (
        save is not None
        and save_test is not None
        and {"Save"} <= _called_attributes(save_test)
        and _pdf_extra_is_declared(root)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="PDF",
                direction="export",
                file=_MODEL_MODULE,
                line=save.lineno,
                functional=True,
            )
        )

    if not _revision_matches(root, source_revision):
        return []
    return result


def _pdf_extra_is_declared(root: Path) -> bool:
    manifest = root / _PYPROJECT
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    extras = data.get("project", {}).get("optional-dependencies", {})
    pdf_extra = extras.get("pdf")
    if not isinstance(pdf_extra, list):
        return False
    return any(isinstance(dep, str) and dep.casefold().startswith("reportlab") for dep in pdf_extra)


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


def _unique_method_in_any_class(module: ast.Module, name: str) -> ast.FunctionDef | None:
    """Find one uniquely-named test method regardless of which `TestCase` class holds it."""

    matches = [
        node
        for class_node in module.body
        if isinstance(class_node, ast.ClassDef)
        for node in class_node.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


def _accessed_attributes(node: ast.AST) -> set[str]:
    return {
        item.attr
        for item in ast.walk(node)
        if isinstance(item, ast.Attribute) and not isinstance(item.ctx, ast.Store)
    }


__all__ = ["corroborate_python_note_format_directions"]
