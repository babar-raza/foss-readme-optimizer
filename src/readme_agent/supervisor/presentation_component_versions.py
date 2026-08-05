"""Semantic versioning and delta classification for presentation components."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PresentationSemanticScopeV1 = Literal[
    "cosmetic",
    "structural",
    "prose_policy",
    "fact_slot",
    "factuality",
    "safety",
    "protected_content",
    "severe_acceptance",
]
ComponentDeltaOutcomeV1 = Literal["UNCHANGED", "VALID_UPDATE_AVAILABLE", "INVALIDATED"]
AffectedStageV1 = Literal[
    "FACTS_COLLECTING",
    "README_ASSESSED",
    "PLAN_READY",
    "CANDIDATE_GENERATED",
    "DETERMINISTIC_VALIDATED",
    "AGENT_REVIEWING",
    "REPAIRING",
]

_NONCRITICAL_SCOPES = {"cosmetic", "structural", "prose_policy", "fact_slot"}
_STAGE_ORDER = {
    "FACTS_COLLECTING": 0,
    "README_ASSESSED": 1,
    "PLAN_READY": 2,
    "CANDIDATE_GENERATED": 3,
    "DETERMINISTIC_VALIDATED": 4,
    "AGENT_REVIEWING": 5,
    "REPAIRING": 6,
}


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SelectedDependencyV1(_StrictFrozenModel):
    dependency_id: str = Field(min_length=3)
    files: dict[str, str] = Field(min_length=1)
    semantic_scope: PresentationSemanticScopeV1 = "factuality"
    earliest_affected_stage: AffectedStageV1 = "FACTS_COLLECTING"
    component_version: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("files")
    @classmethod
    def _hashes_are_sha256(cls, value: dict[str, str]) -> dict[str, str]:
        invalid = any(
            len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)
            for digest in value.values()
        )
        if invalid:
            raise ValueError("dependency file identities must be lowercase SHA-256")
        return dict(sorted(value.items()))

    @model_validator(mode="after")
    def _version_matches_component(self) -> SelectedDependencyV1:
        expected = canonical_sha256(
            {
                "dependency_id": self.dependency_id,
                "files": self.files,
                "semantic_scope": self.semantic_scope,
                "earliest_affected_stage": self.earliest_affected_stage,
            }
        )
        if self.component_version is not None and self.component_version != expected:
            raise ValueError("component_version does not match the component contract")
        object.__setattr__(self, "component_version", expected)
        return self


class ComponentDeltaV1(_StrictFrozenModel):
    """Semantic delta between two independently versioned component manifests."""

    schema_version: Literal[1] = 1
    outcome: ComponentDeltaOutcomeV1
    changed_component_ids: list[str]
    changed_scopes: list[PresentationSemanticScopeV1]
    fact_validity_preserved: bool
    presentation_validity_preserved: bool
    earliest_affected_stage: AffectedStageV1 | None = None


class ComponentManifestProtocol(Protocol):
    repository: str
    source_revision: str
    stage: Any
    ecosystem: str
    upstream_receipt_ids: list[str]
    dependencies: list[SelectedDependencyV1]


def classify_component_delta(
    prior: ComponentManifestProtocol,
    current: ComponentManifestProtocol,
) -> ComponentDeltaV1:
    """Classify an exact component delta without invalidating unrelated assurance axes."""

    if (
        prior.repository != current.repository
        or prior.source_revision != current.source_revision
        or prior.stage != current.stage
        or prior.ecosystem != current.ecosystem
        or prior.upstream_receipt_ids != current.upstream_receipt_ids
    ):
        return ComponentDeltaV1(
            outcome="INVALIDATED",
            changed_component_ids=["manifest_identity"],
            changed_scopes=["factuality"],
            fact_validity_preserved=False,
            presentation_validity_preserved=False,
            earliest_affected_stage="FACTS_COLLECTING",
        )
    prior_by_id = {item.dependency_id: item for item in prior.dependencies}
    current_by_id = {item.dependency_id: item for item in current.dependencies}
    changed_ids = sorted(
        component_id
        for component_id in set(prior_by_id) | set(current_by_id)
        if prior_by_id.get(component_id) != current_by_id.get(component_id)
    )
    if not changed_ids:
        return ComponentDeltaV1(
            outcome="UNCHANGED",
            changed_component_ids=[],
            changed_scopes=[],
            fact_validity_preserved=True,
            presentation_validity_preserved=True,
        )
    changed = [
        component
        for component_id in changed_ids
        for component in (prior_by_id.get(component_id), current_by_id.get(component_id))
        if component is not None
    ]
    scopes = sorted({item.semantic_scope for item in changed})
    earliest = min((item.earliest_affected_stage for item in changed), key=_STAGE_ORDER.__getitem__)
    if set(scopes) <= _NONCRITICAL_SCOPES:
        return ComponentDeltaV1(
            outcome="VALID_UPDATE_AVAILABLE",
            changed_component_ids=changed_ids,
            changed_scopes=scopes,
            fact_validity_preserved=True,
            presentation_validity_preserved=True,
            earliest_affected_stage=earliest,
        )
    return ComponentDeltaV1(
        outcome="INVALIDATED",
        changed_component_ids=changed_ids,
        changed_scopes=scopes,
        fact_validity_preserved="factuality" not in scopes,
        presentation_validity_preserved=False,
        earliest_affected_stage=earliest,
    )
