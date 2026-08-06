"""Normalize hierarchical assessment dispositions into exact source sections."""

from __future__ import annotations

import hashlib
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


@dataclass(frozen=True)
class VerifiedSourcePreservationSelectionV1:
    """Hash-bound source-claim categories controlling exact preservation."""

    source_sha256: str
    assessment_hash: str
    fact_authorized_claim_ids: frozenset[str]
    correction_candidate_claim_ids: frozenset[str]
    resolved_claim_ids: frozenset[str]

    @property
    def non_preservable_claim_ids(self) -> frozenset[str]:
        return self.correction_candidate_claim_ids | self.resolved_claim_ids

    def validate(self, source_text: str, assessment: ReadmeAssessmentV1) -> None:
        if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != self.source_sha256:
            raise ValueError("verified source-preservation selection is stale for source bytes")
        if assessment.canonical_hash() != self.assessment_hash:
            raise ValueError("verified source-preservation selection is stale for assessment")
        claim_ids = {claim.claim_id for claim in assessment.material_claims}
        selected = (
            self.fact_authorized_claim_ids
            | self.correction_candidate_claim_ids
            | self.resolved_claim_ids
        )
        if not selected.issubset(claim_ids):
            raise ValueError("verified source-preservation selection cites an unknown claim")
        if self.fact_authorized_claim_ids & self.correction_candidate_claim_ids:
            raise ValueError("source claim cannot be both fact-authorized and correction-required")
        preserve_ids = {
            claim.claim_id
            for claim in assessment.material_claims
            if claim.disposition == "preserve"
        }
        if preserve_ids != (self.fact_authorized_claim_ids | self.correction_candidate_claim_ids):
            raise ValueError("verified preserve claims require one exhaustive assurance category")


def build_verified_source_preservation_selection(
    source_text: str,
    assessment: ReadmeAssessmentV1,
    *,
    fact_authorized_ranges: list[tuple[int, int]],
    correction_candidate_ranges: list[tuple[int, int]],
    resolved_claim_ids: set[str],
) -> VerifiedSourcePreservationSelectionV1:
    """Convert exact assurance ranges into a stale-resistant preservation selection."""

    claims_by_range = {
        (claim.source_byte_start, claim.source_byte_end): claim.claim_id
        for claim in assessment.material_claims
    }

    def exact_claim_ids(ranges: list[tuple[int, int]], category: str) -> frozenset[str]:
        if len(ranges) != len(set(ranges)):
            raise ValueError(f"{category} assurance ranges contain duplicates")
        try:
            return frozenset(claims_by_range[coordinates] for coordinates in ranges)
        except KeyError as error:
            raise ValueError(
                f"{category} assurance range is partial, spoofed, or stale: {error.args[0]}"
            ) from error

    selection = VerifiedSourcePreservationSelectionV1(
        source_sha256=hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        assessment_hash=assessment.canonical_hash(),
        fact_authorized_claim_ids=exact_claim_ids(
            fact_authorized_ranges,
            "fact-authorized",
        ),
        correction_candidate_claim_ids=exact_claim_ids(
            correction_candidate_ranges,
            "correction-candidate",
        ),
        resolved_claim_ids=frozenset(resolved_claim_ids),
    )
    selection.validate(source_text, assessment)
    return selection


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
    resolved_claim_ids: set[str],
    candidate: str,
    *,
    preservation_selection: VerifiedSourcePreservationSelectionV1 | None = None,
) -> list[PreservedSection]:
    """Return exact non-replaceable leaf-preserve H2 sections."""

    source = source_text.encode("utf-8")
    if preservation_selection is not None:
        preservation_selection.validate(source_text, assessment)
        resolved_claim_ids = set(preservation_selection.resolved_claim_ids)
        non_preservable_claim_ids = set(preservation_selection.non_preservable_claim_ids)
        fact_authorized_claim_ids = set(preservation_selection.fact_authorized_claim_ids)
    else:
        non_preservable_claim_ids = set(resolved_claim_ids)
        fact_authorized_claim_ids = {
            claim.claim_id
            for claim in assessment.material_claims
            if claim.disposition == "preserve"
        }
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
            claim.claim_id in resolved_claim_ids for claim in effective_claims
        )
        correction_candidate = any(
            claim.claim_id in non_preservable_claim_ids for claim in effective_claims
        )
        incomplete_assurance = any(
            claim.claim_id not in fact_authorized_claim_ids for claim in effective_claims
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
        if descendant_reconciliation or correction_candidate or incomplete_assurance:
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
    resolved_claim_ids: set[str],
    candidate: str,
    *,
    preservation_selection: VerifiedSourcePreservationSelectionV1 | None = None,
) -> list[PreservedBlock]:
    """Return exact leaf-preserve claims before the first source H2."""

    source = source_text.encode("utf-8")
    if preservation_selection is not None:
        preservation_selection.validate(source_text, assessment)
        non_preservable_claim_ids = set(preservation_selection.non_preservable_claim_ids)
        fact_authorized_claim_ids = set(preservation_selection.fact_authorized_claim_ids)
    else:
        non_preservable_claim_ids = set(resolved_claim_ids)
        fact_authorized_claim_ids = {
            claim.claim_id
            for claim in assessment.material_claims
            if claim.disposition == "preserve"
        }
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
        if (
            claim.claim_id in fact_authorized_claim_ids
            and claim.claim_id not in non_preservable_claim_ids
            and text not in candidate
        ):
            preserved.append(
                PreservedBlock(
                    markdown=text,
                    source_owner_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                )
            )
    return preserved
