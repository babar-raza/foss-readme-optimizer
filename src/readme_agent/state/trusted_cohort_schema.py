"""Typed contracts for one immutable, qualified trusted delivery cohort."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.registry.models import ProviderRepositoryIdentityV1


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QualifiedTrustedCohortMemberV1(_StrictFrozenModel):
    """One source-, contract-, review-, and checksum-bound cohort member."""

    schema_version: Literal[1] = 1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    provider_identity: ProviderRepositoryIdentityV1
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    observed_target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    state_version: int = Field(ge=0)
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    lifecycle_status: Literal["TRUSTED_NO_OP_PROVEN"] = "TRUSTED_NO_OP_PROVEN"
    readme_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    facts_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    deterministic_validation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    independent_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    no_op_proof_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_cache_identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_standard_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_dependency_hashes: dict[str, str] = Field(min_length=1)
    candidate_normalization_version: str = Field(min_length=1)
    bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bundle_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bundle_path: str = Field(min_length=1)

    @model_validator(mode="after")
    def _source_is_current(self) -> QualifiedTrustedCohortMemberV1:
        if self.observed_target_head != self.source_revision:
            raise ValueError("qualified trusted cohort member must match the target head")
        if any(
            len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)
            for digest in self.prompt_dependency_hashes.values()
        ):
            raise ValueError("prompt dependency hashes must be lowercase SHA-256 values")
        return self


class TrustedCohortExclusionV1(_StrictFrozenModel):
    """Why one registry entry was not enrolled in the qualified cohort."""

    schema_version: Literal[1] = 1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    lifecycle_status: str | None = None
    content_assurance: str | None = None
    source_revision: str | None = None
    observed_target_head: str | None = None
    reasons: tuple[str, ...] = Field(min_length=1)
    bundle_path: str | None = None


class QualifiedTrustedCohortIdentityV1(_StrictFrozenModel):
    """Timestamp-free inputs that define one reproducible cohort identity."""

    schema_version: Literal[1] = 1
    control_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_standard_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_normalization_version: str = Field(min_length=1)
    member_bindings: tuple[dict[str, str | int], ...]

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class QualifiedTrustedCohortV1(_StrictFrozenModel):
    """Immutable delivery cohort derived only from live state and valid bundles."""

    schema_version: Literal[1] = 1
    cohort_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    registry_path: str = Field(min_length=1)
    registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_at: str = Field(min_length=1)
    reviewer_standard_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_registry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_normalization_version: str = Field(min_length=1)
    content_assurance: Literal["trusted_inherited"] = "trusted_inherited"
    factual_truth_verified: Literal[False] = False
    registry_denominator: int = Field(ge=1)
    qualified_count: int = Field(ge=1)
    members: tuple[QualifiedTrustedCohortMemberV1, ...] = Field(min_length=1)
    exclusions: tuple[TrustedCohortExclusionV1, ...] = ()

    def identity(self) -> QualifiedTrustedCohortIdentityV1:
        bindings: list[dict[str, str | int]] = []
        for member in self.members:
            bindings.append(
                {
                    "org_repo": member.org_repo,
                    "repository_id": member.provider_identity.repository_id,
                    "source_revision": member.source_revision,
                    "candidate_sha256": member.candidate_sha256,
                    "bundle_manifest_sha256": member.bundle_manifest_sha256,
                    "bundle_inventory_sha256": member.bundle_inventory_sha256,
                    "state_version": member.state_version,
                }
            )
        return QualifiedTrustedCohortIdentityV1(
            control_revision=self.control_revision,
            registry_sha256=self.registry_sha256,
            reviewer_standard_sha256=self.reviewer_standard_sha256,
            prompt_registry_sha256=self.prompt_registry_sha256,
            candidate_normalization_version=self.candidate_normalization_version,
            member_bindings=tuple(bindings),
        )

    @model_validator(mode="after")
    def _counts_order_and_identity_match(self) -> QualifiedTrustedCohortV1:
        if self.qualified_count != len(self.members):
            raise ValueError("qualified_count does not match members")
        if self.registry_denominator != len(self.members) + len(self.exclusions):
            raise ValueError("every registry entry must be a member or an exclusion")
        member_names = [member.org_repo for member in self.members]
        exclusion_names = [item.org_repo for item in self.exclusions]
        if member_names != sorted(member_names):
            raise ValueError("cohort members must use deterministic repository ordering")
        if exclusion_names != sorted(exclusion_names):
            raise ValueError("cohort exclusions must use deterministic repository ordering")
        if set(member_names) & set(exclusion_names):
            raise ValueError("a repository cannot be both enrolled and excluded")
        if len(set(member_names + exclusion_names)) != self.registry_denominator:
            raise ValueError("cohort repository accounting must be unique")
        if self.identity().canonical_hash() != self.cohort_id:
            raise ValueError("cohort_id does not match the canonical member bindings")
        return self


class TrustedCohortReconstructionV1(_StrictFrozenModel):
    """Independent same-input reconstruction verdict for a frozen cohort."""

    schema_version: Literal[1] = 1
    cohort_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reconstructed_cohort_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    ordered_members: tuple[str, ...]
    reconstructed_ordered_members: tuple[str, ...]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    passed: bool
    reasons: tuple[str, ...]
