"""Collect source-proven PDF guidance and limitations for public presentation."""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def python_pdf_public_guidance(root: Path) -> tuple[object, list[str]] | None:
    """Return exact public guidance reconstructed from non-README source evidence."""

    manifest = root / "pyproject.toml"
    typed = root / "src/aspose_pdf/py.typed"
    features = root / "supported-features.md"
    document = root / "src/aspose_pdf/document.py"
    font_authoring = root / "src/aspose_pdf/engine/font_authoring.py"
    text_layout = root / "src/aspose_pdf/engine/text_layout.py"
    required = (manifest, typed, features, document, font_authoring, text_layout)
    if not all(path.is_file() for path in required):
        return None
    project = tomllib.loads(manifest.read_text(encoding="utf-8")).get("project", {})
    classifiers = project.get("classifiers", []) if isinstance(project, dict) else []
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in required[2:])
    markers = (
        "FontEmbeddingException",
        "TextLayoutOptions",
        "raw bytes, or a binary stream",
        "missing password instead of yielding an empty document",
        "shaped visual order",
        "/ToUnicode",
    )
    if "Development Status :: 3 - Alpha" not in classifiers or not all(
        marker in corpus for marker in markers
    ):
        return None
    statements = [
        (
            "Aspose.PDF FOSS for Python is an open-source Python library for creating, "
            "reading, editing, rendering, and validating PDF documents."
        ),
        (
            "The package is implemented in Python and ships type information. The project is "
            "currently in alpha, so APIs and feature coverage may evolve before the first "
            "stable release."
        ),
        (
            "For Unicode outside the Standard-14 encodings, provide an embeddable "
            "TrueType/OpenType font as bytes, a path, or a `FontDescriptor`:"
        ),
        (
            "The writer creates a subset Type0/CID font, two-byte character codes, "
            "`/ToUnicode`, widths, and the required CID-to-glyph mapping. A character that "
            "the supplied font cannot represent raises `FontEmbeddingException` instead of "
            "silently writing `.notdef`."
        ),
        (
            "Install the `text-layout` extra and pass `TextLayoutOptions` for OpenType "
            "shaping, bidirectional runs, ordered font fallback, and width-constrained line "
            "layout:"
        ),
        (
            "Logical text is retained for extraction while glyphs are painted in their "
            "shaped visual order."
        ),
        (
            "`Document(source, password=..., limits=...)` accepts a path, raw bytes, or a "
            "binary stream and is equivalent to `Document().load_from(source, ...)`. A "
            "missing file, non-PDF data, or a missing password raises; neither form ever "
            "hands back a silently empty document."
        ),
        (
            "See the [supported features](supported-features.md) document for the detailed "
            "capability matrix and known limitations."
        ),
    ]
    return statements, [path.relative_to(root).as_posix() for path in required]


def python_pdf_verified_boundaries(root: Path) -> tuple[object, list[str]] | None:
    """Return exact limitations corroborated by source and feature documentation."""

    features = root / "supported-features.md"
    sources = [
        root / "src/aspose_pdf/document.py",
        root / "src/aspose_pdf/exceptions.py",
        root / "src/aspose_pdf/pages.py",
        root / "src/aspose_pdf/pdfa.py",
        root / "src/aspose_pdf/pdfua.py",
        root / "src/aspose_pdf/signature.py",
    ]
    if not features.is_file() or not all(path.is_file() for path in sources):
        return None
    corpus = (
        features.read_text(encoding="utf-8")
        + "\n"
        + "\n".join(path.read_text(encoding="utf-8") for path in sources)
    )
    markers = (
        "OCR is not implemented",
        "not certification-grade PDF/A conformance",
        "not certification-grade PDF/UA conformance",
        "does **not** perform full PKCS#7 certificate chain checking",
    )
    if not all(marker in corpus for marker in markers):
        return None
    boundaries = [
        (
            "Page rendering supports common page content; it is not represented as complete "
            "PDF graphics coverage."
        ),
        "PDF/A and PDF/UA checks are heuristic signals, not certification-grade conformance.",
        "OCR is not implemented, and layout reflow remains outside the prerelease scope.",
        (
            "The lightweight signature check does not perform full PKCS#7 certificate-chain "
            "validation."
        ),
        "Compatibility surfaces may name features that are unavailable and must fail explicitly.",
        (
            "The documented feature set is bounded by the active test suite rather than every "
            "exposed compatibility name."
        ),
    ]
    locations = ["supported-features.md", *(path.relative_to(root).as_posix() for path in sources)]
    return (
        {
            "boundaries": boundaries,
            "evidence": [
                {"path": relative, "sha256": _sha256(root / relative)}
                for relative in sorted(set(locations))
            ],
            "assurance": "source_and_authoritative_feature_contract",
        },
        sorted(set(locations)),
    )


__all__ = ["python_pdf_public_guidance", "python_pdf_verified_boundaries"]
