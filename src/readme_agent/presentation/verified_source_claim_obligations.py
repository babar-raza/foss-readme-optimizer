"""Bind inherited source-claim obligations to accepted candidate provenance."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_risk import (
    SourceClaimObligation,
    obligation_any_fact_fields,
    obligation_provenance_prefixes,
    obligation_required_fact_fields,
    obligation_required_standard_ids,
)


def _primary_example_is_executed(facts: ProductFactsV2, fact_ids: set[str]) -> bool:
    example_id = facts.selected_fact_ids.get("example.minimal")
    if example_id is None or example_id not in fact_ids:
        return False
    example = facts.fact_by_id(example_id)
    return bool(
        isinstance(example.value, dict)
        and example.value.get("verification_outcome") == "SOURCE_BUILD_VERIFIED"
    )


def _minimal_supplemental_bindings(
    provenance: list[CandidateContentProvenanceV1],
    primary: list[CandidateContentProvenanceV1],
    required_fact_ids: set[str],
) -> list[CandidateContentProvenanceV1] | None:
    """Cover missing source facts with the smallest exact candidate bindings."""

    covered = {fact_id for binding in primary for fact_id in binding.fact_ids}
    missing = required_fact_ids - covered
    selected: list[CandidateContentProvenanceV1] = []
    while missing:
        candidates = [
            binding
            for binding in provenance
            if binding not in primary and binding not in selected
            if binding.fact_ids
            if set(binding.fact_ids).issubset(required_fact_ids)
            if missing.intersection(binding.fact_ids)
        ]
        if not candidates:
            return None
        chosen = min(
            candidates,
            key=lambda binding: (
                -len(missing.intersection(binding.fact_ids)),
                binding.provenance_id,
            ),
        )
        selected.append(chosen)
        missing.difference_update(chosen.fact_ids)
    return selected


def accepted_obligation_bindings(
    obligation: SourceClaimObligation,
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
    *,
    exact_source_fact_ids: list[str] | None = None,
    exact_source_fact_coordinates: list[StructuredFactCoordinateV1] | None = None,
) -> tuple[list[CandidateContentProvenanceV1], list[str]] | None:
    """Return accepted provenance that completely satisfies one source obligation."""

    prefixes = obligation_provenance_prefixes(obligation)
    required_fields = obligation_required_fact_fields(obligation)
    any_fields = obligation_any_fact_fields(obligation)
    required_standard_ids = obligation_required_standard_ids(obligation)
    bindings = [
        binding
        for binding in provenance
        if binding.candidate_byte_end > binding.candidate_byte_start
        if any(
            binding.provenance_id == prefix or binding.provenance_id.startswith(f"{prefix}.")
            for prefix in prefixes
        )
    ]
    if not bindings:
        return None
    configured_standard_ids = {
        standard_id for binding in bindings for standard_id in binding.configured_standard_ids
    }
    if not required_standard_ids.issubset(configured_standard_ids):
        return None
    if obligation == "product_overview" and not all(
        any(
            binding.provenance_id == prefix or binding.provenance_id.startswith(f"{prefix}.")
            for binding in bindings
        )
        for prefix in prefixes
    ):
        return None
    bound_fact_ids = {fact_id for binding in bindings for fact_id in binding.fact_ids}
    required_resolution_fact_ids = set(exact_source_fact_ids or [])
    if exact_source_fact_ids is not None:
        if not exact_source_fact_ids:
            return None
        supplemental = _minimal_supplemental_bindings(
            provenance,
            bindings,
            required_resolution_fact_ids,
        )
        if supplemental is None:
            return None
        bindings.extend(supplemental)
        bound_fact_ids.update(fact_id for binding in supplemental for fact_id in binding.fact_ids)
        if not required_resolution_fact_ids.issubset(bound_fact_ids):
            return None
        resolution_fact_ids = sorted(required_resolution_fact_ids)
    elif obligation == "product_overview":
        resolution_fact_ids = sorted(bound_fact_ids)
    else:
        resolution_fact_ids = sorted(bound_fact_ids)
    accepted_fields: set[str] = set()
    for fact_id in sorted(bound_fact_ids):
        fact = facts.fact_by_id(fact_id)
        if (
            facts.selected_fact_ids.get(fact.field) != fact_id
            or fact.verification_state not in {"verified", "policy_approved"}
            or fact.has_unresolved_conflict
        ):
            return None
        accepted_fields.add(fact.field)
    if not required_fields.issubset(accepted_fields) or (
        any_fields and not any_fields.intersection(accepted_fields)
    ):
        return None
    if exact_source_fact_coordinates:
        required_coordinates = {
            (item.fact_id, item.field, item.path, item.value_sha256)
            for item in exact_source_fact_coordinates
        }
        bound_coordinates = {
            (item.fact_id, item.field, item.path, item.value_sha256)
            for binding in bindings
            for item in binding.fact_coordinates
        }
        if not required_coordinates.issubset(bound_coordinates):
            return None
    if obligation == "primary_example" and not _primary_example_is_executed(facts, bound_fact_ids):
        return None
    return bindings, resolution_fact_ids


def accepted_correction_obligation_bindings(
    obligation: SourceClaimObligation,
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
    *,
    contradiction_fact_ids: set[str],
) -> tuple[list[CandidateContentProvenanceV1], list[str]] | None:
    """Accept an exact factual replacement only after repository facts disprove the source."""

    if not contradiction_fact_ids or obligation not in {
        "api_public_surface",
        "major_capabilities",
        "product_overview",
        "verified_installation",
    }:
        return None
    for fact_id in contradiction_fact_ids:
        fact = facts.fact_by_id(fact_id)
        if (
            facts.selected_fact_ids.get(fact.field) != fact_id
            or fact.verification_state not in {"verified", "policy_approved"}
            or fact.has_unresolved_conflict
        ):
            return None
    return accepted_obligation_bindings(obligation, facts, provenance)


__all__ = ["accepted_correction_obligation_bindings", "accepted_obligation_bindings"]
