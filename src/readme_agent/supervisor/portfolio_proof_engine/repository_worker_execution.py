"""Execute one repository-worker subprocess and classify its terminal result."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from readme_agent.evidence.writer import win_long_path
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_contracts import (
    _SECRET_LIKE_NAME_RE,
    CancellationOutcomeV1,
    RepositoryJobSpecV1,
    WorkerExitClassificationV1,
    WorkerResultV1,
    utc_now_iso,
)
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_process import (
    _EMPTY_DRAIN,
    _DrainResult,
    _send_forced_kill,
    _send_graceful_signal,
    _spawn_kwargs,
    _start_drain_thread,
)


def _receipt_exists(path: Path) -> bool:
    """`Path.is_file()`, but long-path-safe on Windows.

    The real, confirmed root cause of `ACL-ORCH-RECEIPT-VISIBILITY-LAG` (found after two rounds
    of an incorrect timing-based fix -- see the retry loop below and its git history): Win32
    rejects any path at or beyond 260 characters unless it carries the `\\\\?\\` long-path prefix
    (`evidence/writer.py::win_long_path`, the exact mechanism CORE-041 already fixed for the
    *write* side of this same evidence tree). `write_redacted_json()` already writes the receipt
    through that long-path-safe form, so the child's write always succeeds -- but this read-side
    check used a bare `Path.is_file()`, which silently returns `False` for a file that genuinely
    exists the moment its full path reaches that boundary. Confirmed by direct measurement: every
    `receipt_rejected` case in a live 34-repository portfolio pass had a full receipt path of
    260-263 characters; every clean success was 257-259. The failure tracked path *length*
    (`registry_revision_id` + `org_repo` + the worker-invocation UUID, none of it deterministically
    short), not timing, load, or antivirus/cloud-sync interference as two earlier attempts at this
    fix incorrectly assumed.
    """

    target = win_long_path(path) if os.name == "nt" else str(path)
    return os.path.isfile(target)


def _wait_for_receipt_visibility(
    path: Path, *, attempts: int = 3, initial_delay_seconds: float = 0.05
) -> bool:
    """Check receipt existence in a long-path-safe way, with a small residual retry.

    The long-path fix in `_receipt_exists()` above is the real correctness fix and should be
    deterministic on its own -- this thin retry wrapper is kept only as insurance against a
    genuine (much rarer, never actually isolated) filesystem-visibility race independent of path
    length, at a small, bounded cost (~0.15s worst case: 0.05+0.1s) rather than the much larger
    ~1.55s/~7.5s bounds two earlier, incorrect diagnoses of this bug used trying to wait out a
    "lag" that a length-260+ path was never going to resolve no matter how long the wait.
    """

    delay = initial_delay_seconds
    for attempt in range(attempts):
        if _receipt_exists(path):
            return True
        if attempt + 1 < attempts:
            time.sleep(delay)
            delay = min(delay * 2, 1.0)
    return _receipt_exists(path)


def run_child(
    job: RepositoryJobSpecV1,
    *,
    max_capture_bytes: int,
    grace_period_seconds: float,
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
            list(job.argv),
            **_spawn_kwargs(job.environment, job.command_cwd or job.work_dir),
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
    stdout_thread = _start_drain_thread(process.stdout, max_capture_bytes, stdout_holder)
    stderr_thread = _start_drain_thread(process.stderr, max_capture_bytes, stderr_holder)

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
            process.wait(timeout=grace_period_seconds)
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
    receipt_observed = job.expected_receipt_path is not None and _wait_for_receipt_visibility(
        job.expected_receipt_path
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
