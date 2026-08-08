"""Reconcile source-exact spans with verified visitor-facing presentation policy."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.occurrences import find_aspose_link_occurrences
from readme_agent.links.terminology import (
    EnterpriseTerminologyCorrectionV1,
    canonicalize_enterprise_edition,
    enterprise_product_name_from_facts,
)
from readme_agent.presentation.verified_source_shell_policy import source_shell_policy_spans
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    public_text_corrections,
)

_FENCE = re.compile(r"(?ms)^```.*?^```[ \t]*$")
_MARKDOWN_LINK = re.compile(r"(!?)\[([^\]\n]*)\]\((https?://[^)\s]+)\)", re.IGNORECASE)
_AUTOLINK = re.compile(r"<(https?://[^>\s]+)>", re.IGNORECASE)
_HTML_ANCHOR = re.compile(
    r"<a\b[^>]*\bhref=[\"'](https?://[^\"']+)[\"'][^>]*>(.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)


class VerifiedSourcePolicyEditV1(BaseModel):
    """One exact source-byte correction owned by facts and/or governed policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_byte_start: int = Field(ge=0)
    source_byte_end: int = Field(gt=0)
    replacement: str
    fact_ids: list[str] = Field(default_factory=list)
    configured_standard_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _valid_range(self) -> VerifiedSourcePolicyEditV1:
        if self.source_byte_end <= self.source_byte_start:
            raise ValueError("verified source-policy correction requires a nonempty source span")
        return self


def _byte_offset(text: str, character_offset: int) -> int:
    return len(text[:character_offset].encode("utf-8"))


def _visitor_visible(markdown: str, start: int, end: int) -> bool:
    return not any(
        match.start() < end and start < match.end() for match in _FENCE.finditer(markdown)
    )


def _accepted_relationship_fact_id(facts: ProductFactsV2) -> str | None:
    fact_id = facts.selected_fact_ids.get("relationship.commercial_foss")
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact_id


def _edit(
    source_text: str,
    start: int,
    end: int,
    *,
    standard_id: str,
    rationale: str,
    replacement: str = "",
) -> VerifiedSourcePolicyEditV1:
    return VerifiedSourcePolicyEditV1(
        source_byte_start=_byte_offset(source_text, start),
        source_byte_end=_byte_offset(source_text, end),
        replacement=replacement,
        configured_standard_ids=[standard_id],
        rationale=rationale,
    )


def _expanded_link_span(markdown: str, start: int, end: int) -> tuple[int, int, str]:
    """Expand one URL to its visitor-visible link wrapper and safe plain-text replacement."""

    for pattern in (_MARKDOWN_LINK, _AUTOLINK, _HTML_ANCHOR):
        for match in pattern.finditer(markdown):
            if match.start() <= start and end <= match.end():
                if pattern is _MARKDOWN_LINK:
                    replacement = "" if match.group(1) else match.group(2)
                elif pattern is _HTML_ANCHOR:
                    replacement = re.sub(r"<[^>]+>", "", match.group(2))
                else:
                    replacement = ""
                return match.start(), match.end(), replacement
    return start, end, ""


def build_verified_source_policy_edits(
    source_text: str,
    facts: ProductFactsV2,
) -> list[VerifiedSourcePolicyEditV1]:
    """Return non-overlapping corrections that prevent policy-invalid source reinsertion."""

    relationship_fact_id = _accepted_relationship_fact_id(facts)
    enterprise_name = enterprise_product_name_from_facts(facts)
    canonical = f"{enterprise_name} Enterprise Edition" if enterprise_name else ""
    terminology: list[EnterpriseTerminologyCorrectionV1] = []
    if enterprise_name:
        _, terminology = canonicalize_enterprise_edition(
            source_text,
            enterprise_product_name=enterprise_name,
        )
    if terminology and relationship_fact_id is None:
        raise ValueError(
            "verified source terminology correction requires an accepted commercial/FOSS "
            "relationship fact"
        )
    edits = [
        _edit(
            source_text,
            span.character_start,
            span.character_end,
            standard_id=span.standard_id,
            rationale=span.rationale,
            replacement=span.replacement,
        )
        for span in source_shell_policy_spans(source_text)
    ]
    occupied = [(item.source_byte_start, item.source_byte_end) for item in edits]

    for occurrence in find_aspose_link_occurrences(source_text):
        start, end, replacement = _expanded_link_span(
            source_text,
            occurrence.character_start,
            occurrence.character_end,
        )
        if not _visitor_visible(source_text, start, end):
            continue
        byte_start = _byte_offset(source_text, start)
        byte_end = _byte_offset(source_text, end)
        if any(
            existing_start < byte_end and byte_start < existing_end
            for existing_start, existing_end in occupied
        ):
            continue
        terminology_overlap = any(
            correction.character_start < end and start < correction.character_end
            for correction in terminology
        )
        if terminology_overlap:
            replacement = canonical if relationship_fact_id and canonical else ""
        occupied.append((byte_start, byte_end))
        edits.append(
            VerifiedSourcePolicyEditV1(
                source_byte_start=_byte_offset(source_text, start),
                source_byte_end=_byte_offset(source_text, end),
                replacement=replacement,
                fact_ids=[relationship_fact_id]
                if terminology_overlap and relationship_fact_id
                else [],
                configured_standard_ids=[
                    "readme.contextual_links",
                    *(["readme.enterprise_edition_terminology"] if terminology_overlap else []),
                ],
                rationale=(
                    "Remove source-owned Aspose link allocation before the verified contextual "
                    "catalog selects the final bounded links."
                ),
            )
        )

    if enterprise_name:
        for correction in terminology:
            start = correction.character_start
            end = correction.character_end
            if not _visitor_visible(source_text, start, end):
                continue
            byte_start = _byte_offset(source_text, start)
            byte_end = _byte_offset(source_text, end)
            if any(
                existing_start < byte_end and byte_start < existing_end
                for existing_start, existing_end in occupied
            ):
                continue
            occupied.append((byte_start, byte_end))
            edits.append(
                VerifiedSourcePolicyEditV1(
                    source_byte_start=_byte_offset(source_text, start),
                    source_byte_end=_byte_offset(source_text, end),
                    replacement=correction.replacement if relationship_fact_id else "",
                    fact_ids=[relationship_fact_id] if relationship_fact_id else [],
                    configured_standard_ids=["readme.enterprise_edition_terminology"],
                    rationale=(
                        "Replace prohibited Aspose edition terminology with the configured "
                        "Enterprise Edition visitor name."
                    ),
                )
            )
    for public_correction in public_text_corrections(
        source_text, canonical_abbreviations_from_facts(facts)
    ):
        byte_start = _byte_offset(source_text, public_correction.character_start)
        byte_end = _byte_offset(source_text, public_correction.character_end)
        if any(
            existing_start < byte_end and byte_start < existing_end
            for existing_start, existing_end in occupied
        ):
            continue
        occupied.append((byte_start, byte_end))
        edits.append(
            VerifiedSourcePolicyEditV1(
                source_byte_start=byte_start,
                source_byte_end=byte_end,
                replacement=public_correction.replacement,
                configured_standard_ids=[public_correction.standard_id],
                rationale=public_correction.rationale,
            )
        )
    return sorted(edits, key=lambda item: item.source_byte_start)
