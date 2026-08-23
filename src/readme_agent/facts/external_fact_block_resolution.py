"""Deterministically resolve one external fact block against available evidence tiers.

Two independent taxonomies drive this: FactClaimKindV1 (what kind of claim a fact
surface represents) selects which evidence tier is competent to justify it, while
ExternalFactBlockClassV1 (why extraction failed) selects which
ExternalDependencyFingerprintV1 fields make a future retry worthwhile. Standalone and
not wired into the live pipeline by this module.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.evidence.redaction import redact_secret_like_values

# Bare Literals, not one-field wrapper models, to match this repo's own convention for
# closed-vocabulary enums (BlockedCategory, AcquisitionOutcome, ProductTruthOutcome) --
# V1 suffixes are reserved for BaseModel schemas elsewhere in this package.
FactClaimKindV1 = Literal[
    "identity_coordinates",
    "static_existence",
    "example_execution",
    "runtime_behavior",
]

ExternalFactBlockClassV1 = Literal[
    "repository_clone_failure",
    "git_lfs_object_unavailable",
    "package_registry_unavailable",
    "package_version_unresolved",
    "toolchain_unavailable",
    "dependency_resolution_failure",
    "example_runtime_unavailable",
    "source_package_mismatch",
    "network_rate_limited",
    "corrupt_local_cache",
    "unsupported_platform_verifier",
    "external_authentication_unavailable",
    "unknown",
]

FactEvidenceKindV1 = Literal[
    "current_source_or_manifest",
    "committed_distribution_metadata",
    "static_public_api_or_source",
    "verified_imported_knowledge",
    "syntax_verified_example",
    "non_applicability_evidence",
]

WordingModeV1 = Literal["assert", "qualify", "omit", "block", "not_applicable"]

_ORG_REPO_PATTERN = r"^[^/]+/[^/]+$"

# The non-block wording modes, in fixed display order -- used to compute
# prohibited_claims as "every other assertive-or-omitting mode than the one granted".
_ASSERTIVE_WORDING_MODES: tuple[WordingModeV1, ...] = (
    "assert",
    "qualify",
    "omit",
    "not_applicable",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalFactBlockV1(_StrictModel):
    """One external fact block, as reported by whatever extraction path failed."""

    block_id: str = Field(min_length=1)
    # Opaque; never pattern-matched -- this is what keeps the module product-,
    # family-, and license-policy-agnostic.
    fact_surface: str = Field(min_length=1)
    claim_kind: FactClaimKindV1
    diagnostic_code: str | None = None
    detail: str = Field(min_length=1)
    org_repo: str = Field(pattern=_ORG_REPO_PATTERN)
    source_revision: str | None = None
    package_identity: str | None = None


class AvailableFactEvidenceV1(_StrictModel):
    """One catalogued piece of substitute evidence a resolver may cite."""

    evidence_id: str = Field(min_length=1)
    evidence_kind: FactEvidenceKindV1
    competent_claim_kinds: tuple[FactClaimKindV1, ...] = Field(min_length=1)
    org_repo: str = Field(pattern=_ORG_REPO_PATTERN)
    source_revision: str | None = None
    package_identity: str | None = None
    omission_basis: Literal["not_applicable", "omit"] | None = None
    detail: str = Field(min_length=1)

    @model_validator(mode="after")
    def _omission_basis_only_for_non_applicability_evidence(self) -> AvailableFactEvidenceV1:
        required = self.evidence_kind == "non_applicability_evidence"
        if required and self.omission_basis is None:
            raise ValueError("non_applicability_evidence requires an omission_basis")
        if not required and self.omission_basis is not None:
            raise ValueError("omission_basis is only meaningful for non_applicability_evidence")
        return self


class AvailableFactEvidenceCatalogV1(_StrictModel):
    """The complete evidence set the resolver is allowed to consider for one block."""

    org_repo: str = Field(pattern=_ORG_REPO_PATTERN)
    source_revision: str | None = None
    items: tuple[AvailableFactEvidenceV1, ...] = ()

    @model_validator(mode="after")
    def _unique_evidence_ids(self) -> AvailableFactEvidenceCatalogV1:
        ids = [item.evidence_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence_id must be unique within one catalog")
        return self


class ExternalDependencyFingerprintV1(_StrictModel):
    """Current-state fingerprints for the external systems a block might depend on.

    `source_revision` here is the *current* upstream revision, distinct from
    `ExternalFactBlockV1.source_revision` (the revision the block was raised against) --
    the two can legitimately differ, and that difference is the retry signal for e.g.
    repository_clone_failure. Deliberately no timestamp field: retry eligibility must
    never key off wall-clock age, only semantic dependency change.
    """

    schema_version: Literal[1] = 1
    source_revision: str | None = None
    repository_remote_fingerprint: str | None = None
    git_lfs_endpoint_fingerprint: str | None = None
    package_registry_snapshot_hash: str | None = None
    dependency_manifest_hash: str | None = None
    toolchain_fingerprint: str | None = None
    execution_environment_fingerprint: str | None = None
    network_policy_fingerprint: str | None = None
    local_cache_fingerprint: str | None = None
    authentication_context_fingerprint: str | None = None
    imported_knowledge_revision: str | None = None


class FactAssertionAuthorityV1(_StrictModel):
    """The single strongest evidence tier that actually applied to this block."""

    ladder_tier: Literal[1, 2, 3, 4, 5, 6, 7]  # 7 == remained blocked, no evidence applied
    evidence_kind: FactEvidenceKindV1 | None  # None only when ladder_tier == 7
    claim_kind: FactClaimKindV1
    competent: bool
    citation_evidence_ids: tuple[str, ...]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _tier_seven_cites_nothing(self) -> FactAssertionAuthorityV1:
        if self.ladder_tier == 7:
            if self.evidence_kind is not None or self.citation_evidence_ids or self.competent:
                raise ValueError("tier 7 (remained blocked) cannot cite justifying evidence")
        elif self.evidence_kind is None:
            raise ValueError("a resolved tier must record which evidence kind justified it")
        return self


class ExternalFactBlockResolutionV1(_StrictModel):
    """The deterministic outcome of resolving one ExternalFactBlockV1."""

    schema_version: Literal[1] = 1
    block_id: str
    fact_surface: str
    claim_kind: FactClaimKindV1
    block_class: ExternalFactBlockClassV1
    wording_mode: WordingModeV1
    authority: FactAssertionAuthorityV1
    conflict_detected: bool
    conflicting_evidence_ids: tuple[str, ...]
    prohibited_claims: tuple[WordingModeV1, ...]
    residual_unknowns: tuple[str, ...]
    causally_relevant_fingerprint_fields: tuple[str, ...]
    resolution_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    fingerprint_changed_since_previous_resolution: bool | None
    retry_recommended: bool
    resume_predicate: str = Field(min_length=1)

    @model_validator(mode="after")
    def _structural_guarantees(self) -> ExternalFactBlockResolutionV1:
        if self.authority.claim_kind != self.claim_kind:
            raise ValueError("authority.claim_kind must match the resolution's claim_kind")
        if self.conflict_detected != bool(self.conflicting_evidence_ids):
            raise ValueError("conflict_detected must agree with conflicting_evidence_ids")
        if self.conflict_detected and self.wording_mode != "block":
            raise ValueError("an identity conflict must fail closed to block")
        if self.wording_mode == "assert" and (
            not self.authority.competent
            or self.authority.ladder_tier not in (1, 2, 3)
            or not self.authority.citation_evidence_ids
        ):
            raise ValueError("assert requires competent top-tier (1-3) evidence")
        if self.wording_mode in ("not_applicable", "omit") and self.authority.ladder_tier != 6:
            raise ValueError("not_applicable/omit requires tier 6 (non-applicability evidence)")
        if self.wording_mode == "block" and self.authority.citation_evidence_ids:
            raise ValueError("a blocked resolution cannot cite justifying evidence")
        return self


# --- classification ---------------------------------------------------------

_DIAGNOSTIC_CODE_TO_BLOCK_CLASS: dict[str, ExternalFactBlockClassV1] = {
    "GIT_CLONE_FAILED": "repository_clone_failure",
    "GIT_LFS_OBJECT_MISSING": "git_lfs_object_unavailable",
    "REGISTRY_UNAVAILABLE": "package_registry_unavailable",
    "PACKAGE_VERSION_NOT_FOUND": "package_version_unresolved",
    "TOOLCHAIN_UNAVAILABLE": "toolchain_unavailable",
    "DEPENDENCY_RESOLUTION_FAILED": "dependency_resolution_failure",
    "EXAMPLE_RUNTIME_UNAVAILABLE": "example_runtime_unavailable",
    "SOURCE_PACKAGE_MISMATCH": "source_package_mismatch",
    "NETWORK_RATE_LIMITED": "network_rate_limited",
    "LOCAL_CACHE_CORRUPT": "corrupt_local_cache",
    "PLATFORM_VERIFIER_UNSUPPORTED": "unsupported_platform_verifier",
    "EXTERNAL_AUTHENTICATION_UNAVAILABLE": "external_authentication_unavailable",
}

# Order encodes real precedence: an LFS failure message often also mentions "clone",
# so the more specific substring is checked first.
_DETAIL_SUBSTRING_TO_BLOCK_CLASS: tuple[tuple[str, ExternalFactBlockClassV1], ...] = (
    ("git lfs", "git_lfs_object_unavailable"),
    ("clone failed", "repository_clone_failure"),
    ("registry unavailable", "package_registry_unavailable"),
    ("version not found", "package_version_unresolved"),
    ("toolchain", "toolchain_unavailable"),
    ("dependency resolution", "dependency_resolution_failure"),
    ("example runtime", "example_runtime_unavailable"),
    ("package mismatch", "source_package_mismatch"),
    ("rate limit", "network_rate_limited"),
    ("cache corrupt", "corrupt_local_cache"),
    ("platform", "unsupported_platform_verifier"),
    ("authentication", "external_authentication_unavailable"),
)


def classify_external_fact_block_class(
    *, diagnostic_code: str | None, detail: str
) -> ExternalFactBlockClassV1:
    """Prefer an exact structured diagnostic_code match; fall back to a bounded
    substring scan of detail only when no structured code is recognized; never guess --
    default to "unknown"."""

    if diagnostic_code is not None and diagnostic_code in _DIAGNOSTIC_CODE_TO_BLOCK_CLASS:
        return _DIAGNOSTIC_CODE_TO_BLOCK_CLASS[diagnostic_code]
    folded = detail.casefold()
    for substring, block_class in _DETAIL_SUBSTRING_TO_BLOCK_CLASS:
        if substring in folded:
            return block_class
    return "unknown"


# --- resolution ladder -------------------------------------------------------

# tier -> (evidence_kind, {claim_kind: wording_mode})
_LADDER: tuple[
    tuple[Literal[1, 2, 3, 4, 5], FactEvidenceKindV1, dict[FactClaimKindV1, WordingModeV1]], ...
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

_CAUSALLY_RELEVANT_FIELDS_BY_BLOCK_CLASS: dict[ExternalFactBlockClassV1, tuple[str, ...]] = {
    "repository_clone_failure": ("source_revision", "repository_remote_fingerprint"),
    "git_lfs_object_unavailable": ("source_revision", "git_lfs_endpoint_fingerprint"),
    "package_registry_unavailable": (
        "package_registry_snapshot_hash",
        "network_policy_fingerprint",
    ),
    "package_version_unresolved": ("package_registry_snapshot_hash", "dependency_manifest_hash"),
    "toolchain_unavailable": ("toolchain_fingerprint",),
    "dependency_resolution_failure": (
        "dependency_manifest_hash",
        "package_registry_snapshot_hash",
    ),
    "example_runtime_unavailable": ("execution_environment_fingerprint", "toolchain_fingerprint"),
    "source_package_mismatch": ("source_revision", "package_registry_snapshot_hash"),
    "network_rate_limited": ("network_policy_fingerprint",),
    "corrupt_local_cache": ("local_cache_fingerprint",),
    "unsupported_platform_verifier": (
        "execution_environment_fingerprint",
        "toolchain_fingerprint",
    ),
    "external_authentication_unavailable": (
        "authentication_context_fingerprint",
        "network_policy_fingerprint",
    ),
    # Fail-open: the cause itself is unclassified, so every tracked dependency is
    # treated as potentially causal.
    "unknown": (
        "source_revision",
        "repository_remote_fingerprint",
        "git_lfs_endpoint_fingerprint",
        "package_registry_snapshot_hash",
        "dependency_manifest_hash",
        "toolchain_fingerprint",
        "execution_environment_fingerprint",
        "network_policy_fingerprint",
        "local_cache_fingerprint",
        "authentication_context_fingerprint",
    ),
}


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
    """Evidence with an absent identity field where the block has a concrete value is
    neither a conflict nor a match -- it is simply incompetent, and is skipped by the
    ladder as if it weren't in the catalog. Which identity field matters depends on the
    evidence kind: distribution metadata binds on package identity (it has no notion of
    a git revision); every other evidence kind here is source-derived and binds on
    source revision."""

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
        return (
            f"assert is already the strongest available wording for {claim_kind}; "
            "no retry is needed"
        )
    if fingerprint_changed is True:
        return (
            "retry warranted: a causally relevant dependency changed since the prior "
            f"resolution ({fields_text})"
        )
    if fingerprint_changed is False:
        return f"no productive retry until one of {fields_text} changes"
    return f"first resolution recorded; retry becomes worthwhile if any of {fields_text} change"


def _select_ladder_authority(
    block: ExternalFactBlockV1, available_evidence: AvailableFactEvidenceCatalogV1
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
        authority = FactAssertionAuthorityV1(
            ladder_tier=tier,
            evidence_kind=evidence_kind,
            claim_kind=block.claim_kind,
            competent=True,
            citation_evidence_ids=tuple(item.evidence_id for item in competent),
            rationale=redact_secret_like_values(
                f"tier {tier} ({evidence_kind}) is competent for {block.claim_kind}: {detail_text}"
            ),
        )
        return wording_mode, authority

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
        basis = non_applicability[0].omission_basis
        wording_mode = "not_applicable" if basis == "not_applicable" else "omit"
        detail_text = "; ".join(item.detail for item in non_applicability)
        authority = FactAssertionAuthorityV1(
            ladder_tier=6,
            evidence_kind="non_applicability_evidence",
            claim_kind=block.claim_kind,
            competent=True,
            citation_evidence_ids=tuple(item.evidence_id for item in non_applicability),
            rationale=redact_secret_like_values(
                f"evidence-backed non-applicability ({basis}) for {block.claim_kind}: {detail_text}"
            ),
        )
        return wording_mode, authority

    return "block", None


def resolve_external_fact_block(
    *,
    block: ExternalFactBlockV1,
    available_evidence: AvailableFactEvidenceCatalogV1,
    current_dependencies: ExternalDependencyFingerprintV1,
    previous_resolution: ExternalFactBlockResolutionV1 | None = None,
) -> ExternalFactBlockResolutionV1:
    block_class = classify_external_fact_block_class(
        diagnostic_code=block.diagnostic_code, detail=block.detail
    )

    # Only evidence actually competent for this claim kind can conflict -- an
    # unrelated catalog entry must never spuriously block an unrelated claim. A real
    # identity mismatch on competent evidence fails the whole resolution closed,
    # regardless of what any other evidence item says (never pick convenient evidence).
    conflicting = tuple(
        sorted(
            item.evidence_id
            for item in available_evidence.items
            if block.claim_kind in item.competent_claim_kinds and _identity_conflicts(block, item)
        )
    )

    wording_mode: WordingModeV1
    resolved_authority: FactAssertionAuthorityV1 | None
    if conflicting:
        wording_mode = "block"
        resolved_authority = FactAssertionAuthorityV1(
            ladder_tier=7,
            evidence_kind=None,
            claim_kind=block.claim_kind,
            competent=False,
            citation_evidence_ids=(),
            rationale=redact_secret_like_values(
                "identity conflict between block and available evidence; failing closed: "
                f"{block.detail}"
            ),
        )
    else:
        wording_mode, resolved_authority = _select_ladder_authority(block, available_evidence)

    if resolved_authority is None:
        resolved_authority = FactAssertionAuthorityV1(
            ladder_tier=7,
            evidence_kind=None,
            claim_kind=block.claim_kind,
            competent=False,
            citation_evidence_ids=(),
            rationale=redact_secret_like_values(
                f"no competent evidence resolves {block.claim_kind} for this block: {block.detail}"
            ),
        )
    authority: FactAssertionAuthorityV1 = resolved_authority

    relevant_fields = _CAUSALLY_RELEVANT_FIELDS_BY_BLOCK_CLASS[block_class]
    if authority.evidence_kind == "verified_imported_knowledge":
        relevant_fields = tuple(sorted({*relevant_fields, "imported_knowledge_revision"}))

    resolution_hash = _resolution_hash(
        block=block,
        block_class=block_class,
        relevant_fields=relevant_fields,
        current_dependencies=current_dependencies,
    )

    fingerprint_changed: bool | None
    if previous_resolution is not None and previous_resolution.block_id == block.block_id:
        fingerprint_changed = resolution_hash != previous_resolution.resolution_hash
    else:
        fingerprint_changed = None

    retry_recommended = wording_mode != "assert" and fingerprint_changed is not False

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
        retry_recommended=retry_recommended,
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
