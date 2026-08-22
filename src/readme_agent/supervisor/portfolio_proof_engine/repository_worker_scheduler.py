"""Schedule repository workers with bounded repository and resource concurrency."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor

from readme_agent.supervisor.portfolio_proof_engine.repository_worker_contracts import (
    DEFAULT_GRACE_PERIOD_SECONDS,
    DEFAULT_MAX_CAPTURE_BYTES,
    DEFAULT_PROVIDER_CONCURRENCY,
    DEFAULT_REPOSITORY_CONCURRENCY,
    PROVIDER_RESOURCE_CLASS,
    BatchReportV1,
    RepositoryJobSpecV1,
    WorkerResultV1,
    canonical_sha256,
    utc_now_iso,
)
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_execution import run_child
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_resources import (
    _ConcurrencyGate,
)


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

            return run_child(
                job,
                max_capture_bytes=self.max_capture_bytes,
                grace_period_seconds=self.grace_period_seconds,
                provider_requested=provider_requested,
                provider_acquired=provider_acquired,
                provider_wait_seconds=provider_wait_seconds,
                resource_wait_seconds=resource_wait_seconds,
            )
        finally:
            for _, gate in reversed(acquired_gates):
                gate.release()
