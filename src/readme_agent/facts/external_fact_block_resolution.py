"""Deterministically resolve one external fact block against available evidence tiers.

Two independent taxonomies drive this: FactClaimKindV1 (what kind of claim a fact
surface represents) selects which evidence tier is competent to justify it, while
ExternalFactBlockClassV1 (why extraction failed) selects which
ExternalDependencyFingerprintV1 fields make a future retry worthwhile. Standalone and
not wired into the live pipeline by this module.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


# resolve_external_fact_block() lands in the next commit -- the resolution ladder,
# invalidation, and hashing logic are implemented there against this already-frozen
# contract and taxonomy.

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
]
