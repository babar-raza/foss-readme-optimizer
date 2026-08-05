"""Resolve inherited README claims against verified candidate evidence."""

from __future__ import annotations

import hashlib
from collections import Counter

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_claim_matching import (
    equivalent_source_claim_resolution,
    index_equivalent_candidate_claims,
)
from readme_agent.presentation.verified_source_claim_obligations import (
    accepted_obligation_bindings,
)
from readme_agent.presentation.verified_source_claim_omissions import governed_source_omission
from readme_agent.presentation.verified_source_policy_resolution import source_policy_resolution
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.source_claim_assurance import accepted_source_claim_fact_ids
from readme_agent.readme.source_claim_policy import SourceClaimPolicyCorrectionV1
from readme_agent.readme.source_claim_risk import (
    classify_source_claim_risk,
    obligation_requires_source_entailment,
)


def _raise_unresolved_preserve(required: bool, claim_id: str) -> None:
    if required:
        raise ValueError(
            "preserve disposition lost a source claim without exact fact-bound replacement "
            f"candidate content: {claim_id}"
        )


def resolve_source_claims(
    source_text: str,
    candidate: str,
    facts: ProductFactsV2,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    *,
    preserved_source_ranges: list[tuple[int, int]] | None = None,
    authoritative_correction_ranges: list[tuple[int, int]] | None = None,
    presentation_policy_corrections: list[SourceClaimPolicyCorrectionV1] | None = None,
    fail_on_unresolved_preserve: bool = True,
) -> list[SourceClaimResolutionV1]:
    """Resolve removed claims by risk; mandatory claims fail closed without verified slots."""

    source_claims = assess_material_claims(source_text)
    candidate_claims = assess_material_claims(candidate)
    candidate_hashes = Counter(claim.content_sha256 for claim in candidate_claims)
    raw_candidate_occurrences = Counter(
        {
            claim.content_sha256: candidate.count(
                source_text.encode("utf-8")[claim.source_byte_start : claim.source_byte_end].decode(
                    "utf-8"
                )
            )
            for claim in source_claims
        }
    )
    candidate_bytes = candidate.encode("utf-8")
    equivalence_candidates = index_equivalent_candidate_claims(candidate_bytes, candidate_claims)
    resolutions: list[SourceClaimResolutionV1] = []
    source_bytes = source_text.encode("utf-8")
    preserve_ranges = preserved_source_ranges or []
    correction_ranges = authoritative_correction_ranges or []
    policy_corrections = presentation_policy_corrections or []
    for claim in source_claims:
        if raw_candidate_occurrences[claim.content_sha256] > 0:
            raw_candidate_occurrences[claim.content_sha256] -= 1
            if candidate_hashes[claim.content_sha256] > 0:
                candidate_hashes[claim.content_sha256] -= 1
            continue
        survives = candidate_hashes[claim.content_sha256] > 0
        if survives:
            candidate_hashes[claim.content_sha256] -= 1
            continue
        claim_text = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        policy_resolution = source_policy_resolution(claim, policy_corrections)
        if policy_resolution is not None:
            resolutions.append(policy_resolution)
            continue
        equivalent_resolution = equivalent_source_claim_resolution(
            claim,
            claim_text,
            candidate_bytes,
            equivalence_candidates,
            facts,
        )
        if equivalent_resolution is not None:
            resolutions.append(equivalent_resolution)
            continue
        preserve_required = claim.disposition == "preserve" and any(
            claim.source_byte_start < end and start < claim.source_byte_end
            for start, end in preserve_ranges
        )
        correction_required = any(
            claim.source_byte_start < end and start < claim.source_byte_end
            for start, end in correction_ranges
        )
        if preserve_required:
            _raise_unresolved_preserve(fail_on_unresolved_preserve, claim.claim_id)
            continue
        risk = (
            classify_source_claim_risk(source_text, claim)
            if candidate_content_provenance is not None
            else None
        )
        if risk is not None and risk.risk_class == "governed_valid_omission":
            assert candidate_content_provenance is not None
            accepted = accepted_obligation_bindings(
                "contextual_product_relationship",
                facts,
                candidate_content_provenance,
            )
            if accepted is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            bindings, replacement_fact_ids = accepted
            replacement_ids = sorted(binding.provenance_id for binding in bindings)
            resolutions.append(
                SourceClaimResolutionV1(
                    claim_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                    content_sha256=claim.content_sha256,
                    resolution="verified_omission",
                    obligation_id="contextual_product_relationship",
                    fact_ids=replacement_fact_ids,
                    replacement_provenance_ids=replacement_ids,
                    evidence=[
                        f"source-claim:{claim.claim_id}",
                        f"source-content-sha256:{claim.content_sha256}",
                        "obligation:contextual_product_relationship",
                        *(f"candidate-provenance:{item}" for item in replacement_ids),
                        *(f"accepted-fact:{item}" for item in replacement_fact_ids),
                    ],
                    rationale=risk.rationale,
                )
            )
            continue
        governed_omission = governed_source_omission(claim_text)
        if governed_omission is None:
            if candidate_content_provenance is None or risk is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            if not correction_required:
                continue
            if risk.risk_class == "optional_explicit_deferral":
                core_evidence: list[str] = []
                if risk.obligation_id is not None:
                    accepted_core = accepted_obligation_bindings(
                        risk.obligation_id,
                        facts,
                        candidate_content_provenance,
                    )
                    if accepted_core is None:
                        _raise_unresolved_preserve(
                            preserve_required and fail_on_unresolved_preserve,
                            claim.claim_id,
                        )
                        continue
                    core_bindings, _ = accepted_core
                    core_evidence = [
                        f"verified-core-provenance:{binding.provenance_id}"
                        for binding in core_bindings
                    ]
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                resolutions.append(
                    SourceClaimResolutionV1(
                        claim_id=claim.claim_id,
                        source_byte_start=claim.source_byte_start,
                        source_byte_end=claim.source_byte_end,
                        content_sha256=claim.content_sha256,
                        resolution="deferred_verification",
                        evidence=[
                            f"source-claim:{claim.claim_id}",
                            f"source-content-sha256:{claim.content_sha256}",
                            f"candidate-content-sha256:{hashlib.sha256(candidate_bytes).hexdigest()}",
                            "risk-policy:optional-inherited-detail-deferred-v1",
                            *core_evidence,
                        ],
                        rationale=risk.rationale,
                    )
                )
                continue
            if risk.obligation_id is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            accepted = accepted_obligation_bindings(
                risk.obligation_id,
                facts,
                candidate_content_provenance,
                exact_source_fact_ids=(
                    sorted(accepted_source_claim_fact_ids(claim_text, facts))
                    if obligation_requires_source_entailment(risk.obligation_id)
                    else None
                ),
            )
            if accepted is None:
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            bindings, replacement_fact_ids = accepted
            replacement_ids = sorted(binding.provenance_id for binding in bindings)
            resolutions.append(
                SourceClaimResolutionV1(
                    claim_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                    content_sha256=claim.content_sha256,
                    resolution="verified_obligation_replacement",
                    obligation_id=risk.obligation_id,
                    fact_ids=replacement_fact_ids,
                    replacement_provenance_ids=replacement_ids,
                    evidence=[
                        f"source-claim:{claim.claim_id}",
                        f"source-content-sha256:{claim.content_sha256}",
                        f"obligation:{risk.obligation_id}",
                        f"authority:deterministic-claim-disposition:{claim.disposition}",
                        *(f"candidate-provenance:{item}" for item in replacement_ids),
                        *(f"accepted-fact:{item}" for item in replacement_fact_ids),
                    ],
                    rationale=(
                        f"{risk.rationale} The exact replacement slot is bound to selected, "
                        "accepted repository facts under an explicit hash-bound correction range."
                    ),
                )
            )
            continue
        evidence_kind, rationale = governed_omission
        resolutions.append(
            SourceClaimResolutionV1(
                claim_id=claim.claim_id,
                source_byte_start=claim.source_byte_start,
                source_byte_end=claim.source_byte_end,
                content_sha256=claim.content_sha256,
                resolution="verified_omission",
                evidence=[
                    f"source-claim:{claim.claim_id}",
                    f"source-content-sha256:{claim.content_sha256}",
                    f"disposition:{evidence_kind}",
                    f"facts-sha256:{facts.canonical_hash()}",
                ],
                rationale=rationale,
            )
        )
    return resolutions


__all__ = ["resolve_source_claims"]
