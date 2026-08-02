"""Selected dependency manifests for narrow repository-stage invalidation."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StageNameV1 = Literal["SNAPSHOT", "FACTS", "CANDIDATE", "DETERMINISTIC", "APPROVAL", "NOOP"]


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SelectedDependencyV1(_StrictFrozenModel):
    dependency_id: str = Field(min_length=3)
    files: dict[str, str] = Field(min_length=1)

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


class StageDependencyManifestV1(_StrictFrozenModel):
    schema_version: Literal["StageDependencyManifestV1"] = "StageDependencyManifestV1"
    repository: str
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    stage: StageNameV1
    ecosystem: str
    upstream_receipt_ids: list[str] = Field(default_factory=list)
    dependencies: list[SelectedDependencyV1] = Field(min_length=1)
    stage_key: str = Field(pattern=r"^[0-9a-f]{64}$")


def build_stage_dependency_manifest(
    *,
    repository: str,
    source_revision: str,
    stage: StageNameV1,
    ecosystem: str,
    dependencies: list[SelectedDependencyV1],
    upstream_receipt_ids: list[str] | None = None,
) -> StageDependencyManifestV1:
    """Hash only dependencies selected for this stage and ecosystem."""

    ordered = sorted(dependencies, key=lambda item: item.dependency_id)
    upstream = sorted(upstream_receipt_ids or [])
    identity: dict[str, object] = {
        "repository": repository,
        "source_revision": source_revision,
        "stage": stage,
        "ecosystem": ecosystem,
        "upstream_receipt_ids": upstream,
        "dependencies": [item.model_dump(mode="json") for item in ordered],
    }
    return StageDependencyManifestV1(
        repository=repository,
        source_revision=source_revision,
        stage=stage,
        ecosystem=ecosystem,
        upstream_receipt_ids=upstream,
        dependencies=ordered,
        stage_key=canonical_sha256(identity),
    )


def invalidated_stage(
    prior: StageDependencyManifestV1,
    current: StageDependencyManifestV1,
) -> bool:
    """Return whether the exact selected stage contract changed."""

    return prior.stage_key != current.stage_key
