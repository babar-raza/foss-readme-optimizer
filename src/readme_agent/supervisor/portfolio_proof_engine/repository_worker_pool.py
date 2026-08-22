"""Process-isolated repository worker pool: a subordinate executor, not a controller.

Runs an already-decided, ordered list of repository jobs concurrently via subprocess isolation
(never threads for the actual repository work -- `os.environ`, the persistent baseline/work clones,
and the LLM call-ledger are all safe today only under a fresh-process-per-run assumption already
baked into their own code), bounded by repository- and named-resource-concurrency limits. This
module never decides which repository is eligible, which stage/action comes next, whether a repair
is warranted, or whether a goal is complete -- those decisions remain with the authoritative state
machine. It has zero imports from any other `readme_agent` module (stdlib + pydantic only) so that
boundary is provable by inspection: see
`test_repository_worker_pool_imports_no_mission_state_apis`.

Resource gating is a named, caller-defined set of classes (`ResourceRequirementV1.resource_classes`)
rather than a single hardcoded "provider" boolean: real repository processing also touches shared,
non-per-repository state this module has no visibility into (a durable git-backed state store, a
JDK toolchain cache, a registry self-heal marker) and callers may need to serialize access to those
too, without another revision of this module. `"provider"` is the one class name this pool always
recognizes via its own dedicated constructor knob (`provider_concurrency`, default 2, matching the
required default); any other class name is gated only if the caller supplies a limit for it via
`extra_resource_limits`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Literal

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


class _ConcurrencyGate:
    """Bounded semaphore with an observed high-water mark. One instance per resource class."""

    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        self.limit = limit
        self._semaphore = threading.Semaphore(limit)
        self._lock = threading.Lock()
        self._active = 0
        self.observed_max = 0

    def reset_observed_max(self) -> None:
        with self._lock:
            self.observed_max = 0

    def acquire(self) -> float:
        """Blocks until a slot is free; returns the time spent waiting, in seconds."""

        started = time.monotonic()
        self._semaphore.acquire()
        waited = time.monotonic() - started
        with self._lock:
            self._active += 1
            self.observed_max = max(self.observed_max, self._active)
        return waited

    def release(self) -> None:
        with self._lock:
            self._active -= 1
        self._semaphore.release()


class _DrainResult:
    __slots__ = ("excerpt", "sha256", "byte_count")

    def __init__(self, excerpt: str, sha256: str, byte_count: int) -> None:
        self.excerpt = excerpt
        self.sha256 = sha256
        self.byte_count = byte_count


def _drain_pipe(pipe: IO[bytes] | None, max_bytes: int) -> _DrainResult:
    """Read a child pipe to EOF, keeping a bounded excerpt but hashing the full stream."""

    hasher = hashlib.sha256()
    buffer = bytearray()
    byte_count = 0
    if pipe is not None:
        while True:
            chunk = pipe.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
            byte_count += len(chunk)
            if len(buffer) < max_bytes:
                buffer.extend(chunk[: max_bytes - len(buffer)])
    excerpt = bytes(buffer).decode("utf-8", errors="replace")
    return _DrainResult(excerpt=excerpt, sha256=hasher.hexdigest(), byte_count=byte_count)


def _start_drain_thread(
    pipe: IO[bytes] | None, max_bytes: int, result_holder: list[_DrainResult]
) -> threading.Thread:
    def _run() -> None:
        result_holder.append(_drain_pipe(pipe, max_bytes))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def _is_windows() -> bool:
    return os.name == "nt"


def _spawn_kwargs(environment: dict[str, str], cwd: Path) -> dict:
    # Deliberately a bare, untyped `dict` (not `dict[str, object]`): mypy resolves
    # platform-specific stubs (POSIX vs. Windows) from the machine it runs on, so exactly one of
    # `creationflags`/`start_new_session` is unknown on any given platform. An `Any`-valued dict
    # unpacked into `Popen(**kwargs)` keeps overload resolution permissive on both; a precisely
    # typed dict makes the overload match fail on whichever platform didn't type-check this file.
    kwargs: dict = {
        "cwd": str(cwd),
        "env": environment,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if _is_windows():
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    return kwargs


def _send_graceful_signal(process: subprocess.Popen[bytes]) -> None:
    if _is_windows():
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        except (OSError, ValueError):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)  # type: ignore[attr-defined]
        except ProcessLookupError:
            pass


def _send_forced_kill(process: subprocess.Popen[bytes]) -> None:
    if _is_windows():
        killer = subprocess.Popen(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            killer.wait(timeout=5)
        except subprocess.TimeoutExpired:
            killer.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


_EMPTY_DRAIN = _DrainResult("", hashlib.sha256(b"").hexdigest(), 0)


class RepositoryWorkerPool:
    """Subordinate, process-isolated executor. Never decides eligibility, stage, or completion --
    only runs the jobs it is given and reports what happened."""

    def __init__(
        self,
        *,
        repository_concurrency: int = DEFAULT_REPOSITORY_CONCURRENCY,
        provider_concurrency: int = DEFAULT_PROVIDER_CONCURRENCY,
        extra_resource_limits: Mapping[str, int] | None = None,
        max_capture_bytes: int = DEFAULT_MAX_CAPTURE_BYTES,
        grace_period_seconds: float = DEFAULT_GRACE_PERIOD_SECONDS,
    ) -> None:
        if repository_concurrency < 1:
            raise ValueError("repository_concurrency must be at least 1")
        if provider_concurrency < 1:
            raise ValueError("provider_concurrency must be at least 1")
        for name, limit in (extra_resource_limits or {}).items():
            if limit < 1:
                raise ValueError(f"resource limit for {name!r} must be at least 1")

        self.repository_concurrency = repository_concurrency
        self.provider_concurrency = provider_concurrency
        self.max_capture_bytes = max_capture_bytes
        self.grace_period_seconds = grace_period_seconds

        self._repository_gate = _ConcurrencyGate(repository_concurrency)
        resource_limits: dict[str, int] = {
            PROVIDER_RESOURCE_CLASS: provider_concurrency,
            **(dict(extra_resource_limits) if extra_resource_limits else {}),
        }
        self._resource_gates: dict[str, _ConcurrencyGate] = {
            name: _ConcurrencyGate(limit) for name, limit in resource_limits.items()
        }

    def run(
        self,
        jobs: Sequence[RepositoryJobSpecV1],
        *,
        batch_deadline_seconds: float | None = None,
    ) -> BatchReportV1:
        started_wall = utc_now_iso()
        started_monotonic = time.monotonic()
        job_list = list(jobs)
        batch_hash = canonical_sha256([job.contract_hash() for job in job_list])

        self._repository_gate.reset_observed_max()
        for gate in self._resource_gates.values():
            gate.reset_observed_max()

        duplicate_job_ids, duplicate_roots = self._find_duplicates(job_list)
        if duplicate_job_ids or duplicate_roots:
            results = tuple(self._rejected_result(job) for job in job_list)
            ended_wall = utc_now_iso()
            return BatchReportV1(
                batch_contract_hash=batch_hash,
                repository_concurrency_limit=self.repository_concurrency,
                provider_concurrency_limit=self.provider_concurrency,
                observed_max_repository_concurrency=0,
                observed_max_provider_concurrency=0,
                observed_max_resource_concurrency={},
                batch_deadline_seconds=batch_deadline_seconds,
                batch_deadline_expired=False,
                results=results,
                rejected_duplicate_job_ids=tuple(sorted(duplicate_job_ids)),
                rejected_duplicate_output_roots=tuple(sorted(duplicate_roots)),
                started_at=started_wall,
                ended_at=ended_wall,
                total_duration_seconds=time.monotonic() - started_monotonic,
            )

        batch_deadline_at = (
            started_monotonic + batch_deadline_seconds
            if batch_deadline_seconds is not None
            else None
        )

        # The authoritative "don't start new work" check happens inside `_execute_one`, right
        # after this job actually acquires a repository-concurrency slot -- that is the true
        # moment a job "starts," not the moment it is handed to the thread pool. A limited-
        # concurrency pool queues submissions instantly regardless of how long earlier jobs take,
        # so a submission-time-only check would let already-queued jobs run long after the
        # deadline passed. This pre-check is a cheap fast path only (skip the queue entirely for
        # jobs that are already unambiguously too late), never the sole enforcement point.
        entries: list[WorkerResultV1 | Future[WorkerResultV1]] = []
        with ThreadPoolExecutor(max_workers=self.repository_concurrency) as executor:
            for job in job_list:
                if batch_deadline_at is not None and time.monotonic() >= batch_deadline_at:
                    entries.append(self._not_started_result(job))
                    continue
                entries.append(executor.submit(self._execute_one, job, batch_deadline_at))

            results = tuple(
                entry if isinstance(entry, WorkerResultV1) else entry.result() for entry in entries
            )

        deadline_expired_for_batch = (
            batch_deadline_at is not None and time.monotonic() >= batch_deadline_at
        )
        ended_wall = utc_now_iso()
        return BatchReportV1(
            batch_contract_hash=batch_hash,
            repository_concurrency_limit=self.repository_concurrency,
            provider_concurrency_limit=self.provider_concurrency,
            observed_max_repository_concurrency=self._repository_gate.observed_max,
            observed_max_provider_concurrency=(
                self._resource_gates[PROVIDER_RESOURCE_CLASS].observed_max
            ),
            observed_max_resource_concurrency={
                name: gate.observed_max for name, gate in self._resource_gates.items()
            },
            batch_deadline_seconds=batch_deadline_seconds,
            batch_deadline_expired=deadline_expired_for_batch,
            results=results,
            rejected_duplicate_job_ids=(),
            rejected_duplicate_output_roots=(),
            started_at=started_wall,
            ended_at=ended_wall,
            total_duration_seconds=time.monotonic() - started_monotonic,
        )

    def _find_duplicates(self, jobs: list[RepositoryJobSpecV1]) -> tuple[set[str], set[str]]:
        id_counts: dict[str, int] = {}
        for job in jobs:
            id_counts[job.job_id] = id_counts.get(job.job_id, 0) + 1
        duplicate_job_ids = {job_id for job_id, count in id_counts.items() if count > 1}

        path_owners: dict[str, set[str]] = {}
        for job in jobs:
            for path in job.writable_roots():
                key = str(path.resolve())
                path_owners.setdefault(key, set()).add(job.job_id)

        duplicate_roots = {path for path, owners in path_owners.items() if len(owners) > 1}
        for owners in path_owners.values():
            if len(owners) > 1:
                duplicate_job_ids.update(owners)

        return duplicate_job_ids, duplicate_roots

    def _rejected_result(self, job: RepositoryJobSpecV1) -> WorkerResultV1:
        now = utc_now_iso()
        return WorkerResultV1(
            job_id=job.job_id,
            input_ordinal=job.input_ordinal,
            org_repo=job.org_repo,
            contract_hash=job.contract_hash(),
            exit_classification="REJECTED_DUPLICATE",
            succeeded=False,
            return_code=None,
            started_at=None,
            ended_at=now,
            duration_seconds=0.0,
            output_dir=str(job.output_dir),
            evidence_dir=str(job.evidence_dir),
            expected_receipt_path=(
                str(job.expected_receipt_path) if job.expected_receipt_path else None
            ),
            receipt_observed=False,
            failure_reason="duplicate job_id, or a work/output/evidence directory overlapping "
            "another job in this batch",
        )

    def _not_started_result(self, job: RepositoryJobSpecV1) -> WorkerResultV1:
        now = utc_now_iso()
        return WorkerResultV1(
            job_id=job.job_id,
            input_ordinal=job.input_ordinal,
            org_repo=job.org_repo,
            contract_hash=job.contract_hash(),
            exit_classification="NOT_STARTED_DEADLINE_EXPIRED",
            succeeded=False,
            return_code=None,
            started_at=None,
            ended_at=now,
            duration_seconds=0.0,
            output_dir=str(job.output_dir),
            evidence_dir=str(job.evidence_dir),
            expected_receipt_path=(
                str(job.expected_receipt_path) if job.expected_receipt_path else None
            ),
            receipt_observed=False,
            failure_reason="batch deadline expired before this job could be started",
        )

    def _execute_one(
        self, job: RepositoryJobSpecV1, batch_deadline_at: float | None
    ) -> WorkerResultV1:
        self._repository_gate.acquire()
        try:
            # Re-check here, not just at submission time: with limited repository concurrency a
            # job can sit queued behind an earlier one for a long time after being submitted, and
            # this is the actual moment it would start.
            if batch_deadline_at is not None and time.monotonic() >= batch_deadline_at:
                return self._not_started_result(job)
            return self._execute_with_resources(job)
        finally:
            self._repository_gate.release()

    def _execute_with_resources(self, job: RepositoryJobSpecV1) -> WorkerResultV1:
        resource_classes = sorted(set(job.resource.resource_classes))
        acquired_gates: list[tuple[str, _ConcurrencyGate]] = []
        resource_wait_seconds: dict[str, float] = {}
        try:
            for name in resource_classes:
                gate = self._resource_gates.get(name)
                if gate is None:
                    continue
                resource_wait_seconds[name] = gate.acquire()
                acquired_gates.append((name, gate))

            provider_requested = PROVIDER_RESOURCE_CLASS in resource_classes
            provider_acquired = any(name == PROVIDER_RESOURCE_CLASS for name, _ in acquired_gates)
            provider_wait_seconds = resource_wait_seconds.get(PROVIDER_RESOURCE_CLASS, 0.0)

            return self._run_child(
                job,
                provider_requested=provider_requested,
                provider_acquired=provider_acquired,
                provider_wait_seconds=provider_wait_seconds,
                resource_wait_seconds=resource_wait_seconds,
            )
        finally:
            for _, gate in reversed(acquired_gates):
                gate.release()

    def _run_child(
        self,
        job: RepositoryJobSpecV1,
        *,
        provider_requested: bool,
        provider_acquired: bool,
        provider_wait_seconds: float,
        resource_wait_seconds: dict[str, float],
    ) -> WorkerResultV1:
        job.work_dir.mkdir(parents=True, exist_ok=True)
        job.output_dir.mkdir(parents=True, exist_ok=True)
        job.evidence_dir.mkdir(parents=True, exist_ok=True)

        environment_names = tuple(
            sorted(name for name in job.environment if not _SECRET_LIKE_NAME_RE.search(name))
        )
        expected_receipt_path_str = (
            str(job.expected_receipt_path) if job.expected_receipt_path else None
        )

        start_monotonic = time.monotonic()
        started_at = utc_now_iso()

        try:
            process = subprocess.Popen(
                list(job.argv), **_spawn_kwargs(job.environment, job.work_dir)
            )
        except OSError as exc:
            return WorkerResultV1(
                job_id=job.job_id,
                input_ordinal=job.input_ordinal,
                org_repo=job.org_repo,
                contract_hash=job.contract_hash(),
                exit_classification="SPAWN_FAILED",
                succeeded=False,
                return_code=None,
                started_at=started_at,
                ended_at=utc_now_iso(),
                duration_seconds=time.monotonic() - start_monotonic,
                provider_slot_requested=provider_requested,
                provider_slot_acquired=provider_acquired,
                provider_wait_seconds=provider_wait_seconds,
                resource_wait_seconds=resource_wait_seconds,
                output_dir=str(job.output_dir),
                evidence_dir=str(job.evidence_dir),
                expected_receipt_path=expected_receipt_path_str,
                receipt_observed=False,
                environment_names=environment_names,
                failure_reason=str(exc),
            )

        stdout_holder: list[_DrainResult] = []
        stderr_holder: list[_DrainResult] = []
        stdout_thread = _start_drain_thread(process.stdout, self.max_capture_bytes, stdout_holder)
        stderr_thread = _start_drain_thread(process.stderr, self.max_capture_bytes, stderr_holder)

        cancellation = CancellationOutcomeV1()
        timed_out = False
        try:
            process.wait(timeout=job.deadline_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            graceful_sent_at = utc_now_iso()
            _send_graceful_signal(process)
            forced_sent_at: str | None = None
            try:
                process.wait(timeout=self.grace_period_seconds)
            except subprocess.TimeoutExpired:
                forced_sent_at = utc_now_iso()
                _send_forced_kill(process)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            cancellation = CancellationOutcomeV1(
                requested=True,
                reason="JOB_DEADLINE_EXCEEDED",
                graceful_signal_sent_at=graceful_sent_at,
                forced_kill_sent_at=forced_sent_at,
                process_confirmed_terminated=process.poll() is not None,
            )

        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        stdout_drain = stdout_holder[0] if stdout_holder else _EMPTY_DRAIN
        stderr_drain = stderr_holder[0] if stderr_holder else _EMPTY_DRAIN
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

        return_code = process.poll()
        receipt_observed = (
            job.expected_receipt_path is not None and job.expected_receipt_path.is_file()
        )

        exit_classification: WorkerExitClassificationV1
        if timed_out:
            exit_classification = "TIMED_OUT"
        elif return_code != 0:
            exit_classification = "CHILD_NONZERO_EXIT"
        elif job.expected_receipt_path is not None and not receipt_observed:
            exit_classification = "MISSING_EXPECTED_RECEIPT"
        else:
            exit_classification = "SUCCEEDED"

        return WorkerResultV1(
            job_id=job.job_id,
            input_ordinal=job.input_ordinal,
            org_repo=job.org_repo,
            contract_hash=job.contract_hash(),
            exit_classification=exit_classification,
            succeeded=exit_classification == "SUCCEEDED",
            return_code=return_code,
            started_at=started_at,
            ended_at=utc_now_iso(),
            duration_seconds=time.monotonic() - start_monotonic,
            provider_slot_requested=provider_requested,
            provider_slot_acquired=provider_acquired,
            provider_wait_seconds=provider_wait_seconds,
            resource_wait_seconds=resource_wait_seconds,
            output_dir=str(job.output_dir),
            evidence_dir=str(job.evidence_dir),
            expected_receipt_path=expected_receipt_path_str,
            receipt_observed=receipt_observed,
            stdout_excerpt=stdout_drain.excerpt,
            stdout_sha256=stdout_drain.sha256,
            stdout_byte_count=stdout_drain.byte_count,
            stderr_excerpt=stderr_drain.excerpt,
            stderr_sha256=stderr_drain.sha256,
            stderr_byte_count=stderr_drain.byte_count,
            environment_names=environment_names,
            cancellation=cancellation,
            failure_reason=None,
        )
