"""Validate exact fact and candidate-span bindings for removed source claims."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityV1
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.source_claim_risk import (
    obligation_any_fact_fields,
    obligation_provenance_prefixes,
    obligation_required_fact_fields,
)


def replacement_provenance_is_exact(
    resolution: SourceClaimResolutionV1,
    facts: ProductFactsV2,
    provenance_by_id: dict[str, CandidateContentProvenanceV1],
    *,
    exact_source_fact_ids: list[str] | None = None,
    allow_contradicted_source_subset: bool = False,
) -> bool:
    """Require exact selected facts and allowed slot spans for one replacement."""

    if (
        resolution.obligation_id is None
        or not resolution.fact_ids
        or not resolution.replacement_provenance_ids
        or len(resolution.replacement_provenance_ids)
        != len(set(resolution.replacement_provenance_ids))
    ):
        return False
    try:
        bindings = [
            provenance_by_id[provenance_id]
            for provenance_id in resolution.replacement_provenance_ids
        ]
        cited_facts = [facts.fact_by_id(fact_id) for fact_id in resolution.fact_ids]
    except KeyError:
        return False
    bound_fact_ids = {fact_id for binding in bindings for fact_id in binding.fact_ids}
    try:
        bound_facts = [facts.fact_by_id(fact_id) for fact_id in bound_fact_ids]
    except KeyError:
        return False
    if not set(resolution.fact_ids).issubset(bound_fact_ids):
        return False
    if exact_source_fact_ids is not None:
        if not exact_source_fact_ids:
            return False
        if allow_contradicted_source_subset:
            if not set(resolution.fact_ids).issubset(exact_source_fact_ids):
                return False
        elif resolution.obligation_id == "product_overview":
            if not set(exact_source_fact_ids).issubset(resolution.fact_ids):
                return False
        elif set(resolution.fact_ids) != set(exact_source_fact_ids):
            return False
    fields = {fact.field for fact in bound_facts}
    required_fields = obligation_required_fact_fields(resolution.obligation_id)
    any_fields = obligation_any_fact_fields(resolution.obligation_id)
    prefixes = obligation_provenance_prefixes(resolution.obligation_id)
    if not required_fields.issubset(fields) or (any_fields and not any_fields.intersection(fields)):
        return False
    obligation_provenance_ids = {
        provenance_id
        for provenance_id in resolution.replacement_provenance_ids
        if any(
            provenance_id == prefix or provenance_id.startswith(f"{prefix}.") for prefix in prefixes
        )
    }
    if not obligation_provenance_ids:
        return False
    supplemental = [
        binding for binding in bindings if binding.provenance_id not in obligation_provenance_ids
    ]
    remaining_supplemental_facts = set(resolution.fact_ids) - {
        fact_id
        for binding in bindings
        if binding.provenance_id in obligation_provenance_ids
        for fact_id in binding.fact_ids
    }
    for binding in supplemental:
        binding_fact_ids = set(binding.fact_ids)
        if (
            not binding_fact_ids
            or not binding_fact_ids.issubset(resolution.fact_ids)
            or not binding_fact_ids.intersection(remaining_supplemental_facts)
        ):
            return False
        remaining_supplemental_facts.difference_update(binding_fact_ids)
    if remaining_supplemental_facts:
        return False
    if resolution.obligation_id == "product_overview":
        if any(
            not set(binding.fact_ids).intersection(resolution.fact_ids) for binding in supplemental
        ):
            return False
        if not all(
            any(
                provenance_id == prefix or provenance_id.startswith(f"{prefix}.")
                for provenance_id in obligation_provenance_ids
            )
            for prefix in prefixes
        ):
            return False
    return all(
        facts.selected_fact_ids.get(fact.field) == fact.fact_id
        and fact.verification_state in {"verified", "policy_approved"}
        and not fact.has_unresolved_conflict
        for fact in [*cited_facts, *bound_facts]
    )


def replacement_candidate_claims_are_exact(
    resolution: SourceClaimResolutionV1,
    candidate_records: list[ReadmeClaimAccountabilityV1],
    provenance_by_id: dict[str, CandidateContentProvenanceV1],
) -> bool:
    """Require every replaced source fact on an accountable candidate claim span."""

    try:
        bindings = [
            provenance_by_id[provenance_id]
            for provenance_id in resolution.replacement_provenance_ids
        ]
    except KeyError:
        return False
    return all(
        any(
            record.currently_accountable
            and fact_id in record.accepted_fact_ids
            and any(
                fact_id in binding.fact_ids
                and binding.candidate_byte_start < record.source_byte_end
                and record.source_byte_start < binding.candidate_byte_end
                for binding in bindings
            )
            for record in candidate_records
        )
        for fact_id in resolution.fact_ids
    )
