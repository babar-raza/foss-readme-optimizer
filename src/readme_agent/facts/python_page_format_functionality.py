"""Corroborate Python Page directions from public source and tests.

PWD-011: `aspose-page-foss/Aspose.Page-FOSS-for-Python` had no registered family
corroborator at all, so its genuinely real PS/EPS-import, PS-to-PNG-export, XPS-import,
and XPS-to-PDF-export capabilities never became verified `product.formats` facts -- the
deterministic `format_direction_contradiction` gate then correctly rejected the composer's
(accurate) mentions of those directions as unauthorized. Unlike the sibling Note
corroborator, none of these four directions depend on an optional runtime package (the
one direction that does -- XPS-to-image export, which hard-requires an undeclared
`skia-python`/`skia` install -- is deliberately left unverified; see the module docstring
below on why it is excluded).
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_PS_MODULE = "src/aspose/page/ps/document.py"
_XPS_MODULE = "src/aspose/page/xps/document.py"
_PS_RASTER_TESTS = "tests/ps/test_ps_raster_integration.py"
_XPS_INTEGRATION_TESTS = "tests/xps/test_xps_integration.py"


def corroborate_python_page_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Replace extractor noise with only source-and-test-proven Page directions.

    Deliberately excludes XPS-to-image export (`XpsDocument.to_image`/`to_images`):
    `xps/output.py` hard-requires `skia_available()` for that path
    (`RuntimeError("Skia rasterizer is required for XPS image conversion")` when absent),
    and `pyproject.toml` declares no `skia`/`skia-python` dependency anywhere -- not in
    `dependencies`, not in any optional-dependencies group. The repository's own tests
    only exercise that path by mocking `skia_available()` True and injecting a fake
    writer; the one test using real skia output requires an environment this repository
    never declares as installable. PS-to-PDF export (`PsDocument.to_pdf`) is similarly
    excluded even though the underlying code and a real, unconditional test both exist
    (`test_pdf_contains_title_creator`) -- that test calls the module-level `to_pdf(doc,
    options)` function, not `doc.to_pdf(...)`, which the `_called_attributes` AST check
    below (deliberately, like its Note/HTML precedents) only recognizes as an attribute
    call on the document instance; XPS already proves PDF export with a real instance-
    method call, so this narrower signal isn't needed to authorize the PDF format.
    """

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []

    result: list[AsposeOrgFormatEvidenceV1] = []
    result.extend(
        _corroborate_module(
            root,
            module_path=_PS_MODULE,
            class_name="PsDocument",
            test_path=_PS_RASTER_TESTS,
            test_name="test_ps_to_png_header",
            import_format="PS/EPS",
            import_method="from_file",
            export_format="PNG",
            export_method="to_image",
        )
    )
    result.extend(
        _corroborate_module(
            root,
            module_path=_XPS_MODULE,
            class_name="XpsDocument",
            test_path=_XPS_INTEGRATION_TESTS,
            test_name="test_simple_xps_to_pdf",
            import_format="XPS",
            import_method="from_file",
            export_format="PDF",
            export_method="to_pdf",
        )
    )

    if not _revision_matches(root, source_revision):
        return []
    return result


def _corroborate_module(
    root: Path,
    *,
    module_path: str,
    class_name: str,
    test_path: str,
    test_name: str,
    import_format: str,
    import_method: str,
    export_format: str,
    export_method: str,
) -> list[AsposeOrgFormatEvidenceV1]:
    module = _parse_relative(root, module_path)
    test_module = _parse_relative(root, test_path)
    if module is None or test_module is None:
        return []

    test = _unique_method_in_any_class(test_module, test_name)
    if test is None:
        return []
    called = _called_attributes(test)

    result: list[AsposeOrgFormatEvidenceV1] = []
    importer = _unique_method(module, class_name, import_method)
    if importer is not None and import_method in called:
        result.append(
            AsposeOrgFormatEvidenceV1(
                format=import_format,
                direction="import",
                file=module_path,
                line=importer.lineno,
                functional=True,
            )
        )

    exporter = _unique_method(module, class_name, export_method)
    if exporter is not None and export_method in called:
        result.append(
            AsposeOrgFormatEvidenceV1(
                format=export_format,
                direction="export",
                file=module_path,
                line=exporter.lineno,
                functional=True,
            )
        )

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


__all__ = ["corroborate_python_page_format_directions"]
