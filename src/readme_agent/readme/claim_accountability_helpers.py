"""Provide claim-accountability matching, provenance, and disposition helpers."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ClaimDisposition, ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.claim_accountability_models import (
    ClaimOrigin,
    ClaimStage,
    EquivalentCandidateClaimV1,
    ExpectedClaimDisposition,
    ReadmeClaimAccountabilityV1,
    StructuredFactCoordinateV1,
)
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.source_claim_assurance import accepted_source_claim_fact_ids

_CORRECTION_DISPOSITIONS = {"rewrite", "repair", "remove_update", "replace_generic"}
_MARKDOWN_MARKS = re.compile(r"[`*_>#\[\]()]")


def accepted_literal_facts(claim_text: str, facts: ProductFactsV2) -> set[str]:
    return accepted_source_claim_fact_ids(claim_text, facts)


def overlapping_candidate_fact_ids(
    claim: ReadmeMaterialClaimAssessmentV1,
    candidate_text: str,
    claim_map: ReadmeClaimMapV1,
) -> set[str]:
    bindings = [
        binding
        for binding in claim_map.claims
        if binding.coordinate_space == "candidate_utf8"
        and binding.byte_start < claim.source_byte_end
        and claim.source_byte_start < binding.byte_end
    ]
    if not bindings:
        return set()
    claim_bytes = candidate_text.encode("utf-8")[claim.source_byte_start : claim.source_byte_end]
    covered = bytearray(len(claim_bytes))
    for binding in bindings:
        start = max(binding.byte_start, claim.source_byte_start) - claim.source_byte_start
        end = min(binding.byte_end, claim.source_byte_end) - claim.source_byte_start
        covered[start:end] = b"\x01" * (end - start)
    uncovered = bytes(byte for index, byte in enumerate(claim_bytes) if not covered[index]).decode(
        "utf-8", errors="ignore"
    )
    if any(character.isalnum() for character in _MARKDOWN_MARKS.sub("", uncovered)):
        return set()
    return {binding.fact_id for binding in bindings}


def candidate_provenance_for_claim(
    claim: ReadmeMaterialClaimAssessmentV1,
    candidate_text: str,
    provenance: list[CandidateContentProvenanceV1],
) -> list[CandidateContentProvenanceV1]:
    """Return exact bindings only when all non-whitespace claim bytes are covered."""

    bindings = [
        binding
        for binding in provenance
        if binding.candidate_byte_start < claim.source_byte_end
        and claim.source_byte_start < binding.candidate_byte_end
    ]
    if not bindings:
        return []
    claim_bytes = candidate_text.encode("utf-8")[claim.source_byte_start : claim.source_byte_end]
    covered = bytearray(len(claim_bytes))
    for binding in bindings:
        start = max(binding.candidate_byte_start, claim.source_byte_start) - claim.source_byte_start
        end = min(binding.candidate_byte_end, claim.source_byte_end) - claim.source_byte_start
        covered[start:end] = b"\x01" * (end - start)
    uncovered = bytes(byte for index, byte in enumerate(claim_bytes) if not covered[index])
    return bindings if not uncovered.strip() else []


def expected_disposition(
    *,
    stage: ClaimStage,
    origin: ClaimOrigin,
    current: ClaimDisposition,
    accepted_fact_ids: set[str],
    configured_standard_ids: set[str],
    survives_in_candidate: bool | None,
    source_resolution: SourceClaimResolutionV1 | None = None,
    variable_fact_binding_required: bool = False,
    structured_equivalence: bool = False,
) -> tuple[ExpectedClaimDisposition, bool, str]:
    if structured_equivalence:
        if stage != "source" or survives_in_candidate is not False:
            return (
                "unjustified_loss",
                False,
                "Structured equivalence is reserved for exact replaced source claims.",
            )
        return (
            "verified_equivalence",
            True,
            "The exact source claim belongs to a complete structured-fact coordinate group "
            "represented by exact independently accountable candidate claims.",
        )
    if source_resolution is not None:
        if source_resolution.resolution == "deferred_verification":
            if survives_in_candidate is not False:
                return (
                    "unjustified_loss",
                    False,
                    "A deferred source claim must be absent from the candidate.",
                )
            return (
                "deferred_verification",
                True,
                "The exact inherited claim is excluded from the candidate and retained in "
                "evidence until repository verification can justify publication.",
            )
        if source_resolution.resolution == "verified_equivalence":
            if survives_in_candidate is not False:
                return (
                    "unjustified_loss",
                    False,
                    "A verified equivalence is only valid for a replaced source claim.",
                )
            return (
                "verified_equivalence",
                True,
                "The exact source claim is bound to an exact independently accountable "
                "candidate claim with the same accepted facts.",
            )
        if source_resolution.resolution == "verified_obligation_replacement":
            if survives_in_candidate is not False:
                return (
                    "unjustified_loss",
                    False,
                    "A verified obligation replacement is valid only for a replaced claim.",
                )
            return (
                "verified_obligation_replacement",
                True,
                "The exact inherited claim is replaced by a mandatory golden-contract slot "
                "whose exact candidate span is bound to accepted repository facts.",
            )
        if source_resolution.resolution == "verified_omission":
            if survives_in_candidate is not False:
                return (
                    "unjustified_loss",
                    False,
                    "A verified omission cannot approve a source claim that still survives.",
                )
            return (
                "verified_omission",
                True,
                "The exact source claim has an explicit evidence-backed verified omission.",
            )
        if source_resolution.resolution == "presentation_policy_correction":
            if survives_in_candidate is not False:
                return (
                    "unjustified_loss",
                    False,
                    "A partial policy correction must replace the original exact claim bytes.",
                )
            return (
                "presentation_policy_correction",
                True,
                "Exact policy-owned spans are corrected while retained claim bytes remain "
                "bound to exact source lineage.",
            )
        return (
            "required_correction",
            True,
            "The exact source claim has an accepted-fact correction pending operation proof.",
        )
    if current == "investigate":
        return (
            "explicit_uncertainty",
            True,
            "Instruction-like or unresolved source content remains explicitly untrusted.",
        )
    if current in _CORRECTION_DISPOSITIONS:
        return (
            "required_correction",
            False,
            "The assessment requires a bounded correction, but no accepted typed source-claim "
            "resolution proves that the correction occurred.",
        )
    if stage == "source" and survives_in_candidate is False:
        return (
            "unjustified_loss",
            False,
            "Preserved source knowledge disappeared without an exact correction, equivalence, "
            "or omission authority.",
        )
    if accepted_fact_ids:
        return (
            "accepted_fact",
            True,
            "Exact content is bound to at least one selected accepted fact.",
        )
    if configured_standard_ids and not variable_fact_binding_required:
        return (
            "configured_standard",
            True,
            "Generated structural content is bound to a governed presentation standard.",
        )
    if stage == "candidate" and origin == "generated":
        return (
            "unbound_generated",
            False,
            "Generated material has no accepted fact binding and requires correction or omission.",
        )
    return (
        "authoritative_owner_validation",
        False,
        "Byte preservation is not factual approval; an authoritative owner or fact is required.",
    )


def claim_text(document: str, claim: ReadmeMaterialClaimAssessmentV1) -> str:
    return document.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode("utf-8")


def accountability_record(
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
    *,
    stage: ClaimStage,
    origin: ClaimOrigin,
    fact_ids: set[str],
    fact_coordinates: list[StructuredFactCoordinateV1],
    configured_standard_ids: set[str],
    equivalence_group_id: str | None = None,
    equivalent_source_claim_ids: list[str] | None = None,
    equivalent_candidate_claims: list[EquivalentCandidateClaimV1] | None = None,
    survives: bool | None,
    expected: ExpectedClaimDisposition,
    accountable: bool,
    rationale: str,
) -> ReadmeClaimAccountabilityV1:
    return ReadmeClaimAccountabilityV1(
        claim_id=f"{stage}:{claim.claim_id}",
        stage=stage,
        origin=origin,
        source_byte_start=claim.source_byte_start,
        source_byte_end=claim.source_byte_end,
        content_sha256=claim.content_sha256,
        current_disposition=claim.disposition,
        accepted_fact_ids=sorted(fact_ids),
        accepted_fact_coordinates=fact_coordinates,
        configured_standard_ids=sorted(configured_standard_ids),
        authoritative_owners=sorted(
            {facts.fact_by_id(fact_id).authoritative_owner for fact_id in fact_ids}
        ),
        equivalence_group_id=equivalence_group_id,
        equivalent_source_claim_ids=equivalent_source_claim_ids or [],
        equivalent_candidate_claims=equivalent_candidate_claims or [],
        equivalence_normalization_version=(
            "structured-fact-coordinate-v1" if equivalence_group_id is not None else None
        ),
        survives_in_candidate=survives,
        expected_disposition=expected,
        currently_accountable=accountable,
        rationale=rationale,
    )
