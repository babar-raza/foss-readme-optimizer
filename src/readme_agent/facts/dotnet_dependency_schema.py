"""Typed provenance for an offline NuGet dependency cache."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.facts.isolated_execution_schema import ContainerImageIdentityV1

NUGET_ORG_V3_SOURCE: Literal["https://api.nuget.org/v3/index.json"] = (
    "https://api.nuget.org/v3/index.json"
)


class DotnetPackageArtifactV1(BaseModel):
    """One complete package/version directory admitted to offline restore."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    package_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    relative_path: str = Field(pattern=r"^[^/\\]+/[^/\\]+$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_count: int = Field(ge=1)
    size_bytes: int = Field(gt=0)


class DotnetRepositoryArtifactV1(BaseModel):
    """One immutable Git LFS dependency materialized for an offline repository build."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https://media\.githubusercontent\.com/media/")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)

    @field_validator("relative_path")
    @classmethod
    def path_stays_inside_repository(cls, value: str) -> str:
        parts = value.split("/")
        if "\\" in value or value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("repository dependency path must be a normalized relative path")
        return value


def canonical_package_inventory_sha256(artifacts: list[DotnetPackageArtifactV1]) -> str:
    """Hash the complete sorted package/version identity inventory."""

    payload = json.dumps(
        [artifact.model_dump(mode="json") for artifact in artifacts],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class DotnetDependencyAcquisitionV1(BaseModel):
    """Reproducible record of hardened NuGet acquisition for offline use."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(min_length=7)
    snapshot_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_manifest_path: str = Field(min_length=1)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_framework: str = Field(pattern=r"^net(?:8|9|10)\.0$")
    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    image: ContainerImageIdentityV1
    package_source: Literal["https://api.nuget.org/v3/index.json"] = NUGET_ORG_V3_SOURCE
    network_mode: Literal["bridge"] = "bridge"
    container_user: Literal["65534:65534"] = "65534:65534"
    read_only_rootfs: Literal[True] = True
    cap_drop_all: Literal[True] = True
    no_new_privileges: Literal[True] = True
    environment_names: list[str]
    command: list[str] = Field(min_length=1)
    project_transformations: list[str] = Field(default_factory=list)
    repository_artifacts: list[DotnetRepositoryArtifactV1] = Field(default_factory=list)
    artifacts: list[DotnetPackageArtifactV1]
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acquired_at: str
    cleanup_complete: Literal[True] = True

    @model_validator(mode="after")
    def inventory_is_complete(self) -> DotnetDependencyAcquisitionV1:
        ordered = sorted(self.artifacts, key=lambda item: item.relative_path.casefold())
        if self.artifacts != ordered:
            raise ValueError("NuGet package artifacts must be deterministically ordered")
        if len({item.relative_path.casefold() for item in self.artifacts}) != len(self.artifacts):
            raise ValueError("NuGet package artifact paths must be unique")
        if self.inventory_sha256 != canonical_package_inventory_sha256(self.artifacts):
            raise ValueError("NuGet package inventory hash does not match its artifacts")
        repository_ordered = sorted(
            self.repository_artifacts, key=lambda item: item.relative_path.casefold()
        )
        if self.repository_artifacts != repository_ordered:
            raise ValueError("repository dependency artifacts must be deterministically ordered")
        if len({item.relative_path.casefold() for item in self.repository_artifacts}) != len(
            self.repository_artifacts
        ):
            raise ValueError("repository dependency artifact paths must be unique")
        return self
