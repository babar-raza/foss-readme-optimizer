"""Typed contracts for process-isolated repository workers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_REPOSITORY_CONCURRENCY = 2
DEFAULT_PROVIDER_CONCURRENCY = 2
DEFAULT_MAX_CAPTURE_BYTES = 65536
DEFAULT_GRACE_PERIOD_SECONDS = 10.0
PROVIDER_RESOURCE_CLASS = "provider"

_SECRET_LIKE_NAME_RE = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|CREDENTIAL)", re.IGNORECASE
)
_ORG_REPO_RE = re.compile(r"^[^/]+/[^/]+$")


def canonical_sha256(value: object) -> str:
    """Stable content hash: sorted-key, separator-compact JSON -> sha256 hex digest."""

    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResourceRequirementV1(_StrictFrozenModel):
    """Named shared-resource classes this job must hold a slot in before it may start."""

    schema_version: Literal[1] = 1
    resource_classes: tuple[str, ...] = ()


class RepositoryJobSpecV1(_StrictFrozenModel):
    """One coordinator-decided repository job. Fully self-describing: no implicit mission-state
    access -- everything the child process needs (argv, cwd, environment, deadline) is an explicit
    field, not derived by this module from any registry/state file."""

    schema_version: Literal[1] = 1
    job_id: str = Field(min_length=1)
    input_ordinal: int = Field(ge=0)
    org_repo: str
    source_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,64}$")
    action: str = Field(min_length=1)
    argv: tuple[str, ...] = Field(min_length=1)
    command_cwd: Path | None = None
    work_dir: Path
    output_dir: Path
    evidence_dir: Path
    environment: dict[str, str] = Field(default_factory=dict)
    deadline_seconds: float | None = Field(default=None, gt=0)
    resource: ResourceRequirementV1 = Field(default_factory=ResourceRequirementV1)
    expected_receipt_path: Path | None = None

    @field_validator("org_repo")
    @classmethod
    def _check_org_repo(cls, value: str) -> str:
        if not _ORG_REPO_RE.match(value):
            raise ValueError("org_repo must look like 'org/repo'")
        return value

    @field_validator("argv")
    @classmethod
    def _check_argv(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not part for part in value):
            raise ValueError("argv entries must be non-empty")
        return value

    def contract_hash(self) -> str:
        return canonical_sha256(self.model_dump(mode="json"))

    def writable_roots(self) -> tuple[Path, Path, Path]:
        return (self.work_dir, self.output_dir, self.evidence_dir)


class CancellationOutcomeV1(_StrictFrozenModel):
    schema_version: Literal[1] = 1
    requested: bool = False
    reason: Literal["NONE", "JOB_DEADLINE_EXCEEDED"] = "NONE"
    graceful_signal_sent_at: str | None = None
    forced_kill_sent_at: str | None = None
    process_confirmed_terminated: bool = False


WorkerExitClassificationV1 = Literal[
    "SUCCEEDED",
    "CHILD_NONZERO_EXIT",
    "MISSING_EXPECTED_RECEIPT",
    "TIMED_OUT",
    "SPAWN_FAILED",
    "REJECTED_DUPLICATE",
    "NOT_STARTED_DEADLINE_EXPIRED",
]


class WorkerResultV1(_StrictFrozenModel):
    schema_version: Literal[1] = 1
    job_id: str
    input_ordinal: int
    org_repo: str
    contract_hash: str
    exit_classification: WorkerExitClassificationV1
    succeeded: bool
    return_code: int | None = None
    started_at: str | None = None
    ended_at: str | None = None
    duration_seconds: float = Field(ge=0.0)
    provider_slot_requested: bool = False
    provider_slot_acquired: bool = False
    provider_wait_seconds: float = Field(default=0.0, ge=0.0)
    resource_wait_seconds: dict[str, float] = Field(default_factory=dict)
    output_dir: str
    evidence_dir: str
    expected_receipt_path: str | None = None
    receipt_observed: bool = False
    stdout_excerpt: str = ""
    stdout_sha256: str = ""
    stdout_byte_count: int = Field(default=0, ge=0)
    stderr_excerpt: str = ""
    stderr_sha256: str = ""
    stderr_byte_count: int = Field(default=0, ge=0)
    environment_names: tuple[str, ...] = ()
    cancellation: CancellationOutcomeV1 = Field(default_factory=CancellationOutcomeV1)
    failure_reason: str | None = None


class BatchReportV1(_StrictFrozenModel):
    """Deterministic batch report: `results` is always in input order, never completion order."""

    schema_version: Literal[1] = 1
    batch_contract_hash: str
    repository_concurrency_limit: int = Field(ge=1)
    provider_concurrency_limit: int = Field(ge=1)
    observed_max_repository_concurrency: int = Field(ge=0)
    observed_max_provider_concurrency: int = Field(ge=0)
    observed_max_resource_concurrency: dict[str, int] = Field(default_factory=dict)
    batch_deadline_seconds: float | None = None
    batch_deadline_expired: bool = False
    results: tuple[WorkerResultV1, ...] = ()
    rejected_duplicate_job_ids: tuple[str, ...] = ()
    rejected_duplicate_output_roots: tuple[str, ...] = ()
    started_at: str
    ended_at: str
    total_duration_seconds: float = Field(ge=0.0)
