from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from readme_agent.supervisor.portfolio_proof_engine.repository_worker_execution import (
    _wait_for_receipt_visibility,
)
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_pool import (
    RepositoryJobSpecV1,
    RepositoryWorkerPool,
    ResourceRequirementV1,
)

FIXTURE_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "repository_worker_pool"
    / "fake_repository_job.py"
)


def _dirs(base: Path, name: str) -> tuple[Path, Path, Path]:
    root = base / name
    return root / "work", root / "output", root / "evidence"


def _job(
    tmp_path: Path,
    job_id: str,
    ordinal: int,
    *,
    work_dir: Path | None = None,
    output_dir: Path | None = None,
    evidence_dir: Path | None = None,
    sleep_seconds: float = 0.0,
    exit_code: int = 0,
    receipt_path: Path | None = None,
    write_receipt: bool = False,
    stdout_bytes: int = 0,
    stderr_bytes: int = 0,
    counter_file: Path | None = None,
    pid_file: Path | None = None,
    print_env: tuple[str, ...] = (),
    deadline_seconds: float | None = None,
    resource_classes: tuple[str, ...] = (),
    environment: dict[str, str] | None = None,
    command_cwd: Path | None = None,
    print_cwd: bool = False,
) -> RepositoryJobSpecV1:
    default_work, default_output, default_evidence = _dirs(tmp_path, job_id)
    resolved_work = work_dir if work_dir is not None else default_work
    resolved_output = output_dir if output_dir is not None else default_output
    resolved_evidence = evidence_dir if evidence_dir is not None else default_evidence

    argv = [
        sys.executable,
        str(FIXTURE_SCRIPT),
        "--sleep-seconds",
        str(sleep_seconds),
        "--exit-code",
        str(exit_code),
    ]
    if write_receipt and receipt_path is not None:
        argv += ["--write-receipt", str(receipt_path)]
    if stdout_bytes:
        argv += ["--stdout-bytes", str(stdout_bytes)]
    if stderr_bytes:
        argv += ["--stderr-bytes", str(stderr_bytes)]
    if counter_file is not None:
        argv += ["--counter-file", str(counter_file)]
    if pid_file is not None:
        argv += ["--pid-file", str(pid_file)]
    for name in print_env:
        argv += ["--print-env", name]
    if print_cwd:
        argv += ["--print-cwd"]

    return RepositoryJobSpecV1(
        job_id=job_id,
        input_ordinal=ordinal,
        org_repo="acme/" + job_id.replace("_", "-"),
        action="test-action",
        argv=tuple(argv),
        command_cwd=command_cwd,
        work_dir=resolved_work,
        output_dir=resolved_output,
        evidence_dir=resolved_evidence,
        environment=environment or {},
        deadline_seconds=deadline_seconds,
        resource=ResourceRequirementV1(resource_classes=resource_classes),
        expected_receipt_path=receipt_path,
    )


def _process_exists(pid: int) -> bool:
    if os.name == "nt":
        output = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        return str(pid) in output
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_constructor_rejects_concurrency_below_one() -> None:
    with pytest.raises(ValueError):
        RepositoryWorkerPool(repository_concurrency=0)
    with pytest.raises(ValueError):
        RepositoryWorkerPool(provider_concurrency=0)
    with pytest.raises(ValueError):
        RepositoryWorkerPool(extra_resource_limits={"x": 0})


def test_default_concurrency_values_match_required_defaults() -> None:
    pool = RepositoryWorkerPool()
    assert pool.repository_concurrency == 2
    assert pool.provider_concurrency == 2


def test_command_cwd_can_differ_from_disjoint_worker_scratch(tmp_path: Path) -> None:
    command_cwd = tmp_path / "repository-root"
    command_cwd.mkdir()
    job = _job(
        tmp_path,
        "cwd_job",
        0,
        command_cwd=command_cwd,
        print_cwd=True,
    )

    result = RepositoryWorkerPool(repository_concurrency=1).run([job]).results[0]

    assert result.succeeded
    assert f"CWD={command_cwd}" in result.stdout_excerpt
    assert command_cwd != job.work_dir


def test_two_independent_jobs_overlap_and_beat_serial_baseline(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    jobs = [
        _job(tmp_path, "job_a", 0, sleep_seconds=0.5),
        _job(tmp_path, "job_b", 1, sleep_seconds=0.5),
    ]
    started = time.monotonic()
    report = pool.run(jobs)
    elapsed = time.monotonic() - started

    assert all(result.succeeded for result in report.results)
    assert elapsed < 0.9, "two 0.5s jobs should overlap, well under the 1.0s serial baseline"


def test_default_repository_concurrency_never_exceeds_two(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    jobs = [_job(tmp_path, f"job_{i}", i, sleep_seconds=0.15) for i in range(5)]
    report = pool.run(jobs)
    assert report.observed_max_repository_concurrency == 2
    assert all(result.succeeded for result in report.results)


def test_explicit_repository_concurrency_of_three_is_reached(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(repository_concurrency=3)
    jobs = [_job(tmp_path, f"job_{i}", i, sleep_seconds=0.15) for i in range(6)]
    report = pool.run(jobs)
    assert report.observed_max_repository_concurrency == 3


def test_provider_tagged_concurrency_never_exceeds_provider_limit(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(repository_concurrency=4, provider_concurrency=2)
    jobs = [
        _job(tmp_path, f"job_{i}", i, sleep_seconds=0.15, resource_classes=("provider",))
        for i in range(4)
    ]
    report = pool.run(jobs)
    assert report.observed_max_provider_concurrency == 2


def test_non_provider_work_proceeds_while_provider_capacity_occupied(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(repository_concurrency=2, provider_concurrency=1)
    provider_job = _job(
        tmp_path, "provider_job", 0, sleep_seconds=0.6, resource_classes=("provider",)
    )
    plain_job = _job(tmp_path, "plain_job", 1, sleep_seconds=0.05)

    report = pool.run([provider_job, plain_job])
    provider_result = next(r for r in report.results if r.job_id == "provider_job")
    plain_result = next(r for r in report.results if r.job_id == "plain_job")

    assert plain_result.succeeded and provider_result.succeeded
    assert datetime.fromisoformat(plain_result.ended_at) < datetime.fromisoformat(
        provider_result.ended_at
    )


def test_results_preserve_input_order_regardless_of_completion_order(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(repository_concurrency=2)
    slow_first = _job(tmp_path, "slow_first", 0, sleep_seconds=0.4)
    fast_second = _job(tmp_path, "fast_second", 1, sleep_seconds=0.05)

    report = pool.run([slow_first, fast_second])

    assert [result.job_id for result in report.results] == ["slow_first", "fast_second"]


def test_disjoint_directories_prevent_file_collisions(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    receipt_a = _dirs(tmp_path, "job_a")[1] / "receipt.json"
    receipt_b = _dirs(tmp_path, "job_b")[1] / "receipt.json"
    jobs = [
        _job(tmp_path, "job_a", 0, receipt_path=receipt_a, write_receipt=True),
        _job(tmp_path, "job_b", 1, receipt_path=receipt_b, write_receipt=True),
    ]

    report = pool.run(jobs)

    assert all(result.succeeded for result in report.results)
    assert receipt_a.is_file()
    assert receipt_b.is_file()


def test_duplicate_output_roots_rejected_before_any_child_starts(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    shared_root = tmp_path / "shared"
    sentinel = shared_root / "sentinel.txt"
    job_a = _job(
        tmp_path,
        "job_a",
        0,
        work_dir=shared_root / "work",
        output_dir=shared_root / "output",
        evidence_dir=shared_root / "evidence",
        counter_file=sentinel,
    )
    job_b = _job(
        tmp_path,
        "job_b",
        1,
        work_dir=shared_root / "work",
        output_dir=shared_root / "output",
        evidence_dir=shared_root / "evidence",
        counter_file=sentinel,
    )

    report = pool.run([job_a, job_b])

    assert set(report.rejected_duplicate_job_ids) == {"job_a", "job_b"}
    assert all(result.exit_classification == "REJECTED_DUPLICATE" for result in report.results)
    assert not sentinel.exists(), "neither adversarial job should ever have actually run"


def test_one_child_failure_does_not_stop_independent_job(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    failing = _job(tmp_path, "failing_job", 0, exit_code=7)
    healthy = _job(tmp_path, "healthy_job", 1)

    report = pool.run([failing, healthy])

    assert report.results[0].exit_classification == "CHILD_NONZERO_EXIT"
    assert report.results[0].return_code == 7
    assert report.results[1].succeeded is True


def test_missing_expected_receipt_becomes_incomplete_not_success(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    receipt_path = _dirs(tmp_path, "no_receipt_job")[1] / "receipt.json"
    job = _job(tmp_path, "no_receipt_job", 0, receipt_path=receipt_path, write_receipt=False)

    report = pool.run([job])
    result = report.results[0]

    assert result.return_code == 0
    assert result.exit_classification == "MISSING_EXPECTED_RECEIPT"
    assert result.succeeded is False


def test_receipt_visibility_tolerates_a_lagged_write(tmp_path: Path) -> None:
    """ACL-ORCH-RECEIPT-VISIBILITY-LAG: found live on a real 34-repository portfolio pass -- 8
    of 13 processed workers had a completed, receipt-writing, non-crashing child reported as
    receipt_observed=False, two after real, expensive provider work. A bare Path.is_file() right
    after process.wait() returns is not enough on this machine; the retry loop must catch a write
    that lands shortly after the check would otherwise have already given up."""

    path = tmp_path / "lagged-receipt.json"

    def _write_after_delay() -> None:
        time.sleep(0.12)
        path.write_text("{}", encoding="utf-8")

    writer = threading.Thread(target=_write_after_delay)
    writer.start()
    try:
        assert _wait_for_receipt_visibility(path, attempts=6, initial_delay_seconds=0.05) is True
    finally:
        writer.join()


def test_receipt_visibility_still_reports_a_genuine_absence(tmp_path: Path) -> None:
    path = tmp_path / "never-written.json"

    assert _wait_for_receipt_visibility(path, attempts=3, initial_delay_seconds=0.01) is False


def test_global_deadline_prevents_later_jobs_from_starting(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(repository_concurrency=1)
    jobs = [_job(tmp_path, f"job_{i}", i, sleep_seconds=0.3) for i in range(3)]

    report = pool.run(jobs, batch_deadline_seconds=0.1)

    assert report.results[0].exit_classification == "SUCCEEDED"
    assert report.results[1].exit_classification == "NOT_STARTED_DEADLINE_EXPIRED"
    assert report.results[2].exit_classification == "NOT_STARTED_DEADLINE_EXPIRED"
    assert report.batch_deadline_expired is True
