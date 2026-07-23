"""Typed repository-presentation plan contracts."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.facts.gating import TechnicalClaimV1
from readme_agent.registry.surface_ownership import SurfaceOperation, SurfaceOwnershipClass

PresentationDimension = Literal[
    "product_clarity",
    "audience_fit",
    "trust_signals",
    "installation_path",
    "verified_examples",
    "navigation",
    "visual_usefulness",
    "contribution_readiness",
    "maintenance_signals",
    "commercial_context",
]
FindingDisposition = Literal["satisfied", "gap", "blocked", "observation"]
ActionDisposition = Literal["eligible", "blocked", "audit_only", "manual_only"]
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.:-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OPERATIONS_BY_OWNERSHIP: dict[SurfaceOwnershipClass, set[SurfaceOperation]] = {
    "repository_file": {"audit", "propose", "local_patch"},
    "settings_api": {"audit", "propose", "remote_apply"},
    "manual_ui": {"audit", "propose", "manual_apply"},
    "product_owned": {"audit"},
    "github_generated": {"audit"},
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationFindingV1(_StrictModel):
    finding_id: str
    dimension: PresentationDimension
    surface_id: str
    disposition: FindingDisposition
    summary: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)

    @field_validator("finding_id")
    @classmethod
    def _descriptive_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError(f"invalid descriptive finding ID {value!r}")
        return value


class PlannedSourceSpanV1(_StrictModel):
    path: str
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    expected_sha256: str
    replacement_sha256: str
    purpose: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def _safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or "\\" in value or path.is_absolute() or ".." in path.parts:
            raise ValueError("source-span path must be a safe repository-relative POSIX path")
        return value

    @field_validator("expected_sha256", "replacement_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("source-span hashes must be lowercase SHA-256 values")
        return value

    @model_validator(mode="after")
    def _ordered(self) -> PlannedSourceSpanV1:
        if self.byte_end < self.byte_start:
            raise ValueError("source span byte_end must be >= byte_start")
        return self


class PresentationActionV1(_StrictModel):
    action_id: str
    surface_id: str
    region_id: str
    disposition: ActionDisposition
    depends_on: list[str] = Field(default_factory=list)
    claims: list[TechnicalClaimV1] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    ownership_class: SurfaceOwnershipClass
    proposed_operation: SurfaceOperation
    source_spans: list[PlannedSourceSpanV1] = Field(default_factory=list)
    validators: list[str] = Field(min_length=1)
    rollback: str = Field(min_length=1)
    stop_conditions: list[str] = Field(min_length=1)
    patch_sha256: str | None = None

    @field_validator("action_id")
    @classmethod
    def _descriptive_id(cls, value: str) -> str:
        if not _ID_PATTERN.fullmatch(value):
            raise ValueError(f"invalid descriptive action ID {value!r}")
        return value

    @model_validator(mode="after")
    def _eligible_patch_is_proven(self) -> PresentationActionV1:
        cited_fact_ids = sorted({fact_id for claim in self.claims for fact_id in claim.fact_ids})
        if self.fact_ids != cited_fact_ids:
            raise ValueError("action fact_ids must exactly equal the claim citation union")
        allowed_operations = _OPERATIONS_BY_OWNERSHIP[self.ownership_class]
        if self.proposed_operation not in allowed_operations:
            raise ValueError(
                f"operation {self.proposed_operation!r} is incompatible with ownership class "
                f"{self.ownership_class!r}"
            )
        if self.patch_sha256 is not None and not _SHA256_PATTERN.fullmatch(self.patch_sha256):
            raise ValueError("patch_sha256 must be a lowercase SHA-256 value")
        if self.disposition == "eligible":
            if not self.fact_ids or not self.claims:
                raise ValueError("eligible actions require fact citations and technical claims")
            if self.proposed_operation == "local_patch" and not self.source_spans:
                raise ValueError("eligible local_patch actions require bounded source spans")
            if self.proposed_operation == "local_patch" and self.patch_sha256 is None:
                raise ValueError("eligible local_patch actions require a Git patch hash")
        return self


class RepositoryPresentationPlanV1(_StrictModel):
    schema_version: Literal[1] = 1
    org_repo: str
    immutable_base_revision: str
    facts_hash: str
    source_sha256: str
    archetype: str
    findings: list[PresentationFindingV1]
    actions: list[PresentationActionV1]
    candidate_sha256: str | None = None

    @field_validator("immutable_base_revision")
    @classmethod
    def _revision_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("immutable_base_revision cannot be blank")
        return value

    @field_validator("facts_hash", "source_sha256", "candidate_sha256")
    @classmethod
    def _valid_sha256(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_PATTERN.fullmatch(value):
            raise ValueError("plan hashes must be lowercase SHA-256 values")
        return value

    @model_validator(mode="after")
    def _referential_integrity(self) -> RepositoryPresentationPlanV1:
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("presentation plan contains duplicate finding IDs")
        action_ids = [action.action_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("presentation plan contains duplicate action IDs")
        known = set(action_ids)
        for action in self.actions:
            unknown = set(action.depends_on) - known
            if unknown:
                raise ValueError(
                    f"action {action.action_id!r} has unknown dependencies {sorted(unknown)}"
                )
            if action.action_id in action.depends_on:
                raise ValueError(f"action {action.action_id!r} depends on itself")
        self._reject_cycles()
        return self

    def _reject_cycles(self) -> None:
        dependencies = {action.action_id: action.depends_on for action in self.actions}
        visited: set[str] = set()
        active: set[str] = set()

        def visit(action_id: str) -> None:
            if action_id in active:
                raise ValueError(f"presentation action dependency cycle includes {action_id!r}")
            if action_id in visited:
                return
            active.add(action_id)
            for dependency in dependencies[action_id]:
                visit(dependency)
            active.remove(action_id)
            visited.add(action_id)

        for action_id in dependencies:
            visit(action_id)
