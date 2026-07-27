"""Typed provenance for networked Rust dependency acquisition."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.isolated_execution_schema import ContainerImageIdentityV1


class RustDependencyAcquisitionV1(BaseModel):
    """Exact Cargo lock/vendor bundle acquired without executing repository code."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    snapshot_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    image: ContainerImageIdentityV1
    network_mode: Literal["bridge"] = "bridge"
    environment_names: list[str]
    commands: list[list[str]]
    lockfile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vendor_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lock_package_count: int = Field(ge=1)
    acquired_at: str
    cleanup_complete: Literal[True] = True
