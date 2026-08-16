"""Bind exact generated policy prose to accepted repository inputs."""

from __future__ import annotations

import hashlib
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
_DOCUMENTATION_RESOURCE_FACT_FIELDS = {
    "documentation.links",
    "product.identity",
}
_OPENING_SUMMARY_FACT_FIELDS = {
    "product.audience",
    "product.capabilities",
    "product.formats",
    "product.identity",
    "product.problems_solved",
}
_PUBLIC_EXAMPLE_INTRO = re.compile(
    r"\AExpand this section to (?:view examples for|browse) .+\.\Z",
    re.DOTALL,
)
_API_REFERENCE_TABLE = re.compile(
    r"\A\| Type \| Description \|\r?\n"
    r"\| --- \| --- \|\r?\n"
    r"(?:\| `[^`]+` \| [^\r\n|]*(?:\\\|[^\r\n|]*)* \|\r?\n?)+\Z"
)
_API_REFERENCE_SHELL = re.compile(
    r"\A(?:<details>\r?\n<summary>View public API by namespace</summary>|</details>)\r?\n?\Z"
)
_API_REFERENCE_PROVENANCE = re.compile(
    r"^template\.section\.api_reference\.claim:\d+:(?P<digest>[0-9a-f]{16})$"
)
_API_METHOD_INDEX_TABLE = re.compile(
    r"\A\| Type \| Member \| Description \|\r?\n"
    r"\| --- \| --- \| --- \|\r?\n"
    r"(?:\| `[^`]+` \| `[^`]+` \| [^\r\n|]*(?:\\\|[^\r\n|]*)* \|\r?\n?)+\Z"
)
_API_METHOD_INDEX_SHELL = re.compile(
    r"\A(?:<details>\r?\n<summary>View documented public methods</summary>|</details>)\r?\n?\Z"
)
_API_METHOD_INDEX_PROVENANCE = re.compile(
    r"^template\.section\.api_method_index\.claim:\d+:(?P<digest>[0-9a-f]{16})$"
)


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
    if "readme.additional_examples" in standard_ids and _PUBLIC_EXAMPLE_INTRO.fullmatch(
        claim_text.strip()
    ):
        for fact_id in {fact_id for binding in bindings for fact_id in binding.fact_ids}:
            fact = facts.fact_by_id(fact_id)
            if (
                fact.field == "repository.examples"
                and facts.selected_fact_ids.get(fact.field) == fact_id
                and fact.verification_state in {"verified", "policy_approved"}
                and not fact.has_unresolved_conflict
            ):
                fact_ids.add(fact_id)
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
    if "readme.documentation_resources" in standard_ids and "](https://" in claim_text:
        for fact_id in {fact_id for binding in bindings for fact_id in binding.fact_ids}:
            fact = facts.fact_by_id(fact_id)
            if (
                fact.field in _DOCUMENTATION_RESOURCE_FACT_FIELDS
                and facts.selected_fact_ids.get(fact.field) == fact_id
                and fact.verification_state in {"verified", "policy_approved"}
                and not fact.has_unresolved_conflict
            ):
                fact_ids.add(fact_id)
    if "readme.agentic_opening_summary" in standard_ids:
        for fact_id in {fact_id for binding in bindings for fact_id in binding.fact_ids}:
            fact = facts.fact_by_id(fact_id)
            if (
                fact.field in _OPENING_SUMMARY_FACT_FIELDS
                and facts.selected_fact_ids.get(fact.field) == fact_id
                and fact.verification_state in {"verified", "policy_approved"}
                and not fact.has_unresolved_conflict
            ):
                fact_ids.add(fact_id)
    if "readme.api_reference" in standard_ids and (
        _API_REFERENCE_TABLE.fullmatch(claim_text.strip())
        or _API_REFERENCE_SHELL.fullmatch(claim_text)
    ):
        digest = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()[:16]
        canonical_bindings = [
            binding
            for binding in bindings
            if (match := _API_REFERENCE_PROVENANCE.fullmatch(binding.provenance_id)) is not None
            and match.group("digest") == digest
        ]
        for fact_id in {fact_id for binding in canonical_bindings for fact_id in binding.fact_ids}:
            fact = facts.fact_by_id(fact_id)
            if (
                fact.field == "api.public_surface"
                and facts.selected_fact_ids.get(fact.field) == fact_id
                and fact.verification_state in {"verified", "policy_approved"}
                and not fact.has_unresolved_conflict
            ):
                fact_ids.add(fact_id)
    if "readme.api_method_index" in standard_ids and (
        _API_METHOD_INDEX_TABLE.fullmatch(claim_text.strip())
        or _API_METHOD_INDEX_SHELL.fullmatch(claim_text)
    ):
        digest = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()[:16]
        canonical_bindings = [
            binding
            for binding in bindings
            if (match := _API_METHOD_INDEX_PROVENANCE.fullmatch(binding.provenance_id)) is not None
            and match.group("digest") == digest
        ]
        for fact_id in {fact_id for binding in canonical_bindings for fact_id in binding.fact_ids}:
            fact = facts.fact_by_id(fact_id)
            if (
                fact.field == "api.public_surface"
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
