"""Typed provenance for isolated Python distribution-metadata generation."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PYTHON_VERSION_RE = re.compile(r"^\d+\.\d+$")


class PythonDistributionMetadataPayloadV1(BaseModel):
    """Driver-owned projection of exactly one generated PKG-INFO file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    status: Literal["ok"] = "ok"
    pkg_info_path: str = Field(min_length=1)
    pkg_info_sha256: str
    requires_python: str | None = None
    python_classifier_versions: list[str] = Field(default_factory=list)

    @field_validator("pkg_info_sha256")
    @classmethod
    def pkg_info_hash_must_be_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("PKG-INFO hash must be lowercase SHA-256")
        return value

    @field_validator("pkg_info_path")
    @classmethod
    def pkg_info_path_must_be_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or path.name != "PKG-INFO":
            raise ValueError("PKG-INFO path must be one safe generated relative path")
        return value

    @field_validator("python_classifier_versions")
    @classmethod
    def versions_must_be_exact_and_stable(cls, value: list[str]) -> list[str]:
        if any(not _PYTHON_VERSION_RE.fullmatch(version) for version in value):
            raise ValueError("Python classifier versions must be exact X.Y values")
        expected = sorted(set(value), key=lambda version: tuple(map(int, version.split("."))))
        if value != expected:
            raise ValueError("Python classifier versions must be sorted and unique")
        return value


class PythonDistributionMetadataProofV1(BaseModel):
    """Bind generated metadata to one snapshot, root, image, and execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    snapshot_inventory_sha256: str
    package_root_path: str
    manifest_path: str
    manifest_sha256: str
    driver_sha256: str
    execution: IsolatedExecutionResultV1
    metadata: PythonDistributionMetadataPayloadV1 | None = None
    truth_eligible: bool
    failure_reason: str | None = None

    @model_validator(mode="after")
    def accepted_proof_requires_exact_isolated_success(self) -> PythonDistributionMetadataProofV1:
        for name, value in (
            ("snapshot_inventory_sha256", self.snapshot_inventory_sha256),
            ("manifest_sha256", self.manifest_sha256),
            ("driver_sha256", self.driver_sha256),
        ):
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be lowercase SHA-256")
        exact_execution = (
            self.execution.truth_eligible
            and self.execution.return_code == 0
            and not self.execution.timed_out
            and not self.execution.oom_killed
            and self.execution.cleanup.complete
            and self.execution.org_repo == self.org_repo
            and self.execution.source_revision == self.source_revision
        )
        if self.truth_eligible and (not exact_execution or self.metadata is None):
            raise ValueError("truth-eligible metadata lacks exact isolated success")
        if self.truth_eligible and self.failure_reason is not None:
            raise ValueError("truth-eligible metadata cannot retain a failure reason")
        if not self.truth_eligible and not self.failure_reason:
            raise ValueError("ineligible metadata requires one failure reason")
        return self
