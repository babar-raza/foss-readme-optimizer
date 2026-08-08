"""Compose exact source-preservation dispositions into verified template output."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_preservation_sections import (
    PreservedBlock,
    VerifiedSourcePreservationSelectionV1,
    preserved_h2_sections,
    preserved_opening_claims,
)
from readme_agent.presentation.verified_preservation_segments import (
    CandidateEdit,
    apply_edit,
    navigation_edit,
    rebase_provenance,
    rebase_source_placements,
)
from readme_agent.presentation.verified_source_density import apply_verified_source_density
from readme_agent.presentation.verified_source_detail_routing import (
    route_source_detail_blocks,
    source_section_routes_to_canonical_contract,
)
from readme_agent.presentation.verified_source_placements import (
    exclude_source_placements_from_provenance,
    replacement_placements,
    resolve_preserve_claim_placements,
    separated_exact_blocks,
)
from readme_agent.presentation.verified_source_policy import VerifiedSourcePolicyEditV1
from readme_agent.presentation.verified_source_policy_application import (
    apply_verified_source_policy,
    rebase_source_policy_corrections,
)
from readme_agent.presentation.verified_source_shell_policy import (
    fully_omitted_by_shell_policy,
    unapplied_shell_omission_corrections,
    validate_compiled_source_shell,
)
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import heading_identity, parse_headings
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


@dataclass(frozen=True)
class VerifiedSourceComposition:
    candidate: str
    provenance: list[CandidateContentProvenanceV1]
    source_placements: list[ExactSourcePlacementV1]
    source_policy_corrections: list[SourceClaimPolicyCorrectionV1]


def compose_verified_source_preservation(
    candidate: str,
    source_text: str,
    facts: ProductFactsV2,
    assessment: ReadmeAssessmentV1,
    resolved_claim_ids: set[str],
    provenance: list[CandidateContentProvenanceV1],
    source_policy_edits: list[VerifiedSourcePolicyEditV1] | None = None,
    *,
    preservation_selection: VerifiedSourcePreservationSelectionV1 | None = None,
) -> VerifiedSourceComposition:
    """Apply exact preserve dispositions without duplicating the source document shell."""

    policy_edits = source_policy_edits or []
    preserved_sections = preserved_h2_sections(
        source_text,
        assessment,
        resolved_claim_ids,
        candidate,
        preservation_selection=preservation_selection,
    )
    candidate_headings = [heading for heading in parse_headings(candidate) if heading.level == 2]
    block_by_identity = {heading_identity(heading.title): heading for heading in candidate_headings}
    if len(block_by_identity) != len(candidate_headings):
        raise ValueError("compiled candidate contains duplicate H2 headings")
    additions = [
        PreservedBlock(
            markdown=section.markdown,
            source_owner_id=next(
                item.section_id
                for item in assessment.sections
                if item.level == 2
                and item.source_byte_start == section.source_byte_start
                and item.source_byte_end == section.source_byte_end
            ),
            source_byte_start=section.source_byte_start,
            source_byte_end=section.source_byte_end,
        )
        for section in preserved_sections
        if heading_identity(section.title) not in block_by_identity
        and not source_section_routes_to_canonical_contract(
            source_text,
            assessment,
            facts,
            section.source_byte_start,
            section.source_byte_end,
        )
        and not fully_omitted_by_shell_policy(
            section.source_byte_start,
            section.source_byte_end,
            policy_edits,
        )
    ]
    opening_claims = preserved_opening_claims(
        source_text,
        assessment,
        resolved_claim_ids,
        candidate,
        preservation_selection=preservation_selection,
    )
    opening_claims = [
        block
        for block in opening_claims
        if not fully_omitted_by_shell_policy(
            block.source_byte_start,
            block.source_byte_end,
            policy_edits,
        )
    ]
    edits: list[tuple[CandidateEdit, list[PreservedBlock], str, str]] = []
    if opening_claims:
        opening_end = candidate_headings[0].start if candidate_headings else len(candidate)
        opening_byte = len(candidate[:opening_end].encode("utf-8"))
        replacement = "".join(block.markdown for block in opening_claims) + "\n"
        edits.append(
            (CandidateEdit(opening_byte, opening_byte, replacement), opening_claims, "opening", "")
        )
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
            (
                CandidateEdit(
                    insertion_byte,
                    insertion_byte,
                    separated_exact_blocks(additions),
                ),
                additions,
                "section",
                "",
            )
        )

    composed = candidate
    composed_provenance = provenance
    source_placements: list[ExactSourcePlacementV1] = []
    for edit, blocks, prefix, leading in sorted(
        edits, key=lambda item: item[0].byte_start, reverse=True
    ):
        source_placements = rebase_source_placements(source_placements, edit)
        composed = apply_edit(composed, edit)
        composed_provenance = rebase_provenance(composed_provenance, edit, composed)
        source_placements.extend(
            replacement_placements(
                blocks,
                edit,
                f"source.{prefix}",
                leading=leading,
                separated=prefix != "opening",
            )
        )
    non_preservable_claim_ids = (
        set(preservation_selection.non_preservable_claim_ids)
        if preservation_selection is not None
        else resolved_claim_ids
    )
    fact_authorized_claim_ids = (
        set(preservation_selection.fact_authorized_claim_ids)
        if preservation_selection is not None
        else set()
    )
    missing_blocks, adopted_placements = resolve_preserve_claim_placements(
        composed,
        source_text,
        assessment,
        non_preservable_claim_ids,
        fact_authorized_claim_ids,
        source_placements,
    )
    missing_blocks = [
        block
        for block in missing_blocks
        if not fully_omitted_by_shell_policy(
            block.source_byte_start,
            block.source_byte_end,
            policy_edits,
        )
    ]
    source_placements.extend(adopted_placements)
    if missing_blocks:
        routed = route_source_detail_blocks(
            source_text,
            assessment,
            facts,
            missing_blocks,
            composed,
            composed_provenance,
        )
        for (target_title, summary), blocks in sorted(routed.items(), reverse=True):
            headings = [heading for heading in parse_headings(composed) if heading.level == 2]
            target = next(
                (
                    heading
                    for heading in headings
                    if heading_identity(heading.title) == heading_identity(target_title)
                ),
                None,
            )
            if target is None:
                license_heading = next(
                    (
                        heading
                        for heading in headings
                        if heading_identity(heading.title) == "license"
                    ),
                    None,
                )
                insertion_character = (
                    license_heading.start if license_heading is not None else len(composed)
                )
                insertion_byte = len(composed[:insertion_character].encode("utf-8"))
                leading = f"## {target_title}\n\n"
                trailing = ""
            else:
                insertion_byte = len(composed[: target.section_end].encode("utf-8"))
                leading = f"<details>\n<summary>{summary}</summary>\n\n"
                trailing = "</details>\n\n"
            source_detail = separated_exact_blocks(blocks)
            replacement = leading + source_detail + trailing
            detail_edit = CandidateEdit(insertion_byte, insertion_byte, replacement)
            source_placements = rebase_source_placements(source_placements, detail_edit)
            composed = apply_edit(composed, detail_edit)
            composed_provenance = rebase_provenance(composed_provenance, detail_edit, composed)
            source_placements.extend(
                replacement_placements(
                    blocks,
                    detail_edit,
                    f"source.canonical-detail.{heading_identity(target_title)}",
                    leading=leading,
                )
            )
            identity = heading_identity(target_title)
            composed_provenance.append(
                CandidateContentProvenanceV1(
                    provenance_id=f"source.canonical-detail.{identity}.open",
                    candidate_byte_start=insertion_byte,
                    candidate_byte_end=insertion_byte + len(leading.encode("utf-8")),
                    configured_standard_ids=["readme.source_detail_routing"],
                    rationale=(
                        "Bind the canonical source-detail destination to the governed "
                        "detail-routing standard."
                    ),
                )
            )
            if trailing:
                composed_provenance.append(
                    CandidateContentProvenanceV1(
                        provenance_id=f"source.canonical-detail.{identity}.close",
                        candidate_byte_start=(
                            insertion_byte
                            + len(leading.encode("utf-8"))
                            + len(source_detail.encode("utf-8"))
                        ),
                        candidate_byte_end=insertion_byte + len(replacement.encode("utf-8")),
                        configured_standard_ids=["readme.source_detail_routing"],
                        rationale=(
                            "Bind the canonical collapsible source-detail closing to the "
                            "governed detail-routing standard."
                        ),
                    ),
                )
    composed_provenance = exclude_source_placements_from_provenance(
        composed_provenance,
        source_placements,
    )
    composed, source_placements, composed_provenance, policy_corrections = (
        apply_verified_source_policy(
            composed,
            source_text,
            source_placements,
            composed_provenance,
            policy_edits,
        )
    )
    policy_corrections = unapplied_shell_omission_corrections(
        source_text,
        policy_edits,
        policy_corrections,
    )
    density = apply_verified_source_density(
        composed,
        source_text,
        composed_provenance,
        source_placements,
        policy_corrections,
    )
    composed = density.candidate
    composed_provenance = density.provenance
    source_placements = density.source_placements
    policy_corrections = density.source_policy_corrections
    toc_edit = navigation_edit(composed)
    policy_corrections = rebase_source_policy_corrections(policy_corrections, toc_edit)
    source_placements = rebase_source_placements(source_placements, toc_edit)
    composed = apply_edit(composed, toc_edit)
    composed_provenance = rebase_provenance(composed_provenance, toc_edit, composed)
    composed_provenance = exclude_source_placements_from_provenance(
        composed_provenance,
        source_placements,
    )

    validate_compiled_source_shell(composed)
    if composed.rstrip() + "\n" != composed:
        raise ValueError("source-preserving composition produced a noncanonical trailing boundary")
    return VerifiedSourceComposition(
        candidate=composed,
        provenance=composed_provenance,
        source_placements=source_placements,
        source_policy_corrections=policy_corrections,
    )
