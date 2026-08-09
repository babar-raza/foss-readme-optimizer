"""Collect source-proven public PDF capabilities and visitor guidance."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

_Component = tuple[str, str, frozenset[str]]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _verified_group(
    root: Path,
    label: str,
    components: tuple[_Component, ...],
) -> tuple[dict[str, object], list[str]] | None:
    evidence: list[dict[str, object]] = []
    locations: list[str] = []
    for relative, class_name, required in components:
        path = root / relative
        if not path.is_file() or not required.issubset(_class_methods(path, class_name)):
            return None
        evidence.append(
            {
                "class": class_name,
                "methods": sorted(required),
                "source_path": relative,
                "source_sha256": _sha256(path),
            }
        )
        locations.append(relative)
    return {"label": label, "components": evidence}, locations


_CAPABILITY_GROUPS: tuple[tuple[str, tuple[_Component, ...]], ...] = (
    (
        "Create, load, save, merge, split, and inspect PDF documents",
        (
            (
                "src/aspose_pdf/document.py",
                "Document",
                frozenset({"load_from", "save", "merge", "validate"}),
            ),
            ("src/aspose_pdf/facades.py", "PdfFileEditor", frozenset({"extract"})),
        ),
    ),
    (
        "Extract text, images, attachments, metadata, and bookmarks",
        (
            (
                "src/aspose_pdf/facades.py",
                "PdfExtractor",
                frozenset({"extract_text", "extract_image", "extract_attachment"}),
            ),
            (
                "src/aspose_pdf/document.py",
                "Document",
                frozenset({"info", "xmp_metadata", "outlines"}),
            ),
        ),
    ),
    (
        "Render pages to PNG or TIFF",
        (("src/aspose_pdf/pages.py", "Page", frozenset({"render", "save_as_image"})),),
    ),
    (
        "Replace or redact text in supported content streams",
        (("src/aspose_pdf/pages.py", "Page", frozenset({"replace_text", "redact_text"})),),
    ),
    (
        "Concatenate, extract, insert, delete, and append PDF pages",
        (
            (
                "src/aspose_pdf/facades.py",
                "PdfFileEditor",
                frozenset({"concatenate", "extract", "insert", "delete", "append"}),
            ),
        ),
    ),
    (
        "Create and manage interactive form fields",
        (
            (
                "src/aspose_pdf/forms.py",
                "Form",
                frozenset({"add_text_field", "add_checkbox", "add_radio_group", "flatten"}),
            ),
        ),
    ),
    (
        "Add, update, and remove PDF annotations",
        (
            (
                "src/aspose_pdf/annotations/__init__.py",
                "AnnotationCollection",
                frozenset({"add", "insert", "delete", "clear"}),
            ),
        ),
    ),
    (
        "Create and inspect PDF signatures",
        (("src/aspose_pdf/signature.py", "PdfSignature", frozenset({"valid", "validate"})),),
    ),
    (
        "Optimize streams, images, fonts, and unused objects",
        (
            (
                "src/aspose_pdf/document.py",
                "Document",
                frozenset({"optimize", "optimize_resources", "compress_streams"}),
            ),
        ),
    ),
    (
        "Apply configurable resource limits when processing untrusted PDFs",
        (
            ("src/aspose_pdf/document.py", "Document", frozenset({"load_from"})),
            ("src/aspose_pdf/load_limits.py", "PdfLoadLimits", frozenset({"unlimited"})),
        ),
    ),
    (
        "Perform heuristic PDF/A and PDF/UA checks and conversions",
        (
            (
                "src/aspose_pdf/document.py",
                "Document",
                frozenset(
                    {"validate_pdfa", "validate_pdfua", "convert_to_pdfa", "convert_to_pdfua"}
                ),
            ),
        ),
    ),
)


def _rich_authoring_group(root: Path) -> tuple[dict[str, object], list[str]] | None:
    group = _verified_group(
        root,
        (
            "Add Standard-14 or embedded Unicode text, including shaped bidirectional text, "
            "plus images, lines, rectangles, annotations, attachments, and form data"
        ),
        (
            (
                "src/aspose_pdf/pages.py",
                "Page",
                frozenset({"add_text", "add_image", "draw_line", "draw_rectangle"}),
            ),
            ("src/aspose_pdf/document.py", "Document", frozenset({"add_attachment"})),
            ("src/aspose_pdf/forms.py", "Form", frozenset({"add_text_field"})),
            (
                "src/aspose_pdf/annotations/__init__.py",
                "AnnotationCollection",
                frozenset({"add"}),
            ),
        ),
    )
    features = root / "supported-features.md"
    layout = root / "src/aspose_pdf/text_layout.py"
    if group is None or not features.is_file() or not layout.is_file():
        return None
    feature_text = features.read_text(encoding="utf-8").casefold()
    if not all(
        marker in feature_text
        for marker in (
            "embedded unicode text with `page.add_text()`",
            "unicode bidi algorithm",
        )
    ):
        return None
    value, locations = group
    components = value["components"]
    assert isinstance(components, list)
    components.append(
        {
            "class": "TextLayoutOptions",
            "methods": [],
            "source_path": "src/aspose_pdf/text_layout.py",
            "source_sha256": _sha256(layout),
        }
    )
    locations.extend(["src/aspose_pdf/text_layout.py", "supported-features.md"])
    return value, locations


def python_pdf_capability_details(root: Path) -> tuple[object, list[str]] | None:
    """Return PDF capability labels only when their complete source contracts exist."""

    groups: list[dict[str, object]] = []
    locations: list[str] = []
    for label, components in _CAPABILITY_GROUPS:
        result = _verified_group(root, label, components)
        if result is not None:
            value, group_locations = result
            groups.append(value)
            locations.extend(group_locations)
    if rich := _rich_authoring_group(root):
        groups.append(rich[0])
        locations.extend(rich[1])
    encryption = root / "src/aspose_pdf/engine/encryption.py"
    if encryption.is_file():
        text = encryption.read_text(encoding="utf-8")
        if "AES-CBC, RC4 encryption" in text:
            groups.append(
                {
                    "label": "Encrypt and decrypt documents with RC4 or AES",
                    "source_path": "src/aspose_pdf/engine/encryption.py",
                    "source_sha256": _sha256(encryption),
                }
            )
            locations.append("src/aspose_pdf/engine/encryption.py")
    render_test = root / "tests/test_page_rendering.py"
    if not render_test.is_file():
        return None
    render_text = render_test.read_text(encoding="utf-8")
    if '"page.png"' not in render_text or '"page.tiff"' not in render_text:
        return None
    locations.append("tests/test_page_rendering.py")
    if len(groups) < 6:
        return None
    return (
        {
            "input_formats": ["PDF"],
            "output_formats": ["PDF", "PNG", "TIFF"],
            "capability_groups": groups,
            "assurance": "source_api_and_documentation_corroborated",
        },
        sorted(set(locations)),
    )


__all__ = ["python_pdf_capability_details"]
