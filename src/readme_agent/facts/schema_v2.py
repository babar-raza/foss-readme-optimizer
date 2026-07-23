"""Provenance-complete ProductFactsV2 contracts and stable field inventory."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FactSourceType = Literal[
    "mechanical_repository",
    "mechanical_manifest",
    "mechanical_test",
    "external_registry",
    "approved_policy",
    "release",
    "approved_documentation",
    "readme_claim",
]
FactVerificationState = Literal[
    "verified",
    "policy_approved",
    "unverified",
    "missing",
    "conflicting",
    "blocked",
]
ConflictStatus = Literal["unresolved", "resolved_by_precedence", "owner_resolved"]

# Canonical inventory required by decision #75/L8-006. Descriptive IDs deliberately
# remain stable across runs and avoid sequence-number machinery names.
REQUIRED_PRODUCT_FIELDS = (
    "product.identity",
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.platforms",
    "installation.coordinates",
    "installation.verified_acquisition",
    "example.minimal",
    "documentation.links",
    "release.state",
    "product.limitations",
    "product.compatibility",
    "product.license",
    "support.routes",
    "relationship.commercial_foss",
)

_FACT_ID_RE = re.compile(r"^[a-z][a-z0-9_.:@/-]*$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactSourceV2(_StrictModel):
    source_type: FactSourceType
    location: str = Field(min_length=1)
    source_revision: str | None = None
    retrieved_at: str | None = None

    @model_validator(mode="after")
    def _has_revision_or_retrieval_time(self) -> FactSourceV2:
        if self.source_revision is None and self.retrieved_at is None:
            raise ValueError("fact source requires source_revision or retrieved_at")
        return self


class FactConflictV2(_StrictModel):
    conflicting_fact_id: str
    conflicting_value: Any
    conflicting_source: FactSourceV2
    status: ConflictStatus
    reason: str = Field(min_length=1)
    authoritative_owner: str = Field(min_length=1)
    affected_surfaces: list[str] = Field(min_length=1)

    @field_validator("conflicting_fact_id")
    @classmethod
    def _valid_conflicting_fact_id(cls, value: str) -> str:
        if not _FACT_ID_RE.fullmatch(value):
            raise ValueError(f"invalid descriptive fact ID {value!r}")
        return value


class FactRecordV2(_StrictModel):
    fact_id: str
    field: str
    value: Any = None
    source: FactSourceV2
    verification_state: FactVerificationState
    authoritative_owner: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    conflicts: list[FactConflictV2] = Field(default_factory=list)
    affected_surfaces: list[str] = Field(min_length=1)

    @field_validator("fact_id", "field")
    @classmethod
    def _valid_descriptive_id(cls, value: str) -> str:
        if not _FACT_ID_RE.fullmatch(value):
            raise ValueError(f"invalid descriptive fact ID/field {value!r}")
        return value

    @model_validator(mode="after")
    def _enforce_untrusted_readme_boundary(self) -> FactRecordV2:
        if self.source.source_type == "readme_claim" and self.verification_state not in {
            "unverified",
            "conflicting",
            "blocked",
        }:
            raise ValueError("README prose is untrusted data and cannot be verified by itself")
        if self.verification_state == "missing" and self.value is not None:
            raise ValueError("a missing fact must have value=None")
        if any(conflict.status == "unresolved" for conflict in self.conflicts):
            if self.verification_state != "conflicting":
                raise ValueError("unresolved conflicts require verification_state='conflicting'")
        return self

    @property
    def has_unresolved_conflict(self) -> bool:
        return any(conflict.status == "unresolved" for conflict in self.conflicts)


class ProductFactsV2(_StrictModel):
    schema_version: Literal[2] = 2
    org_repo: str
    facts: list[FactRecordV2]
    selected_fact_ids: dict[str, str]

    @field_validator("org_repo")
    @classmethod
    def _valid_org_repo(cls, value: str) -> str:
        parts = value.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("org_repo must be 'org/repo'")
        return value

    @model_validator(mode="after")
    def _unique_and_referentially_complete(self) -> ProductFactsV2:
        by_id = {fact.fact_id: fact for fact in self.facts}
        if len(by_id) != len(self.facts):
            raise ValueError("ProductFactsV2 fact_id values must be unique")
        for field_name, fact_id in self.selected_fact_ids.items():
            fact = by_id.get(fact_id)
            if fact is None:
                raise ValueError(f"selected fact {fact_id!r} does not exist")
            if fact.field != field_name:
                raise ValueError(f"selected field {field_name!r} points to fact for {fact.field!r}")
        missing_selections = set(REQUIRED_PRODUCT_FIELDS) - set(self.selected_fact_ids)
        if missing_selections:
            raise ValueError(
                f"ProductFactsV2 is missing required field selections: {sorted(missing_selections)}"
            )
        return self

    def fact_by_id(self, fact_id: str) -> FactRecordV2:
        for fact in self.facts:
            if fact.fact_id == fact_id:
                return fact
        raise KeyError(fact_id)

    def selected_fact(self, field_name: str) -> FactRecordV2:
        try:
            fact_id = self.selected_fact_ids[field_name]
        except KeyError as exc:
            raise KeyError(f"no selected fact for field {field_name!r}") from exc
        return self.fact_by_id(fact_id)

    def facts_for_field(self, field_name: str) -> list[FactRecordV2]:
        return [fact for fact in self.facts if fact.field == field_name]

    def canonical_hash(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def descriptive_fact_id(field_name: str, qualifier: str = "primary") -> str:
    """Build a stable, human-readable ID from the canonical field inventory."""

    normalized = re.sub(r"[^a-z0-9_.:/@-]+", "-", qualifier.lower()).strip("-")
    return f"{field_name}:{normalized or 'primary'}"
