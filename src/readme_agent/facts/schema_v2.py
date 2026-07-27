"""Provenance-complete ProductFactsV2 contracts and stable field inventory."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.facts.evidence_polarity import EvidencePolarityAssessmentV1
from readme_agent.facts.root_role_schema import PackageRootRoleInventoryV1

FactSourceType = Literal[
    "mechanical_repository",
    "mechanical_manifest",
    "mechanical_test",
    "external_registry",
    "approved_policy",
    "release",
    "approved_documentation",
    "readme_claim",
    "agent_drafted",
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

# Fields whose value requires product interpretation or a runnable example
# rather than manifest parsing alone. The canonical product-truth stage uses
# this to decide whether the governed drafting capability is necessary.
README_DRAFTABLE_PRODUCT_FIELDS = (
    "product.audience",
    "product.problems_solved",
    "product.capabilities",
    "product.formats",
    "product.limitations",
    "example.minimal",
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
    evidence_assessments: list[EvidencePolarityAssessmentV1] | None = None
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

    @model_validator(mode="after")
    def _enforce_agent_drafted_boundary(self) -> FactRecordV2:
        # agent_drafted differs from readme_claim: by construction it has already
        # passed a real mechanical/citation gate upstream (see facts/interpretive_evidence.py
        # and facts/policy_evidence.py), so it CAN reach 'verified'. It can never reach
        # 'policy_approved' though -- that state must keep meaning "a human explicitly
        # signed off in policy YAML", and no machine draft gets to claim that for itself.
        is_agent_drafted = self.source.source_type == "agent_drafted"
        if is_agent_drafted and self.verification_state == "policy_approved":
            raise ValueError(
                "agent-drafted facts cannot claim policy_approved; "
                "that state requires explicit human sign-off in policy YAML"
            )
        return self

    @model_validator(mode="after")
    def _bind_directional_evidence(self) -> FactRecordV2:
        if self.evidence_assessments is None:
            return self
        expected_polarity = (
            "explicit_constraint"
            if self.field == "product.limitations"
            else "positive_implementation"
        )
        for assessment in self.evidence_assessments:
            if assessment.fact_id != self.fact_id:
                raise ValueError("evidence assessment fact ID must match its fact record")
            if assessment.expected_polarity != expected_polarity:
                raise ValueError("evidence assessment polarity must match the fact field")
            if (
                self.source.source_revision is not None
                and assessment.source_revision != self.source.source_revision
            ):
                raise ValueError("evidence assessment revision must match its fact source")
            if (
                self.verification_state in {"verified", "policy_approved"}
                and not assessment.accepted
            ):
                raise ValueError("accepted fact cannot retain rejected directional evidence")
        return self

    @property
    def has_unresolved_conflict(self) -> bool:
        return any(conflict.status == "unresolved" for conflict in self.conflicts)


class ProductFactsV2(_StrictModel):
    schema_version: Literal[2] = 2
    org_repo: str
    facts: list[FactRecordV2]
    selected_fact_ids: dict[str, str]
    package_root_roles: PackageRootRoleInventoryV1 | None = None

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
        payload = self.model_dump(mode="json")
        # Additive migration: facts persisted before root-role classification have
        # no package_root_roles key. Preserve their canonical hash so the current
        # acceptance-contract mismatch can trigger a governed recollection instead
        # of looking like evidence corruption.
        if self.package_root_roles is None:
            payload.pop("package_root_roles", None)
        for fact, fact_payload in zip(self.facts, payload["facts"], strict=True):
            if fact.evidence_assessments is None:
                fact_payload.pop("evidence_assessments", None)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def descriptive_fact_id(field_name: str, qualifier: str = "primary") -> str:
    """Build a stable, human-readable ID from the canonical field inventory."""

    normalized = re.sub(r"[^a-z0-9_.:/@-]+", "-", qualifier.lower()).strip("-")
    return f"{field_name}:{normalized or 'primary'}"
