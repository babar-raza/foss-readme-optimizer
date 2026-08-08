"""Resolve inherited README claims against verified candidate evidence."""

from __future__ import annotations

from collections import Counter

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_source_claim_matching import (
    equivalent_source_claim_resolution,
    index_equivalent_candidate_claims,
)
from readme_agent.presentation.verified_source_claim_obligations import (
    accepted_correction_obligation_bindings,
    accepted_obligation_bindings,
)
from readme_agent.presentation.verified_source_claim_omissions import (
    deferred_unverified_obligation_detail_resolution,
    deferred_unverified_source_example_resolution,
    deferred_withheld_source_resolution,
    exact_authorized_claim_ids,
    governed_source_omission,
    verified_paired_example_intro_resolution,
)
from readme_agent.presentation.verified_source_policy_resolution import source_policy_resolution
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.source_claim_contradiction import contradicted_source_claim_fact_ids
from readme_agent.readme.source_claim_fact_binding import complete_source_claim_fact_binding
from readme_agent.readme.source_claim_obligations import applicable_product_overview_fact_ids
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

    if source_text == candidate:
        return []

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
    preserve_claim_ids = exact_authorized_claim_ids(
        source_text,
        source_claims,
        preserved_source_ranges or [],
        authority="fact-authorized preservation",
    )
    correction_claim_ids = exact_authorized_claim_ids(
        source_text,
        source_claims,
        authoritative_correction_ranges or [],
        authority="correction-candidate withholding",
    )
    overlap = preserve_claim_ids & correction_claim_ids
    if overlap:
        raise ValueError(
            "source claim cannot be both fact-authorized and correction-required: "
            f"{sorted(overlap)[0]}"
        )
    policy_corrections = presentation_policy_corrections or []
    for claim_index, claim in enumerate(source_claims):
        claim_text = source_bytes[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
        fact_authorized_preserve = claim.claim_id in preserve_claim_ids
        if candidate_content_provenance:
            equivalent_resolution = equivalent_source_claim_resolution(
                claim,
                claim_text,
                candidate_bytes,
                equivalence_candidates,
                facts,
                candidate_content_provenance,
            )
            if equivalent_resolution is not None:
                resolutions.append(equivalent_resolution)
                if raw_candidate_occurrences[claim.content_sha256] > 0:
                    raw_candidate_occurrences[claim.content_sha256] -= 1
                if candidate_hashes[claim.content_sha256] > 0:
                    candidate_hashes[claim.content_sha256] -= 1
                continue
        if fact_authorized_preserve and raw_candidate_occurrences[claim.content_sha256] > 0:
            raw_candidate_occurrences[claim.content_sha256] -= 1
            if candidate_hashes[claim.content_sha256] > 0:
                candidate_hashes[claim.content_sha256] -= 1
            continue
        correction_candidate = claim.claim_id in correction_claim_ids
        if not correction_candidate and raw_candidate_occurrences[claim.content_sha256] > 0:
            raw_candidate_occurrences[claim.content_sha256] -= 1
            if candidate_hashes[claim.content_sha256] > 0:
                candidate_hashes[claim.content_sha256] -= 1
            continue
        survives = not correction_candidate and candidate_hashes[claim.content_sha256] > 0
        if survives:
            candidate_hashes[claim.content_sha256] -= 1
            continue
        policy_resolution = source_policy_resolution(
            claim,
            policy_corrections,
            source_bytes=source_bytes,
            candidate_bytes=candidate_bytes,
        )
        if policy_resolution is not None:
            resolutions.append(policy_resolution)
            continue
        equivalent_resolution = (
            equivalent_source_claim_resolution(
                claim,
                claim_text,
                candidate_bytes,
                equivalence_candidates,
                facts,
                candidate_content_provenance,
            )
            if not fact_authorized_preserve or candidate_content_provenance
            else None
        )
        if equivalent_resolution is not None:
            resolutions.append(equivalent_resolution)
            continue
        preserve_required = claim.disposition == "preserve" and claim.claim_id in preserve_claim_ids
        correction_required = claim.claim_id in correction_claim_ids
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
        if preserve_required:
            _raise_unresolved_preserve(fail_on_unresolved_preserve, claim.claim_id)
            continue
        if risk is not None and not correction_required:
            continue
        if not correction_required:
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
            if risk.obligation_id == "primary_example":
                accepted_primary = accepted_obligation_bindings(
                    "primary_example",
                    facts,
                    candidate_content_provenance,
                )
                deferred_example = deferred_unverified_source_example_resolution(
                    claim,
                    claim_text,
                    source_text,
                    candidate_bytes,
                    risk,
                    facts,
                    accepted_primary,
                    correction_candidate_claim_ids=correction_claim_ids,
                )
                if deferred_example is not None:
                    resolutions.append(deferred_example)
                    continue
                paired_claim = (
                    source_claims[claim_index + 1] if claim_index + 1 < len(source_claims) else None
                )
                paired_claim_text = (
                    source_bytes[
                        paired_claim.source_byte_start : paired_claim.source_byte_end
                    ].decode("utf-8")
                    if paired_claim is not None
                    else None
                )
                paired_resolution = (
                    equivalent_source_claim_resolution(
                        paired_claim,
                        paired_claim_text,
                        candidate_bytes,
                        equivalence_candidates,
                        facts,
                        candidate_content_provenance,
                    )
                    if paired_claim is not None and paired_claim_text is not None
                    else None
                )
                paired_intro = verified_paired_example_intro_resolution(
                    claim,
                    claim_text,
                    paired_claim,
                    paired_claim_text,
                    source_text,
                    risk,
                    facts,
                    accepted_primary,
                    paired_resolution,
                    correction_candidate_claim_ids=correction_claim_ids,
                )
                if paired_intro is not None:
                    resolutions.append(paired_intro)
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
                deferred = deferred_withheld_source_resolution(
                    claim,
                    claim_text,
                    candidate_bytes,
                    risk,
                    correction_candidate_claim_ids=correction_claim_ids,
                    extra_evidence=core_evidence,
                )
                if deferred is None:
                    raise ValueError(
                        "optional source withholding lacked exact correction authority: "
                        f"{claim.claim_id}"
                    )
                resolutions.append(deferred)
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
                    sorted(
                        binding.fact_ids
                        if (
                            binding := complete_source_claim_fact_binding(
                                source_text,
                                claim,
                                facts,
                            )
                        )
                        else []
                    )
                    if obligation_requires_source_entailment(risk.obligation_id)
                    else sorted(applicable_product_overview_fact_ids(facts))
                    if risk.obligation_id == "product_overview"
                    else None
                ),
            )
            contradiction_fact_ids: set[str] = set()
            if (
                accepted is None
                and obligation_requires_source_entailment(risk.obligation_id)
                and correction_required
            ):
                contradiction_fact_ids = contradicted_source_claim_fact_ids(
                    source_text,
                    claim,
                    facts,
                )
                accepted = accepted_correction_obligation_bindings(
                    risk.obligation_id,
                    facts,
                    candidate_content_provenance,
                    contradiction_fact_ids=contradiction_fact_ids,
                )
            if accepted is None:
                candidate_core = accepted_obligation_bindings(
                    risk.obligation_id,
                    facts,
                    candidate_content_provenance,
                )
                deferred_detail = deferred_unverified_obligation_detail_resolution(
                    claim,
                    claim_text,
                    candidate_bytes,
                    risk,
                    facts,
                    correction_candidate_claim_ids=correction_claim_ids,
                    candidate_core_present=candidate_core is not None,
                )
                if deferred_detail is not None:
                    resolutions.append(deferred_detail)
                    continue
                _raise_unresolved_preserve(
                    preserve_required and fail_on_unresolved_preserve,
                    claim.claim_id,
                )
                continue
            bindings, replacement_fact_ids = accepted
            replacement_ids = sorted(binding.provenance_id for binding in bindings)
            if not replacement_fact_ids:
                resolutions.append(
                    SourceClaimResolutionV1(
                        claim_id=claim.claim_id,
                        source_byte_start=claim.source_byte_start,
                        source_byte_end=claim.source_byte_end,
                        content_sha256=claim.content_sha256,
                        resolution="verified_omission",
                        obligation_id=risk.obligation_id,
                        evidence=[
                            f"source-claim:{claim.claim_id}",
                            f"source-content-sha256:{claim.content_sha256}",
                            f"configured-obligation:{risk.obligation_id}",
                            "authority:verified-source-assurance:correction-candidate",
                            *(f"candidate-provenance:{item}" for item in replacement_ids),
                        ],
                        rationale=(
                            f"{risk.rationale} The source shell is superseded by the exact "
                            "configured candidate slot under hash-bound correction authority."
                        ),
                    )
                )
                continue
            resolutions.append(
                SourceClaimResolutionV1(
                    claim_id=claim.claim_id,
                    source_byte_start=claim.source_byte_start,
                    source_byte_end=claim.source_byte_end,
                    content_sha256=claim.content_sha256,
                    resolution="verified_obligation_replacement",
                    obligation_id=risk.obligation_id,
                    fact_ids=replacement_fact_ids,
                    contradiction_fact_ids=sorted(contradiction_fact_ids),
                    replacement_provenance_ids=replacement_ids,
                    evidence=[
                        f"source-claim:{claim.claim_id}",
                        f"source-content-sha256:{claim.content_sha256}",
                        f"obligation:{risk.obligation_id}",
                        "authority:verified-source-assurance:correction-candidate",
                        f"authority:deterministic-claim-disposition:{claim.disposition}",
                        *(f"contradicting-fact:{item}" for item in sorted(contradiction_fact_ids)),
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
