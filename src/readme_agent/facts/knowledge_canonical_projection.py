"""Project verified imported knowledge into missing canonical product-truth fields."""

from __future__ import annotations

import re
from collections.abc import Iterable

from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_ACCEPTED_STATES = {"verified", "policy_approved"}
_PROJECTION_MAP = {
    "aspose.feature_claims": "product.capabilities",
    "aspose.format_support_claims": "product.formats",
    "aspose.limitation_claims": "product.limitations",
}
_FORMAT_RE = re.compile(
    r"^(import|export) support for\s+([A-Za-z0-9.+_-]+)"
    r"(?:\s+format)?(?:\s+\(method name:\s*[^)]+\))?(?:\s+via\s+.+)?$",
    re.IGNORECASE,
)
_LIMITATION_RE = re.compile(
    r"^Not implemented:\s*(.+?)(?:\s+in\s+.+(?:[/\\].+)?(?::\d+)?)?$",
    re.IGNORECASE,
)
_INTERNAL_TEXT_RE = re.compile(
    r"(?:source revision|verification environment|inventoried at|syntax checked|"
    r"evidence receipt|confidence score|extraction failure)",
    re.IGNORECASE,
)
_ABBREVIATIONS = {
    "3mf": "3MF",
    "bmp": "BMP",
    "csv": "CSV",
    "doc": "DOC",
    "docx": "DOCX",
    "dxf": "DXF",
    "epub": "EPUB",
    "eps": "EPS",
    "fbx": "FBX",
    "gif": "GIF",
    "gltf": "GLTF",
    "html": "HTML",
    "jbig2": "JBIG2",
    "jpeg": "JPEG",
    "jpg": "JPG",
    "json": "JSON",
    "obj": "OBJ",
    "odf": "ODF",
    "ods": "ODS",
    "odt": "ODT",
    "pdf": "PDF",
    "ply": "PLY",
    "png": "PNG",
    "ps": "PS",
    "rvm": "RVM",
    "stl": "STL",
    "svg": "SVG",
    "tiff": "TIFF",
    "txt": "TXT",
    "xls": "XLS",
    "xlsb": "XLSB",
    "xlsm": "XLSM",
    "xlsx": "XLSX",
    "xml": "XML",
    "xps": "XPS",
}
_NON_FORMAT_TOKENS = {"auto", "hint", "unknown"}


def _accepted_without_conflict(fact: FactRecordV2) -> bool:
    return fact.verification_state in _ACCEPTED_STATES and not fact.has_unresolved_conflict


def _has_accepted_canonical_fact(candidates: Iterable[FactRecordV2], field: str) -> bool:
    return any(fact.field == field and _accepted_without_conflict(fact) for fact in candidates)


def _claim_items(fact: FactRecordV2) -> list[dict[str, object]]:
    if not isinstance(fact.value, list):
        return []
    return [item for item in fact.value if isinstance(item, dict)]


def _clean_capabilities(items: list[dict[str, object]]) -> list[str]:
    values: list[str] = []
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text or _INTERNAL_TEXT_RE.search(text):
            continue
        values.append(text.rstrip(". ") + ".")
    return _deduplicate(values)


def _format_label(raw: str) -> str:
    return _ABBREVIATIONS.get(raw.casefold(), raw)


def _clean_formats(items: list[dict[str, object]]) -> list[str]:
    values: list[str] = []
    for item in items:
        text = str(item.get("text", "")).strip()
        match = _FORMAT_RE.match(text)
        if match is None:
            continue
        raw_format = match.group(2)
        if raw_format.casefold() in _NON_FORMAT_TOKENS:
            continue
        direction = "Input" if match.group(1).casefold() == "import" else "Output"
        values.append(f"{direction} format: {_format_label(raw_format)}")
    return _deduplicate(values)


def _clean_limitations(items: list[dict[str, object]]) -> list[str]:
    values: list[str] = []
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text or _INTERNAL_TEXT_RE.search(text):
            continue
        match = _LIMITATION_RE.match(text)
        if match is None:
            continue
        symbol = match.group(1).strip().rstrip(". ")
        # A bare Type.method token loses overload identity. Live Slides/Java
        # evidence proved this can turn one unsupported overload into the false
        # public claim that the working method itself is unimplemented. Only an
        # explicit signature is safe enough to project; richer current-source
        # limitation hints are handled by presentation_knowledge.py.
        if not symbol or "/" in symbol or "\\" in symbol or "(" not in symbol or ")" not in symbol:
            continue
        values.append(f"`{symbol}` is not implemented.")
    return _deduplicate(values)


def _deduplicate(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def _project_value(source: FactRecordV2, target_field: str) -> list[str]:
    items = _claim_items(source)
    if target_field == "product.capabilities":
        return _clean_capabilities(items)
    if target_field == "product.formats":
        return _clean_formats(items)
    if target_field == "product.limitations":
        return _clean_limitations(items)
    return []


def project_knowledge_into_canonical_facts(
    candidates: Iterable[FactRecordV2],
) -> list[FactRecordV2]:
    """Return conservative canonical projections from eligible selected knowledge.

    A projection is produced only when the target has no accepted fact already. The source must
    itself be verified or policy-approved and conflict-free. The projection cites that exact
    selected knowledge fact, so ProductFactsV2 retains complete item-to-canonical provenance.
    """

    materialized = list(candidates)
    projections: list[FactRecordV2] = []
    for source_field, target_field in _PROJECTION_MAP.items():
        if _has_accepted_canonical_fact(materialized, target_field):
            continue
        eligible = [
            fact
            for fact in materialized
            if fact.field == source_field and _accepted_without_conflict(fact)
        ]
        if not eligible:
            continue
        source = sorted(eligible, key=lambda fact: fact.fact_id)[0]
        value = _project_value(source, target_field)
        if not value:
            continue
        projections.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(target_field, "verified-knowledge-projection"),
                field=target_field,
                value=value,
                source=FactSourceV2(
                    source_type="approved_documentation",
                    location=f"{source.source.location}#canonical-projection",
                    source_revision=source.source.source_revision,
                    retrieved_at=source.source.retrieved_at,
                ),
                verification_state="verified",
                authoritative_owner="repository-owner",
                confidence=source.confidence,
                supporting_fact_ids=[source.fact_id],
                affected_surfaces=SURFACE_DEPENDENCIES[target_field],
            )
        )
    return projections


__all__ = ["project_knowledge_into_canonical_facts"]
