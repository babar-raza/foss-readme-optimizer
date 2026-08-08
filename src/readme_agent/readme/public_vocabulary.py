"""Define fact-aware canonical technical vocabulary for public README text."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from readme_agent.facts.schema_v2 import ProductFactsV2

DEFAULT_TECHNICAL_ABBREVIATIONS = (
    "3D",
    "3MF",
    "API",
    "BMP",
    "CLI",
    "COLLADA",
    "CSV",
    "CID",
    "CIE",
    "CGM",
    "CMap",
    "CMaps",
    "CMS",
    "DOC",
    "DOCX",
    "DSC",
    "EPS",
    "FBX",
    "FOSS",
    "GIF",
    "GLB",
    "GLTF",
    "HTML",
    "HTTP",
    "HTTPS",
    "JPEG",
    "JPG",
    "JSON",
    "MCP",
    "MIME",
    "OBJ",
    "ODP",
    "ODS",
    "PBR",
    "PDF",
    "PNG",
    "PPT",
    "PPTX",
    "PS",
    "RTF",
    "SDK",
    "SEO",
    "SFNT",
    "SVG",
    "TIFF",
    "TTF",
    "URI",
    "URL",
    "VM",
    "XLS",
    "XLSX",
    "XML",
    "XPS",
    "ZIP",
)
DOCUMENT_FORMAT_ABBREVIATIONS = frozenset(
    {
        "3MF",
        "BMP",
        "COLLADA",
        "CSV",
        "CGM",
        "DOC",
        "DOCX",
        "EPS",
        "FBX",
        "GIF",
        "GLB",
        "GLTF",
        "HTML",
        "JPEG",
        "JPG",
        "JSON",
        "OBJ",
        "ODP",
        "ODS",
        "PDF",
        "PNG",
        "PPT",
        "PPTX",
        "PS",
        "RTF",
        "SVG",
        "TIFF",
        "XLS",
        "XLSX",
        "XML",
        "XPS",
        "ZIP",
    }
)
_FACT_ABBREVIATION = re.compile(r"(?<![A-Za-z0-9_-])([A-Z][A-Z0-9]{2,7})(?![A-Za-z0-9_-])")
_DYNAMIC_STOPWORDS = {
    "ALL",
    "AND",
    "FALSE",
    "FOR",
    "FROM",
    "INTO",
    "NONE",
    "NOT",
    "ONLY",
    "OR",
    "THE",
    "TODO",
    "TRUE",
    "WITH",
}
_DYNAMIC_FIELDS = {
    "product.capabilities",
    "product.formats",
    "product.problems_solved",
}


def compile_abbreviation_pattern(terms: Iterable[str]) -> re.Pattern[str]:
    """Compile a boundary-aware case-insensitive pattern for canonical terms."""

    values = sorted(set(terms), key=lambda item: (-len(item), item))
    return re.compile(
        r"(?<![A-Za-z0-9_-])(" + "|".join(map(re.escape, values)) + r")(?![A-Za-z0-9_-])",
        re.IGNORECASE,
    )


def canonical_abbreviations_from_facts(facts: ProductFactsV2 | None) -> tuple[str, ...]:
    """Combine governed common abbreviations with accepted repository vocabulary."""

    values = set(DEFAULT_TECHNICAL_ABBREVIATIONS)
    if facts is None:
        return tuple(sorted(values))
    reserved_identity_words: set[str] = set()
    try:
        identity = facts.selected_fact("product.identity")
    except KeyError:
        identity = None
    if identity is not None:
        identity_values = (
            identity.value.values() if isinstance(identity.value, dict) else [identity.value]
        )
        for identity_value in identity_values:
            if isinstance(identity_value, str):
                reserved_identity_words.update(
                    word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z0-9]+", identity_value)
                )

    def visit(value: object) -> None:
        if isinstance(value, str):
            values.update(
                token
                for token in _FACT_ABBREVIATION.findall(value)
                if token not in _DYNAMIC_STOPWORDS
                and token.casefold() not in reserved_identity_words
            )
        elif isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for field in _DYNAMIC_FIELDS:
        fact_id = facts.selected_fact_ids.get(field)
        if fact_id is None:
            continue
        fact = facts.fact_by_id(fact_id)
        if (
            fact.verification_state in {"verified", "policy_approved"}
            and not fact.has_unresolved_conflict
        ):
            visit(fact.value)
    return tuple(sorted(values))


def canonicalize_abbreviations(
    value: str,
    canonical_terms: Iterable[str] = DEFAULT_TECHNICAL_ABBREVIATIONS,
) -> str:
    """Use configured canonical casing for technical abbreviations in public text."""

    canonical = {item.casefold(): item for item in canonical_terms}
    return compile_abbreviation_pattern(canonical.values()).sub(
        lambda match: canonical[match.group(0).casefold()], value
    )


__all__ = [
    "DEFAULT_TECHNICAL_ABBREVIATIONS",
    "DOCUMENT_FORMAT_ABBREVIATIONS",
    "canonical_abbreviations_from_facts",
    "canonicalize_abbreviations",
    "compile_abbreviation_pattern",
]
