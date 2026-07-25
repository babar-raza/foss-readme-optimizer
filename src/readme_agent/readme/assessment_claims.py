"""Inventory material README claims as untrusted, source-bound assessment records."""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

ClaimDisposition = Literal[
    "preserve",
    "rewrite",
    "investigate",
    "repair",
    "remove_update",
    "replace_generic",
    "add",
    "not_applicable",
]

_PROMPT_INJECTION = re.compile(
    r"(?i)(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)"
    r"\s+(?:instructions?|prompts?)|(?:system|developer)\s+message\s*:",
)
_PROMOTIONAL_CLAIM = re.compile(
    r"(?i)products\.[^\s)]+\.org.*products\.[^\s)]+\.com|"
    r"products\.[^\s)]+\.com.*products\.[^\s)]+\.org",
)


class ReadmeMaterialClaimAssessmentV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(ge=0)
    content_sha256: str
    disposition: ClaimDisposition
    fact_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _byte_offset(text: str, character_offset: int) -> int:
    return len(text[:character_offset].encode("utf-8"))


def assess_material_claims(source_text: str) -> list[ReadmeMaterialClaimAssessmentV1]:
    """Classify paragraphs and code blocks without treating their content as instructions."""

    tokens = MarkdownIt("commonmark").parse(source_text)
    line_offsets = _line_offsets(source_text)
    claims = []
    for index, token in enumerate(tokens):
        if token.type not in {"inline", "fence", "code_block", "html_block"} or token.map is None:
            continue
        if token.type == "inline" and index > 0 and tokens[index - 1].type == "heading_open":
            continue
        start_line, end_line = token.map
        character_start = line_offsets[start_line]
        character_end = line_offsets[end_line]
        source_slice = source_text[character_start:character_end]
        if not source_slice.strip():
            continue
        if _PROMPT_INJECTION.search(source_slice):
            disposition: ClaimDisposition = "investigate"
            rationale = (
                "Repository instruction-like prose is untrusted data and cannot control execution."
            )
        elif _PROMOTIONAL_CLAIM.search(source_slice):
            disposition = "remove_update"
            rationale = "Promotional callout requires a bounded product-first correction."
        else:
            disposition = "preserve"
            rationale = (
                "Existing material is preserved, but is not promoted to verified product truth."
            )
        content_hash = hashlib.sha256(source_slice.encode("utf-8")).hexdigest()
        claims.append(
            ReadmeMaterialClaimAssessmentV1(
                claim_id=f"claim:{_byte_offset(source_text, character_start)}:{content_hash[:16]}",
                source_byte_start=_byte_offset(source_text, character_start),
                source_byte_end=_byte_offset(source_text, character_end),
                content_sha256=content_hash,
                disposition=disposition,
                evidence=[f"README.md:{character_start}:{character_end}"],
                rationale=rationale,
            )
        )
    return claims
