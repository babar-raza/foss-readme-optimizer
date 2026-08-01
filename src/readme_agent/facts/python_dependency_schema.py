"""Typed provenance for an offline Python dependency wheelhouse."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.facts.isolated_execution_schema import ContainerImageIdentityV1


class PythonWheelArtifactV1(BaseModel):
    """One exact binary wheel admitted to the offline consumer environment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(pattern=r"^[^/\\]+\.whl$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class PythonDependencyAcquisitionV1(BaseModel):
    """Reproducible record of isolated resolution and binary-only acquisition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    snapshot_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image: ContainerImageIdentityV1
    network_mode: Literal["bridge"] = "bridge"
    environment_names: list[str]
    requirements: list[str]
    command: list[str]
    artifacts: list[PythonWheelArtifactV1]
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acquired_at: str
    cleanup_complete: bool

    @model_validator(mode="after")
    def dependencies_require_wheels_and_cleanup(self) -> PythonDependencyAcquisitionV1:
        if self.requirements and not self.artifacts:
            raise ValueError("Python runtime dependencies require a nonempty wheelhouse")
        if not self.cleanup_complete:
            raise ValueError("Python dependency acquisition cleanup is incomplete")
        return self
