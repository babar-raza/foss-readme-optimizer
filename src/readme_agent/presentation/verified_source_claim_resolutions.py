"""Expose strict and composition-probe source-claim resolution modes."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_claim_resolution_engine import resolve_source_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1


def build_source_claim_resolutions(
    source_text: str,
    candidate: str,
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    *,
    preserved_source_ranges: list[tuple[int, int]] | None = None,
    authoritative_correction_ranges: list[tuple[int, int]] | None = None,
    presentation_policy_corrections: list[SourceClaimPolicyCorrectionV1] | None = None,
) -> list[SourceClaimResolutionV1]:
    """Build final strict resolutions; unresolved leaf-preserve loss always raises."""

    return resolve_source_claims(
        source_text,
        candidate,
        facts,
        candidate_content_provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=authoritative_correction_ranges,
        presentation_policy_corrections=presentation_policy_corrections,
        fail_on_unresolved_preserve=True,
    )


def probe_source_claim_resolutions_for_composition(
    source_text: str,
    candidate: str,
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1],
    *,
    preserved_source_ranges: list[tuple[int, int]],
    authoritative_correction_ranges: list[tuple[int, int]],
) -> list[SourceClaimResolutionV1]:
    """Probe replaceable claims before exact preservation; never use as final plan evidence."""

    return resolve_source_claims(
        source_text,
        candidate,
        facts,
        candidate_content_provenance,
        preserved_source_ranges=preserved_source_ranges,
        authoritative_correction_ranges=authoritative_correction_ranges,
        fail_on_unresolved_preserve=False,
    )


__all__ = [
    "build_source_claim_resolutions",
    "probe_source_claim_resolutions_for_composition",
]
