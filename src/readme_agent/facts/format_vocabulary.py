"""Define the canonical file-format vocabulary used by repository facts."""

from __future__ import annotations

import re

DOCUMENT_FORMAT_ABBREVIATIONS = frozenset(
    {
        "3DS",
        "3MF",
        "A3DW",
        "AMF",
        "APNG",
        "BMP",
        "CFB",
        "CFF",
        "CGM",
        "COLLADA",
        "CSV",
        "CSS",
        "DAE",
        "DOC",
        "DOCX",
        "DRACO",
        "DVI",
        "DXF",
        "EMF",
        "EML",
        "EOT",
        "EPS",
        "EPUB",
        "FBX",
        "GIF",
        "GLB",
        "GLTF",
        "HTML",
        "ICS",
        "JPEG",
        "JPG",
        "JSON",
        "JBIG2",
        "JT",
        "MARKDOWN",
        "MHT",
        "MHTML",
        "MIME",
        "MSG",
        "OBJ",
        "ODP",
        "ODF",
        "ODS",
        "ODT",
        "ONE",
        "ONENOTE",
        "OPC",
        "OST",
        "OTF",
        "OTP",
        "PDF",
        "PFA",
        "PFB",
        "PLY",
        "PNG",
        "POTM",
        "POTX",
        "PPSM",
        "PPSX",
        "PPT",
        "PPTM",
        "PPTX",
        "PS",
        "PSB",
        "PSD",
        "PST",
        "RTF",
        "RVM",
        "STL",
        "SVG",
        "SWF",
        "TEX",
        "TGA",
        "TIFF",
        "TTF",
        "TXT",
        "TYPE1",
        "U3D",
        "USD",
        "VCF",
        "WEBP",
        "WMF",
        "WOFF",
        "WOFF2",
        "XLS",
        "XLSB",
        "XLSM",
        "XLSX",
        "XML",
        "XPS",
        "ZIP",
    }
)

_ALIASES = {
    "discreet3ds": "3DS",
    "3mf": "3MF",
    "microsoft3mf": "3MF",
    "threemf": "3MF",
    "html5": "HTML",
    "markdown": "MARKDOWN",
    "ms-one": "ONE",
    "ms_one": "ONE",
    "onestore": "ONE",
    "type1": "TYPE1",
}
_FORMAT_SUPPORT = re.compile(
    r"^(?P<action>import|export) support for\s+(?P<format>[A-Za-z0-9.+_-]+)"
    r"(?:\s+format)?(?:\s+\(method name:\s*[^)]+\))?(?:\s+via\s+.+)?$",
    re.IGNORECASE,
)


def canonical_document_format(value: str) -> str | None:
    """Return a governed public format label or reject a method-like token."""

    normalized = value.strip().replace(" ", "").casefold()
    alias = _ALIASES.get(normalized)
    if alias is not None:
        return alias
    upper = normalized.upper()
    return upper if upper in DOCUMENT_FORMAT_ABBREVIATIONS else None


def parse_format_support_claim(text: str) -> tuple[str, str] | None:
    """Parse one extractor claim only when its object is a known document format."""

    match = _FORMAT_SUPPORT.fullmatch(text.strip())
    if match is None:
        return None
    format_name = canonical_document_format(match.group("format"))
    if format_name is None:
        return None
    return match.group("action").casefold(), format_name


__all__ = [
    "DOCUMENT_FORMAT_ABBREVIATIONS",
    "canonical_document_format",
    "parse_format_support_claim",
]
