"""Canonicalize and validate Aspose Enterprise Edition visitor terminology."""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

_FENCE = re.compile(r"(?ms)^```.*?^```[ \t]*$")
_PRODUCT_LINK = re.compile(
    r"\[([^\]]+)\]\((https://products\.aspose\.com/[^)\s]+)\)",
    re.IGNORECASE,
)
_ASPOSE_SCOPE = re.compile(r"\bAspose(?:\.[A-Za-z0-9]+)?\b|https://[^ \t)\]]*aspose\.com", re.I)
_PROHIBITED = re.compile(
    r"\b(?:"
    r"(?:full[- ]featured\s+|full\s+)?commercial(?:\s+On-Premise)?"
    r"|On-Premise|paid|premium|proprietary|full"
    r")\s+(?:edition|product|package|library)\b",
    re.IGNORECASE,
)
_COMMERCIAL_ASPOSE = re.compile(
    r"\b(?:the\s+)?(?:full[- ]featured\s+|full\s+)?commercial\s+"
    r"Aspose(?:\.[A-Za-z0-9]+)?(?:\s+for\s+[A-Za-z0-9.+# -]+)?"
    r"(?:\s+On-Premise)?\s+(?:edition|product|package|library)\b",
    re.IGNORECASE,
)


class EnterpriseTerminologyCorrectionV1(BaseModel):
    """One deterministic visitor-language correction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    original: str
    replacement: str
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=0)


class EnterpriseTerminologyFindingV1(BaseModel):
    """One prohibited Aspose edition label that remains visitor-visible."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["prohibited_descriptor", "product_link_label"]
    excerpt: str
    character_start: int = Field(ge=0)
    character_end: int = Field(ge=0)


def _visitor_ranges(markdown: str) -> list[tuple[int, int]]:
    """Return non-fenced ranges; source code is protected rather than rewritten."""

    ranges: list[tuple[int, int]] = []
    cursor = 0
    for match in _FENCE.finditer(markdown):
        if cursor < match.start():
            ranges.append((cursor, match.start()))
        cursor = match.end()
    if cursor < len(markdown):
        ranges.append((cursor, len(markdown)))
    return ranges


def _scoped_chunks(markdown: str) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    for range_start, range_end in _visitor_ranges(markdown):
        text = markdown[range_start:range_end]
        cursor = 0
        for piece in re.split(r"(\n\s*\n)", text):
            start = range_start + cursor
            end = start + len(piece)
            cursor += len(piece)
            if piece.strip() and _ASPOSE_SCOPE.search(piece):
                chunks.append((start, end, piece))
    return chunks


def canonicalize_enterprise_edition(
    markdown: str,
    *,
    enterprise_product_name: str,
) -> tuple[str, list[EnterpriseTerminologyCorrectionV1]]:
    """Replace only Aspose-scoped stale edition labels outside protected code."""

    canonical = f"{enterprise_product_name.strip()} Enterprise Edition"
    corrections: list[EnterpriseTerminologyCorrectionV1] = []
    for chunk_start, _, chunk in _scoped_chunks(markdown):
        matches = [*_COMMERCIAL_ASPOSE.finditer(chunk), *_PROHIBITED.finditer(chunk)]
        occupied: list[tuple[int, int]] = []
        for match in sorted(matches, key=lambda item: (item.start(), -(item.end() - item.start()))):
            absolute_start = chunk_start + match.start()
            absolute_end = chunk_start + match.end()
            if any(start < absolute_end and absolute_start < end for start, end in occupied):
                continue
            occupied.append((absolute_start, absolute_end))
            replacement = (
                f"the {canonical}" if match.group(0).casefold().startswith("the ") else canonical
            )
            corrections.append(
                EnterpriseTerminologyCorrectionV1(
                    original=markdown[absolute_start:absolute_end],
                    replacement=replacement,
                    character_start=absolute_start,
                    character_end=absolute_end,
                )
            )
    rendered = markdown
    for correction in sorted(corrections, key=lambda item: item.character_start, reverse=True):
        rendered = (
            rendered[: correction.character_start]
            + correction.replacement
            + rendered[correction.character_end :]
        )
    return rendered, sorted(corrections, key=lambda item: item.character_start)


def find_enterprise_terminology_findings(
    markdown: str,
) -> list[EnterpriseTerminologyFindingV1]:
    """Find stale Aspose labels and noncanonical products.aspose.com anchors."""

    findings: list[EnterpriseTerminologyFindingV1] = []
    for chunk_start, _, chunk in _scoped_chunks(markdown):
        for match in _PROHIBITED.finditer(chunk):
            findings.append(
                EnterpriseTerminologyFindingV1(
                    kind="prohibited_descriptor",
                    excerpt=match.group(0),
                    character_start=chunk_start + match.start(),
                    character_end=chunk_start + match.end(),
                )
            )
        for match in _PRODUCT_LINK.finditer(chunk):
            hostname = (urlparse(match.group(2)).hostname or "").casefold()
            if hostname != "products.aspose.com" or "Enterprise Edition" in match.group(1):
                continue
            findings.append(
                EnterpriseTerminologyFindingV1(
                    kind="product_link_label",
                    excerpt=match.group(0),
                    character_start=chunk_start + match.start(),
                    character_end=chunk_start + match.end(),
                )
            )
    return sorted(findings, key=lambda finding: finding.character_start)
