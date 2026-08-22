"""Resolve source prose that exists only to introduce an adjacent example."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_claim_matching import (
    equivalent_source_claim_resolution,
)
from readme_agent.presentation.verified_source_claim_obligations import (
    accepted_obligation_bindings,
)
from readme_agent.presentation.verified_source_claim_omissions import (
    verified_paired_example_intro_resolution,
)
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.source_claim_risk import classify_source_claim_risk


def resolve_paired_example_intro(
    *,
    claim_index: int,
    source_claims: list[ReadmeMaterialClaimAssessmentV1],
    source_text: str,
    candidate_bytes: bytes,
    equivalence_candidates: dict[str, list[ReadmeMaterialClaimAssessmentV1]],
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1],
    authorized_claim_ids: frozenset[str],
) -> SourceClaimResolutionV1 | None:
    """Resolve a redundant intro only after its adjacent example is fact-bound."""

    claim = source_claims[claim_index]
    if claim.claim_id not in authorized_claim_ids:
        return None
    risk = classify_source_claim_risk(source_text, claim)
    if risk.obligation_id != "primary_example":
        return None
    accepted_primary = accepted_obligation_bindings(
        "primary_example",
        facts,
        candidate_content_provenance,
    )
    paired_claim = source_claims[claim_index + 1] if claim_index + 1 < len(source_claims) else None
    if paired_claim is None:
        return None
    source_bytes = source_text.encode("utf-8")
    claim_text = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    paired_text = source_bytes[
        paired_claim.source_byte_start : paired_claim.source_byte_end
    ].decode("utf-8")
    paired_resolution = equivalent_source_claim_resolution(
        paired_claim,
        paired_text,
        candidate_bytes,
        equivalence_candidates,
        facts,
        candidate_content_provenance,
    )
    return verified_paired_example_intro_resolution(
        claim,
        claim_text,
        paired_claim,
        paired_text,
        source_text,
        risk,
        facts,
        accepted_primary,
        paired_resolution,
        authorized_claim_ids=authorized_claim_ids,
    )


__all__ = ["resolve_paired_example_intro"]
