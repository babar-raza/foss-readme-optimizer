"""Typed contracts for truth-eligible disposable container execution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_IMMUTABLE_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
_SECRET_NAME_RE = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|ACCESS_KEY|AUTH|"
    r"CREDENTIAL|COOKIE|SESSION)",
    re.IGNORECASE,
)
_ALLOWED_ENVIRONMENT_NAMES = {
    "CARGO_HOME",
    "CARGO_TERM_COLOR",
    "CI",
    "DOTNET_CLI_HOME",
    "DOTNET_CLI_TELEMETRY_OPTOUT",
    "DOTNET_NOLOGO",
    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE",
    "GOCACHE",
    "GOMODCACHE",
    "GOPATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "NPM_CONFIG_CACHE",
    "NUGET_PACKAGES",
    "PIP_CACHE_DIR",
    "RUSTUP_HOME",
    "TMPDIR",
    "TZ",
}


class IsolatedExecutionPolicyV1(BaseModel):
    """Fail-closed resource and privilege policy for one container."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    immutable_image: str
    cpu_limit: float = Field(default=1.0, gt=0, le=4)
    memory_mebibytes: int = Field(default=512, ge=64, le=4096)
    pids_limit: int = Field(default=64, ge=8, le=512)
    timeout_seconds: float = Field(default=300, gt=0, le=900)
    tmpfs_mebibytes: int = Field(default=64, ge=8, le=1024)
    network_mode: Literal["none"] = "none"
    read_only_rootfs: Literal[True] = True
    cap_drop_all: Literal[True] = True
    no_new_privileges: Literal[True] = True
    seccomp_profile: Literal["runtime-default"] = "runtime-default"
    user: str = "65534:65534"
    workspace_path: Literal["/workspace"] = "/workspace"

    @field_validator("immutable_image")
    @classmethod
    def immutable_image_must_use_digest(cls, value: str) -> str:
        if not _IMMUTABLE_IMAGE_RE.fullmatch(value):
            raise ValueError("container image must be pinned as repository@sha256:<64 hex>")
        return value

    @field_validator("user")
    @classmethod
    def user_must_be_numeric_and_non_root(cls, value: str) -> str:
        match = re.fullmatch(r"(\d+):(\d+)", value)
        if match is None or "0" in match.groups():
            raise ValueError("container user must be a numeric non-root uid:gid")
        return value


class IsolatedExecutionRequestV1(BaseModel):
    """One immutable source tree and argv to execute under a hardened policy."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    source_root: Path
    argv: list[str]
    environment: dict[str, str] = Field(default_factory=dict)
    policy: IsolatedExecutionPolicyV1

    @field_validator("argv")
    @classmethod
    def argv_must_be_direct_and_nonempty(cls, value: list[str]) -> list[str]:
        if not value or not value[0] or any("\0" in item for item in value):
            raise ValueError("isolated argv must identify a direct executable without NUL bytes")
        return value

    @field_validator("environment")
    @classmethod
    def environment_must_not_contain_credentials(cls, value: dict[str, str]) -> dict[str, str]:
        prohibited = sorted(name for name in value if _SECRET_NAME_RE.search(name))
        if prohibited:
            raise ValueError(
                "isolated environment contains credential-like names: " + ", ".join(prohibited)
            )
        unsupported = sorted(set(value) - _ALLOWED_ENVIRONMENT_NAMES)
        if unsupported:
            raise ValueError(
                "isolated environment contains non-allowlisted names: " + ", ".join(unsupported)
            )
        return value


class ContainerImageIdentityV1(BaseModel):
    """Immutable image and engine identity observed immediately before execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_reference: str
    repo_digest: str
    image_id: str
    operating_system: str
    architecture: str
    engine_version: str


class ContainerCleanupV1(BaseModel):
    """Postcondition proving both disposable resources were removed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_container_removed: bool
    seed_container_removed: bool
    workspace_volume_removed: bool

    @property
    def complete(self) -> bool:
        return (
            self.execution_container_removed
            and self.seed_container_removed
            and self.workspace_volume_removed
        )


class IsolatedExecutionResultV1(BaseModel):
    """Redacted outcome and reproducible provenance for one isolated command."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    isolation_kind: Literal["docker_container"] = "docker_container"
    truth_eligible: bool
    org_repo: str
    source_revision: str
    argv: list[str]
    environment_names: list[str]
    input_sha256: str
    input_file_count: int = Field(ge=0)
    policy_sha256: str
    policy: IsolatedExecutionPolicyV1
    image: ContainerImageIdentityV1
    container_id: str
    process_inventory: list[str]
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool
    oom_killed: bool
    started_at: str
    finished_at: str
    cleanup: ContainerCleanupV1

    @model_validator(mode="after")
    def truth_eligibility_requires_complete_isolation(self) -> IsolatedExecutionResultV1:
        if self.truth_eligible and (
            not self.cleanup.complete
            or self.image.requested_reference != self.policy.immutable_image
            or self.image.repo_digest != self.policy.immutable_image
            or not self.image.image_id.startswith("sha256:")
        ):
            raise ValueError("truth-eligible execution lacks immutable-image or cleanup proof")
        return self
