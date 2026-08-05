"""Normalize hierarchical assessment dispositions into exact source sections."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.document_structure import heading_identity, parse_headings


@dataclass(frozen=True)
class PreservedSection:
    title: str
    markdown: str
    source_byte_start: int
    source_byte_end: int


@dataclass(frozen=True)
class PreservedBlock:
    """One exact source-owned block with immutable byte coordinates."""

    markdown: str
    source_owner_id: str
    source_byte_start: int
    source_byte_end: int


def effective_disposition_ranges(
    assessment: ReadmeAssessmentV1,
    dispositions: set[str],
) -> list[tuple[int, int]]:
    """Return exact claim-owned ranges without inheriting container dispositions."""

    ranges: set[tuple[int, int]] = set()
    for claim in assessment.material_claims:
        if claim.disposition in dispositions:
            ranges.add((claim.source_byte_start, claim.source_byte_end))
    return sorted(ranges)


def effective_preserve_ranges(
    assessment: ReadmeAssessmentV1,
) -> list[tuple[int, int]]:
    return effective_disposition_ranges(assessment, {"preserve"})


def effective_correction_ranges(
    assessment: ReadmeAssessmentV1,
) -> list[tuple[int, int]]:
    return effective_disposition_ranges(
        assessment,
        {"investigate", "remove_update", "repair", "replace_generic", "rewrite"},
    )


def _source_slice(source: bytes, start: int, end: int) -> str:
    try:
        return source[start:end].decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("preserve disposition does not align to UTF-8 source bytes") from error


def preserved_h2_sections(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    replaceable_claim_ids: set[str],
    candidate: str,
) -> list[PreservedSection]:
    """Return exact non-replaceable leaf-preserve H2 sections."""

    source = source_text.encode("utf-8")
    coordinates = {
        (
            len(source_text[: heading.start].encode("utf-8")),
            len(source_text[: heading.section_end].encode("utf-8")),
        ): (heading.level, heading.title)
        for heading in parse_headings(source_text)
    }
    sections: list[PreservedSection] = []
    declared_identities: list[str] = []
    for section in assessment.sections:
        if section.level != 2 or section.disposition != "preserve":
            continue
        declared_identities.append(heading_identity(section.heading))
        effective_claims = [
            claim
            for claim in assessment.material_claims
            if section.source_byte_start <= claim.source_byte_start
            and claim.source_byte_end <= section.source_byte_end
            and claim.disposition == "preserve"
        ]
        nested_corrections = [
            child
            for child in assessment.sections
            if child.level > section.level
            and section.source_byte_start <= child.source_byte_start
            and child.source_byte_end <= section.source_byte_end
            and child.disposition in {"remove_update", "repair", "replace_generic", "rewrite"}
        ]
        descendant_reconciliation = any(
            claim.claim_id in replaceable_claim_ids for claim in effective_claims
        )
        structural = coordinates.get((section.source_byte_start, section.source_byte_end))
        if structural != (2, section.heading):
            raise ValueError(
                f"preserve disposition is not an exact CommonMark H2 section: {section.section_id}"
            )
        markdown = _source_slice(source, section.source_byte_start, section.source_byte_end)
        headings = parse_headings(markdown)
        if (
            not headings
            or headings[0].level != 2
            or headings[0].start != 0
            or headings[0].title != section.heading
            or any(heading.level < 2 for heading in headings)
        ):
            raise ValueError(
                f"preserved source section is structurally malformed: {section.heading}"
            )
        if descendant_reconciliation:
            continue
        if nested_corrections:
            raise ValueError(
                "preserve H2 contains correction-owned child sections and cannot be copied "
                f"whole: {section.heading}"
            )
        sections.append(
            PreservedSection(
                title=section.heading,
                markdown=markdown,
                source_byte_start=section.source_byte_start,
                source_byte_end=section.source_byte_end,
            )
        )
    identities = Counter(declared_identities)
    duplicates = sorted(identity for identity, count in identities.items() if count > 1)
    if duplicates:
        raise ValueError(f"preserve dispositions contain duplicate H2 headings: {duplicates}")
    return sections


def preserved_opening_claims(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    replaceable_claim_ids: set[str],
    candidate: str,
) -> list[PreservedBlock]:
    """Return exact leaf-preserve claims before the first source H2."""

    source = source_text.encode("utf-8")
    h2_starts = [
        len(source_text[: heading.start].encode("utf-8"))
        for heading in parse_headings(source_text)
        if heading.level == 2
    ]
    opening_end = min(h2_starts, default=len(source))
    preserve_ranges = effective_preserve_ranges(assessment)
    preserved: list[PreservedBlock] = []
    for claim in assessment.material_claims:
        if claim.source_byte_end > opening_end or not any(
            start <= claim.source_byte_start and claim.source_byte_end <= end
            for start, end in preserve_ranges
        ):
            continue
        text = _source_slice(source, claim.source_byte_start, claim.source_byte_end)
        if claim.claim_id not in replaceable_claim_ids and text not in candidate:
            preserved.append(
                PreservedBlock(
                    markdown=text,
                    source_owner_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                )
            )
    return preserved
