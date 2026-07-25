"""Independently reconstruct and validate a complete README document candidate."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.protected_content import (
    fingerprint_protected_content,
    validate_protected_content,
)
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_renderer import (
    apply_document_operations,
    document_template_hash,
)
from readme_agent.readme.markers import find_presentation_span

_ACCEPTED_STATES = {"verified", "policy_approved"}


class DocumentCandidateValidationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    checks: dict[str, bool]
    errors: list[str] = Field(default_factory=list)
    authorized_protected_corrections: list[str] = Field(default_factory=list)


def _sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _text_value(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item).rstrip(".") + "." for item in value)
    return str(value)


def _accepted(facts: ProductFactsV2, field_name: str):
    fact = facts.selected_fact(field_name)
    if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
        return None
    return fact


def validate_readme_document_candidate(
    original_text: str,
    candidate_text: str,
    plan: ReadmeDocumentPlanV1,
    facts: ProductFactsV2,
) -> DocumentCandidateValidationV1:
    """Reject stale spans, uncited corrections, reconstruction drift, and protected loss."""

    errors: list[str] = []
    checks: dict[str, bool] = {}
    source_span = find_presentation_span(original_text)
    source_inner = source_span.content if source_span is not None else original_text
    source = source_inner.encode("utf-8")
    candidate_span = find_presentation_span(candidate_text)

    checks["source_document_hash"] = _sha256(original_text) == plan.source_sha256
    checks["adoption_preserved_source"] = (
        _sha256(source) == plan.adoption.source_inner_sha256
        and len(source) == plan.adoption.source_inner_bytes
    )
    checks["candidate_has_presentation_span"] = candidate_span is not None
    checks["facts_hash_matches"] = (
        plan.facts_hash == facts.canonical_hash()
        and candidate_span is not None
        and candidate_span.facts_hash == plan.facts_hash
    )
    checks["template_hash_matches"] = plan.template_sha256 == document_template_hash()
    checks["candidate_hash_matches"] = _sha256(candidate_text) == plan.candidate_sha256

    for name, passed in checks.items():
        if not passed:
            errors.append(f"{name} failed")

    citations_valid = True
    span_hashes_valid = True
    authorized_fragment_ids: set[str] = set()
    for operation in plan.operations:
        selected = source[operation.source_byte_start : operation.source_byte_end]
        if _sha256(selected) != operation.expected_sha256:
            span_hashes_valid = False
            errors.append(f"{operation.operation_id}: source span hash changed")
        if _sha256(operation.replacement_text) != operation.replacement_sha256:
            span_hashes_valid = False
            errors.append(f"{operation.operation_id}: replacement hash changed")
        for fact_id in operation.fact_ids:
            try:
                fact = facts.fact_by_id(fact_id)
            except KeyError:
                citations_valid = False
                errors.append(f"{operation.operation_id}: unknown fact {fact_id}")
                continue
            if facts.selected_fact_ids.get(fact.field) != fact_id:
                citations_valid = False
                errors.append(f"{operation.operation_id}: {fact_id} is not selected")
            if fact.verification_state not in _ACCEPTED_STATES or fact.has_unresolved_conflict:
                citations_valid = False
                errors.append(f"{operation.operation_id}: {fact_id} is {fact.verification_state}")
        if operation.protected_content_treatment == "authoritative_fact_correction":
            corrected = selected.decode("utf-8")
            authorized_fragment_ids.update(
                fragment.fragment_id
                for fragment in fingerprint_protected_content(corrected).fragments
            )

    checks["source_span_hashes"] = span_hashes_valid
    checks["fact_citations"] = citations_valid

    reconstructed = apply_document_operations(source, plan.operations)
    checks["document_reconstruction"] = (
        candidate_span is not None and reconstructed == candidate_span.content_bytes
    )
    if not checks["document_reconstruction"]:
        errors.append("candidate inner bytes do not reconstruct from the document plan")

    protected = (
        validate_protected_content(
            fingerprint_protected_content(source_inner),
            fingerprint_protected_content(candidate_span.content if candidate_span else ""),
            require_maintainer_region_unchanged=False,
        )
        if candidate_span is not None
        else None
    )
    unauthorized_losses = (
        [loss for loss in protected.losses if loss.fragment_id not in authorized_fragment_ids]
        if protected is not None
        else []
    )
    checks["protected_content"] = protected is not None and not unauthorized_losses
    errors.extend(
        f"unauthorized protected-content loss: {loss.fragment_id}" for loss in unauthorized_losses
    )

    example = _accepted(facts, "example.minimal")
    example_value = example.value if example is not None and isinstance(example.value, dict) else {}
    exact_example = str(example_value.get("code", "")).rstrip()
    checks["verified_example_present"] = (
        example is None
        or not exact_example
        or bool(candidate_span is not None and exact_example in candidate_span.content)
    )
    if not checks["verified_example_present"]:
        errors.append("selected verified minimal example is absent")

    overview_facts = [
        selected
        for field_name in ("product.audience", "product.problems_solved")
        if (selected := _accepted(facts, field_name)) is not None
    ]
    checks["verified_overview_present"] = candidate_span is not None and all(
        _text_value(selected.value) in candidate_span.content for selected in overview_facts
    )
    if not checks["verified_overview_present"]:
        errors.append("fact-backed audience/problem overview is absent")

    return DocumentCandidateValidationV1(
        valid=not errors,
        checks=checks,
        errors=errors,
        authorized_protected_corrections=sorted(authorized_fragment_ids),
    )
