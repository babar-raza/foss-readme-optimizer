"""Collect source-bound Python distribution and capability evidence."""

from __future__ import annotations

import ast
import hashlib
import re
import tomllib
from pathlib import Path

_REQUIRES_DISTRIBUTION = re.compile(
    r"\brequires?\s+(?P<distribution>[A-Za-z0-9][A-Za-z0-9_.-]*)",
    flags=re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def python_distribution_evidence(root: Path) -> tuple[object, list[str]] | None:
    """Return manifest-declared runtime, maturity, dependency, and typing details."""

    manifest = root / "pyproject.toml"
    if not manifest.is_file():
        return None
    try:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    classifiers = [str(item) for item in project.get("classifiers", []) if isinstance(item, str)]
    status = next(
        (
            classifier.split(" - ", 1)[1].strip()
            for classifier in classifiers
            if classifier.startswith("Development Status ::") and " - " in classifier
        ),
        None,
    )
    dependencies = [str(item) for item in project.get("dependencies", []) if isinstance(item, str)]
    typed_marker = next(
        (path for path in sorted((root / "src").glob("**/py.typed")) if path.is_file()),
        None,
    )
    typed_classifier = "Typing :: Typed" in classifiers
    value: dict[str, object] = {
        "manifest_path": "pyproject.toml",
        "requires_python": str(project.get("requires-python") or "").strip(),
        "runtime_dependencies": dependencies,
        "development_status": status,
        "typed_classifier": typed_classifier,
    }
    locations = ["pyproject.toml"]
    if typed_marker is not None:
        relative = typed_marker.relative_to(root).as_posix()
        value["typed_marker"] = {"path": relative, "sha256": _sha256(typed_marker)}
        locations.append(relative)
    return value, locations


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _dependency_purpose(path: Path, import_name: str) -> str:
    folded = path.as_posix().casefold()
    if "/mcp/" in folded or import_name == "fastmcp":
        return "MCP server hosting"
    if "image" in folded or import_name == "skia":
        return "image conversion"
    return "optional capability"


def python_capability_dependencies(root: Path) -> tuple[object, list[str]] | None:
    """Return optional distributions proven by imports and exact source declarations."""

    source_root = root / "src"
    if not source_root.is_dir():
        return None
    entries: list[dict[str, object]] = []
    locations: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        imports = _imported_roots(tree)
        declared: list[tuple[str, int]] = [
            (match.group("distribution"), text.count("\n", 0, match.start()) + 1)
            for match in _REQUIRES_DISTRIBUTION.finditer(text)
        ]
        if "fastmcp" in imports and not any(
            distribution.casefold() == "fastmcp" for distribution, _line in declared
        ):
            line = next(
                (
                    node.lineno
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and node.module == "fastmcp"
                ),
                1,
            )
            declared.append(("fastmcp", line))
        relative = path.relative_to(root).as_posix()
        for distribution, line in declared:
            normalized = distribution.casefold().replace("-", "").replace("_", "")
            if len(normalized) < 3:
                continue
            matching_import = next(
                (
                    imported
                    for imported in imports
                    if normalized == imported.casefold().replace("_", "")
                    or normalized == imported.casefold().replace("_", "") + "python"
                    or (normalized == "pillow" and imported.casefold() == "pil")
                ),
                None,
            )
            if matching_import is None:
                continue
            entry = {
                "distribution": distribution,
                "import_name": matching_import,
                "purpose": _dependency_purpose(path, matching_import),
                "install_command": f"python -m pip install {distribution}",
                "path": relative,
                "line": line,
                "source_sha256": _sha256(path),
            }
            key = (str(entry["distribution"]).casefold(), str(entry["purpose"]))
            if any(
                (str(item["distribution"]).casefold(), str(item["purpose"])) == key
                for item in entries
            ):
                continue
            entries.append(entry)
            locations.append(relative)
    if not entries:
        return None
    return {"entries": sorted(entries, key=lambda item: str(item["distribution"]))}, sorted(
        set(locations)
    )


_PDF_CAPABILITY_SPECS = (
    (
        "Create, load, save, merge, and inspect PDF documents",
        "document.py",
        "Document",
        ("load_from", "save", "merge", "validate"),
    ),
    (
        "Add and edit text and images, including text replacement and redaction",
        "pages.py",
        "Page",
        ("add_text", "add_image", "replace_text", "redact_text"),
    ),
    (
        "Extract text, images, and attachments",
        "facades.py",
        "PdfExtractor",
        ("extract_text", "get_text", "extract_image", "extract_attachment"),
    ),
    (
        "Concatenate, extract, insert, delete, and append PDF pages",
        "facades.py",
        "PdfFileEditor",
        ("concatenate", "extract", "insert", "delete", "append"),
    ),
    ("Render PDF pages to PNG or TIFF images", "pages.py", "Page", ("render", "save_as_image")),
    (
        "Create and manage interactive form fields",
        "forms.py",
        "Form",
        ("add_text_field", "add_checkbox", "add_radio_group", "flatten"),
    ),
    (
        "Add, update, and remove PDF annotations",
        "annotations/__init__.py",
        "AnnotationCollection",
        ("add", "insert", "delete", "clear"),
    ),
    (
        "Encrypt, decrypt, optimize, and compress PDF documents",
        "document.py",
        "Document",
        ("encrypt", "decrypt", "optimize", "compress_streams"),
    ),
    (
        "Run heuristic PDF/A and PDF/UA validation",
        "document.py",
        "Document",
        ("validate_pdfa", "validate_pdfua", "convert_to_pdfa", "convert_to_pdfua"),
    ),
)


def _class_methods(path: Path, class_name: str) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()
    definition = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if definition is None:
        return set()
    return {
        node.name
        for node in definition.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def python_repository_capability_details(root: Path) -> tuple[object, list[str]] | None:
    """Return visitor-facing PDF groups only when every named API exists in source."""

    groups: list[dict[str, object]] = []
    locations: list[str] = []
    source_root = root / "src/aspose_pdf"
    for label, suffix, class_name, required in _PDF_CAPABILITY_SPECS:
        path = source_root / suffix
        methods = _class_methods(path, class_name) if path.is_file() else set()
        if not set(required).issubset(methods):
            continue
        relative = path.relative_to(root).as_posix()
        groups.append(
            {
                "label": label,
                "class": class_name,
                "methods": list(required),
                "source_path": relative,
                "source_sha256": _sha256(path),
            }
        )
        locations.append(relative)
    render_test = root / "tests/test_page_rendering.py"
    render_source = source_root / "pages.py"
    output_formats: list[str] = []
    if render_test.is_file() and render_source.is_file():
        text = render_test.read_text(encoding="utf-8")
        if (
            "save_as_image" in _class_methods(render_source, "Page")
            and '"page.png"' in text
            and '"page.tiff"' in text
        ):
            output_formats = ["PDF", "PNG", "TIFF"]
            locations.append("tests/test_page_rendering.py")
    if len(groups) < 6 or not output_formats:
        return None
    return (
        {
            "input_formats": ["PDF"],
            "output_formats": output_formats,
            "capability_groups": groups,
            "assurance": "source_api_and_test_corroborated",
        },
        sorted(set(locations)),
    )
