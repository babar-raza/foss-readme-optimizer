"""Bind exact generated policy prose to accepted repository inputs."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import ClaimDisposition
from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.example_assurance_validation import (
    additional_examples_disclosure_fact_ids,
)

_CORRECTION_DISPOSITIONS = {"rewrite", "repair", "remove_update", "replace_generic"}
_MERMAID_FENCE = re.compile(
    r"\A```mermaid[^\S\r\n]*\r?\n.+\r?\n```[^\S\r\n]*(?:\r?\n)?\Z",
    re.DOTALL,
)
_MERMAID_FACT_FIELDS = {
    "product.capabilities",
    "product.formats",
    "product.identity",
    "product.problems_solved",
}


def accepted_candidate_policy_fact_ids(
    claim_text: str,
    facts: ProductFactsV2,
    bindings: list[CandidateContentProvenanceV1],
) -> set[str]:
    """Return facts supporting exact non-literal prose under a typed standard."""

    standard_ids = {
        standard_id for binding in bindings for standard_id in binding.configured_standard_ids
    }
    fact_ids = set(additional_examples_disclosure_fact_ids(claim_text, facts))
    if "readme.at_a_glance_mermaid" in standard_ids and _MERMAID_FENCE.fullmatch(claim_text):
        for fact_id in {fact_id for binding in bindings for fact_id in binding.fact_ids}:
            fact = facts.fact_by_id(fact_id)
            if (
                fact.field in _MERMAID_FACT_FIELDS
                and facts.selected_fact_ids.get(fact.field) == fact_id
                and fact.verification_state in {"verified", "policy_approved"}
                and not fact.has_unresolved_conflict
            ):
                fact_ids.add(fact_id)
    if "readme.contextual_links" not in standard_ids:
        return fact_ids
    for fact_id in {fact_id for binding in bindings for fact_id in binding.fact_ids}:
        fact = facts.fact_by_id(fact_id)
        if (
            facts.selected_fact_ids.get(fact.field) != fact_id
            or fact.verification_state not in {"verified", "policy_approved"}
            or fact.has_unresolved_conflict
        ):
            return fact_ids
        fact_ids.add(fact_id)
    return fact_ids


def exact_candidate_policy_correction(
    disposition: ClaimDisposition,
    configured_standard_ids: set[str],
    accepted_fact_ids: set[str],
) -> bool:
    """Recognize only fact-bound contextual prose rejected by source-oriented assessment."""

    return bool(
        disposition in _CORRECTION_DISPOSITIONS
        and "readme.contextual_links" in configured_standard_ids
        and accepted_fact_ids
    )


__all__ = ["accepted_candidate_policy_fact_ids", "exact_candidate_policy_correction"]
