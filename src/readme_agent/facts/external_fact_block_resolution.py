"""Resolve one external fact block against a complete evidence catalog."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from readme_agent.evidence.redaction import redact_secret_like_values
from readme_agent.facts.external_fact_block_classification import (
    causally_relevant_fingerprint_fields,
    classify_external_fact_block_class,
)
from readme_agent.facts.external_fact_block_contracts import (
    AvailableFactEvidenceCatalogV1,
    AvailableFactEvidenceV1,
    ExternalDependencyFingerprintV1,
    ExternalFactBlockClassV1,
    ExternalFactBlockResolutionV1,
    ExternalFactBlockV1,
    FactAssertionAuthorityV1,
    FactClaimKindV1,
    FactEvidenceKindV1,
    WordingModeV1,
)

_ASSERTIVE_WORDING_MODES: tuple[WordingModeV1, ...] = (
    "assert",
    "qualify",
    "omit",
    "not_applicable",
)

_LADDER: tuple[
    tuple[Literal[1, 2, 3, 4, 5], FactEvidenceKindV1, dict[FactClaimKindV1, WordingModeV1]],
    ...,
] = (
    (
        1,
        "current_source_or_manifest",
        {"identity_coordinates": "assert", "static_existence": "assert"},
    ),
    (2, "committed_distribution_metadata", {"identity_coordinates": "assert"}),
    (
        3,
        "static_public_api_or_source",
        {
            "static_existence": "assert",
            "example_execution": "qualify",
            "runtime_behavior": "qualify",
        },
    ),
    (
        4,
        "verified_imported_knowledge",
        {
            "identity_coordinates": "qualify",
            "static_existence": "qualify",
            "example_execution": "qualify",
            "runtime_behavior": "qualify",
        },
    ),
    (5, "syntax_verified_example", {"example_execution": "qualify"}),
)


def _identity_conflicts(block: ExternalFactBlockV1, evidence: AvailableFactEvidenceV1) -> bool:
    for block_value, evidence_value in (
        (block.org_repo, evidence.org_repo),
        (block.source_revision, evidence.source_revision),
        (block.package_identity, evidence.package_identity),
    ):
        if block_value is not None and evidence_value is not None and block_value != evidence_value:
            return True
    return False


def _identity_bound(block: ExternalFactBlockV1, evidence: AvailableFactEvidenceV1) -> bool:
    if evidence.evidence_kind == "committed_distribution_metadata":
        return not (block.package_identity is not None and evidence.package_identity is None)
    if evidence.evidence_kind == "non_applicability_evidence":
        return True
    return not (block.source_revision is not None and evidence.source_revision is None)


def _resolution_hash(
    *,
    block: ExternalFactBlockV1,
    block_class: ExternalFactBlockClassV1,
    relevant_fields: tuple[str, ...],
    current_dependencies: ExternalDependencyFingerprintV1,
) -> str:
    payload = {
        "org_repo": block.org_repo,
        "block_source_revision": block.source_revision,
        "block_class": block_class,
        "claim_kind": block.claim_kind,
        "current_dependencies": {
            field: getattr(current_dependencies, field) for field in relevant_fields
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _resume_predicate(
    *,
    wording_mode: WordingModeV1,
    claim_kind: FactClaimKindV1,
    fingerprint_changed: bool | None,
    relevant_fields: tuple[str, ...],
) -> str:
    fields_text = ", ".join(relevant_fields) if relevant_fields else "no tracked dependency"
    if wording_mode == "assert":
        return f"assert is already the strongest wording for {claim_kind}; no retry is needed"
    if fingerprint_changed is True:
        return (
            "retry warranted: a causally relevant dependency changed since the prior "
            f"resolution ({fields_text})"
        )
    if fingerprint_changed is False:
        return f"no productive retry until one of {fields_text} changes"
    return f"first resolution recorded; retry becomes worthwhile if any of {fields_text} change"


def _terminal_block_authority(
    *,
    claim_kind: FactClaimKindV1,
    rationale: str,
) -> FactAssertionAuthorityV1:
    return FactAssertionAuthorityV1(
        ladder_tier=7,
        evidence_kind=None,
        claim_kind=claim_kind,
        competent=False,
        citation_evidence_ids=(),
        rationale=redact_secret_like_values(rationale),
    )


def _select_ladder_authority(
    block: ExternalFactBlockV1,
    available_evidence: AvailableFactEvidenceCatalogV1,
) -> tuple[WordingModeV1, FactAssertionAuthorityV1 | None]:
    for tier, evidence_kind, claim_kind_to_wording in _LADDER:
        if block.claim_kind not in claim_kind_to_wording:
            continue
        competent = sorted(
            (
                item
                for item in available_evidence.items
                if item.evidence_kind == evidence_kind
                and block.claim_kind in item.competent_claim_kinds
                and _identity_bound(block, item)
            ),
            key=lambda item: item.evidence_id,
        )
        if not competent:
            continue
        wording_mode = claim_kind_to_wording[block.claim_kind]
        detail_text = "; ".join(item.detail for item in competent)
        return wording_mode, FactAssertionAuthorityV1(
            ladder_tier=tier,
            evidence_kind=evidence_kind,
            claim_kind=block.claim_kind,
            competent=True,
            citation_evidence_ids=tuple(item.evidence_id for item in competent),
            rationale=redact_secret_like_values(
                f"tier {tier} ({evidence_kind}) is competent for {block.claim_kind}: {detail_text}"
            ),
        )

    non_applicability = sorted(
        (
            item
            for item in available_evidence.items
            if item.evidence_kind == "non_applicability_evidence"
            and block.claim_kind in item.competent_claim_kinds
            and _identity_bound(block, item)
        ),
        key=lambda item: item.evidence_id,
    )
    if non_applicability:
        bases = {item.omission_basis for item in non_applicability}
        if len(bases) != 1:
            return "block", None
        basis = non_applicability[0].omission_basis
        wording_mode = "not_applicable" if basis == "not_applicable" else "omit"
        detail_text = "; ".join(item.detail for item in non_applicability)
        return wording_mode, FactAssertionAuthorityV1(
            ladder_tier=6,
            evidence_kind="non_applicability_evidence",
            claim_kind=block.claim_kind,
            competent=True,
            citation_evidence_ids=tuple(item.evidence_id for item in non_applicability),
            rationale=redact_secret_like_values(
                f"evidence-backed non-applicability ({basis}) for {block.claim_kind}: {detail_text}"
            ),
        )
    return "block", None


def resolve_external_fact_block(
    *,
    block: ExternalFactBlockV1,
    available_evidence: AvailableFactEvidenceCatalogV1,
    current_dependencies: ExternalDependencyFingerprintV1,
    previous_resolution: ExternalFactBlockResolutionV1 | None = None,
) -> ExternalFactBlockResolutionV1:
    """Resolve one block without inventing evidence or retrying unchanged dependencies."""

    block_class = classify_external_fact_block_class(
        diagnostic_code=block.diagnostic_code,
        detail=block.detail,
    )
    conflicting = tuple(
        sorted(
            item.evidence_id
            for item in available_evidence.items
            if block.claim_kind in item.competent_claim_kinds and _identity_conflicts(block, item)
        )
    )
    if conflicting:
        wording_mode: WordingModeV1 = "block"
        authority = _terminal_block_authority(
            claim_kind=block.claim_kind,
            rationale=(
                "identity conflict between block and available evidence; failing closed: "
                f"{block.detail}"
            ),
        )
    else:
        wording_mode, selected = _select_ladder_authority(block, available_evidence)
        authority = selected or _terminal_block_authority(
            claim_kind=block.claim_kind,
            rationale=f"no competent evidence resolves {block.claim_kind}: {block.detail}",
        )

    relevant_fields = causally_relevant_fingerprint_fields(block_class)
    if authority.evidence_kind == "verified_imported_knowledge":
        relevant_fields = tuple(sorted({*relevant_fields, "imported_knowledge_revision"}))
    resolution_hash = _resolution_hash(
        block=block,
        block_class=block_class,
        relevant_fields=relevant_fields,
        current_dependencies=current_dependencies,
    )
    fingerprint_changed = (
        resolution_hash != previous_resolution.resolution_hash
        if previous_resolution is not None and previous_resolution.block_id == block.block_id
        else None
    )
    prohibited_claims = tuple(mode for mode in _ASSERTIVE_WORDING_MODES if mode != wording_mode)
    residual_unknowns: tuple[str, ...]
    if wording_mode == "block":
        residual_unknowns = (f"{block.claim_kind} for {block.fact_surface} remains unresolved",)
    elif wording_mode == "qualify":
        residual_unknowns = (
            f"{block.claim_kind} is evidenced but not proven to assertion strength",
        )
    else:
        residual_unknowns = ()
    return ExternalFactBlockResolutionV1(
        block_id=block.block_id,
        fact_surface=block.fact_surface,
        claim_kind=block.claim_kind,
        block_class=block_class,
        wording_mode=wording_mode,
        authority=authority,
        conflict_detected=bool(conflicting),
        conflicting_evidence_ids=conflicting,
        prohibited_claims=prohibited_claims,
        residual_unknowns=residual_unknowns,
        causally_relevant_fingerprint_fields=tuple(sorted(relevant_fields)),
        resolution_hash=resolution_hash,
        fingerprint_changed_since_previous_resolution=fingerprint_changed,
        retry_recommended=wording_mode != "assert" and fingerprint_changed is not False,
        resume_predicate=_resume_predicate(
            wording_mode=wording_mode,
            claim_kind=block.claim_kind,
            fingerprint_changed=fingerprint_changed,
            relevant_fields=relevant_fields,
        ),
    )


__all__ = [
    "AvailableFactEvidenceCatalogV1",
    "AvailableFactEvidenceV1",
    "ExternalDependencyFingerprintV1",
    "ExternalFactBlockClassV1",
    "ExternalFactBlockResolutionV1",
    "ExternalFactBlockV1",
    "FactAssertionAuthorityV1",
    "FactClaimKindV1",
    "FactEvidenceKindV1",
    "WordingModeV1",
    "classify_external_fact_block_class",
    "resolve_external_fact_block",
]
