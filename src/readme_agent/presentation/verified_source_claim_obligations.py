"""Bind inherited source-claim obligations to accepted candidate provenance."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.source_claim_risk import (
    SourceClaimObligation,
    applicable_product_overview_fact_ids,
    obligation_any_fact_fields,
    obligation_provenance_prefixes,
    obligation_required_fact_fields,
)


def accepted_obligation_bindings(
    obligation: SourceClaimObligation,
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
    *,
    exact_source_fact_ids: list[str] | None = None,
) -> tuple[list[CandidateContentProvenanceV1], list[str]] | None:
    """Return accepted provenance that completely satisfies one source obligation."""

    prefixes = obligation_provenance_prefixes(obligation)
    required_fields = obligation_required_fact_fields(obligation)
    any_fields = obligation_any_fact_fields(obligation)
    bindings = [
        binding
        for binding in provenance
        if any(
            binding.provenance_id == prefix or binding.provenance_id.startswith(f"{prefix}.")
            for prefix in prefixes
        )
    ]
    if not bindings:
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
    if obligation == "product_overview":
        required_resolution_fact_ids.update(applicable_product_overview_fact_ids(facts))
    if exact_source_fact_ids is not None:
        if not exact_source_fact_ids and obligation != "product_overview":
            return None
        if obligation == "product_overview":
            missing_fact_ids = required_resolution_fact_ids - bound_fact_ids
            supplemental = [
                binding
                for binding in provenance
                if missing_fact_ids.intersection(binding.fact_ids) and binding not in bindings
            ]
            bindings.extend(supplemental)
            bound_fact_ids.update(
                fact_id for binding in supplemental for fact_id in binding.fact_ids
            )
        if not required_resolution_fact_ids.issubset(bound_fact_ids):
            return None
        resolution_fact_ids = sorted(required_resolution_fact_ids)
    elif obligation == "product_overview":
        missing_fact_ids = required_resolution_fact_ids - bound_fact_ids
        supplemental = [
            binding
            for binding in provenance
            if missing_fact_ids.intersection(binding.fact_ids) and binding not in bindings
        ]
        bindings.extend(supplemental)
        bound_fact_ids.update(fact_id for binding in supplemental for fact_id in binding.fact_ids)
        if not required_resolution_fact_ids.issubset(bound_fact_ids):
            return None
        resolution_fact_ids = sorted(required_resolution_fact_ids)
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
    return bindings, resolution_fact_ids
