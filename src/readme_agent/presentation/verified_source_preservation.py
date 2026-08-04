"""Compose exact source-preservation dispositions into verified template output."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from readme_agent.presentation.verified_preservation_sections import (
    preserved_h2_sections,
    preserved_opening_claims,
)
from readme_agent.presentation.verified_preservation_segments import (
    CandidateEdit,
    apply_edit,
    navigation_edit,
    rebase_provenance,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import heading_identity, parse_headings


@dataclass(frozen=True)
class VerifiedSourceComposition:
    candidate: str
    provenance: list[CandidateContentProvenanceV1]


def _separated_exact_blocks(blocks: list[str]) -> str:
    """Keep each source block exact while generating a structural boundary after it."""

    return "".join(block + ("" if block.endswith("\n\n") else "\n\n") for block in blocks)


def _missing_preserve_blocks(
    candidate: str,
    source_text: str,
    assessment: ReadmeAssessmentV1,
    replaceable_claim_ids: set[str],
) -> list[str]:
    """Return exact preserve claims not already represented with full multiplicity."""

    source = source_text.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    navigation_ranges = [
        (
            len(source_text[: heading.start].encode("utf-8")),
            len(source_text[: heading.section_end].encode("utf-8")),
        )
        for heading in parse_headings(source_text)
        if heading.level == 2 and heading_identity(heading.title) == "navigation"
    ]

    def is_navigation_claim(start: int, end: int) -> bool:
        return any(
            nav_start <= start and end <= nav_end for nav_start, nav_end in navigation_ranges
        )

    remaining: dict[str, int] = {}
    blocks: dict[str, bytes] = {}
    for claim in assessment.material_claims:
        if (
            claim.disposition != "preserve"
            or claim.claim_id in replaceable_claim_ids
            or is_navigation_claim(claim.source_byte_start, claim.source_byte_end)
        ):
            continue
        block = source[claim.source_byte_start : claim.source_byte_end]
        blocks.setdefault(claim.content_sha256, block)
        remaining.setdefault(claim.content_sha256, candidate_bytes.count(block))
    missing: list[str] = []
    for claim in assessment.material_claims:
        if (
            claim.disposition != "preserve"
            or claim.claim_id in replaceable_claim_ids
            or is_navigation_claim(claim.source_byte_start, claim.source_byte_end)
        ):
            continue
        if remaining[claim.content_sha256] > 0:
            remaining[claim.content_sha256] -= 1
            continue
        try:
            missing.append(blocks[claim.content_sha256].decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ValueError("preserve claim does not align to UTF-8 source bytes") from error
    return missing


def compose_verified_source_preservation(
    candidate: str,
    source_text: str,
    assessment: ReadmeAssessmentV1,
    replaceable_claim_ids: set[str],
    provenance: list[CandidateContentProvenanceV1],
) -> VerifiedSourceComposition:
    """Apply exact preserve dispositions without duplicating the source document shell."""

    preserved_sections = preserved_h2_sections(
        source_text,
        assessment,
        replaceable_claim_ids,
        candidate,
    )
    candidate_headings = [heading for heading in parse_headings(candidate) if heading.level == 2]
    block_by_identity = {heading_identity(heading.title): heading for heading in candidate_headings}
    if len(block_by_identity) != len(candidate_headings):
        raise ValueError("compiled candidate contains duplicate H2 headings")
    additions = [
        section.markdown
        for section in preserved_sections
        if heading_identity(section.title) not in block_by_identity
    ]
    opening_claims = preserved_opening_claims(
        source_text,
        assessment,
        replaceable_claim_ids,
        candidate,
    )
    edits: list[CandidateEdit] = []
    if opening_claims:
        opening_end = candidate_headings[0].start if candidate_headings else len(candidate)
        opening_byte = len(candidate[:opening_end].encode("utf-8"))
        edits.append(CandidateEdit(opening_byte, opening_byte, "".join(opening_claims) + "\n"))
    if additions:
        license_heading = next(
            (
                heading
                for heading in candidate_headings
                if heading_identity(heading.title) == "license"
            ),
            None,
        )
        insertion_character = license_heading.start if license_heading else len(candidate)
        insertion_byte = len(candidate[:insertion_character].encode("utf-8"))
        edits.append(
            CandidateEdit(insertion_byte, insertion_byte, _separated_exact_blocks(additions))
        )

    composed = candidate
    composed_provenance = provenance
    for edit in sorted(edits, key=lambda item: item.byte_start, reverse=True):
        composed = apply_edit(composed, edit)
        composed_provenance = rebase_provenance(composed_provenance, edit, composed)
    missing_blocks = _missing_preserve_blocks(
        composed,
        source_text,
        assessment,
        replaceable_claim_ids,
    )
    if missing_blocks:
        preserved_heading = "Preserved repository details"
        headings = [heading for heading in parse_headings(composed) if heading.level == 2]
        if any(
            heading_identity(heading.title) == heading_identity(preserved_heading)
            for heading in headings
        ):
            raise ValueError("source-preservation detail heading collides with candidate content")
        license_heading = next(
            (heading for heading in headings if heading_identity(heading.title) == "license"),
            None,
        )
        insertion_character = license_heading.start if license_heading else len(composed)
        detail_edit = CandidateEdit(
            len(composed[:insertion_character].encode("utf-8")),
            len(composed[:insertion_character].encode("utf-8")),
            f"## {preserved_heading}\n\n" + _separated_exact_blocks(missing_blocks),
        )
        composed = apply_edit(composed, detail_edit)
        composed_provenance = rebase_provenance(composed_provenance, detail_edit, composed)
    toc_edit = navigation_edit(composed)
    composed = apply_edit(composed, toc_edit)
    composed_provenance = rebase_provenance(composed_provenance, toc_edit, composed)

    headings = parse_headings(composed)
    h1_count = sum(heading.level == 1 for heading in headings)
    h2_identities = [heading_identity(heading.title) for heading in headings if heading.level == 2]
    duplicate_h2s = sorted(
        identity for identity, count in Counter(h2_identities).items() if count > 1
    )
    if h1_count != 1 or duplicate_h2s:
        raise ValueError(
            "source-preserving composition introduced an invalid document shell: "
            f"h1_count={h1_count}, duplicate_h2s={duplicate_h2s}"
        )
    if composed.rstrip() + "\n" != composed:
        raise ValueError("source-preserving composition produced a noncanonical trailing boundary")
    return VerifiedSourceComposition(candidate=composed, provenance=composed_provenance)
