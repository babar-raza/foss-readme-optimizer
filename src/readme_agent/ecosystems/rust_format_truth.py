"""Derive directional Rust format evidence only from explicit public I/O APIs."""

from __future__ import annotations

import re
from typing import Literal

from readme_agent.ecosystems.rust_api_schema import (
    RustFormatDirection,
    RustFormatEvidenceV1,
    RustPublicApiSurfaceV1,
    RustPublicSymbolV1,
)

_ENUM_DIRECTIONS: dict[str, RustFormatDirection] = {
    "SaveFormat": "export",
    "ExportFormat": "export",
    "OutputFormat": "export",
    "LoadFormat": "import",
    "ImportFormat": "import",
    "InputFormat": "import",
}
_METHOD_PATTERNS: tuple[tuple[re.Pattern[str], RustFormatDirection], ...] = (
    (
        re.compile(r"^(?:save|write|export)(?:_to)?_([a-z][a-z0-9_]*)$"),
        "export",
    ),
    (
        re.compile(r"^(?:load|read|import)(?:_from)?_([a-z][a-z0-9_]*)$"),
        "import",
    ),
)
_NON_FORMAT_NAMES = frozenset({"auto", "default", "none", "unknown"})


def _format_name(name: str) -> str:
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()
    return words.replace("_", "")


def _record(
    symbol: RustPublicSymbolV1,
    *,
    name: str,
    direction: RustFormatDirection,
    evidence_kind: Literal["format_enum_variant", "explicit_io_method"],
) -> RustFormatEvidenceV1 | None:
    normalized = _format_name(name)
    if not normalized or normalized in _NON_FORMAT_NAMES:
        return None
    return RustFormatEvidenceV1(
        format=normalized,
        direction=direction,
        evidence_kind=evidence_kind,
        qualified_symbol=symbol.qualified_name,
        declaration_path=symbol.declaration_path,
        source_line=symbol.source_line,
    )


def extract_rust_format_evidence(
    surface: RustPublicApiSurfaceV1,
) -> list[RustFormatEvidenceV1]:
    """Return only public enum variants and methods with explicit format-I/O direction."""

    records: list[RustFormatEvidenceV1] = []
    for symbol in surface.symbols:
        if symbol.kind == "variant" and symbol.parent_name in _ENUM_DIRECTIONS:
            record = _record(
                symbol,
                name=symbol.name,
                direction=_ENUM_DIRECTIONS[symbol.parent_name],
                evidence_kind="format_enum_variant",
            )
            if record:
                records.append(record)
            continue
        if symbol.kind != "method":
            continue
        for pattern, direction in _METHOD_PATTERNS:
            match = pattern.fullmatch(symbol.name)
            if match:
                record = _record(
                    symbol,
                    name=match.group(1),
                    direction=direction,
                    evidence_kind="explicit_io_method",
                )
                if record:
                    records.append(record)
                break
    unique: dict[tuple[str, str, str], RustFormatEvidenceV1] = {}
    for record in sorted(
        records,
        key=lambda item: (
            item.format,
            item.direction,
            item.evidence_kind,
            len(item.qualified_symbol),
            item.qualified_symbol,
        ),
    ):
        key = (record.format, record.direction, record.evidence_kind)
        unique.setdefault(key, record)
    return list(unique.values())
