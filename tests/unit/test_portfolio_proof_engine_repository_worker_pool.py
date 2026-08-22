from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from readme_agent.supervisor.portfolio_proof_engine import repository_worker_pool
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

    return RepositoryJobSpecV1(
        job_id=job_id,
        input_ordinal=ordinal,
        org_repo="acme/" + job_id.replace("_", "-"),
        action="test-action",
        argv=tuple(argv),
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


def test_global_deadline_prevents_later_jobs_from_starting(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(repository_concurrency=1)
    jobs = [_job(tmp_path, f"job_{i}", i, sleep_seconds=0.3) for i in range(3)]

    report = pool.run(jobs, batch_deadline_seconds=0.1)

    assert report.results[0].exit_classification == "SUCCEEDED"
    assert report.results[1].exit_classification == "NOT_STARTED_DEADLINE_EXPIRED"
    assert report.results[2].exit_classification == "NOT_STARTED_DEADLINE_EXPIRED"
    assert report.batch_deadline_expired is True


def test_bounded_cancellation_leaves_no_leaked_process(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(grace_period_seconds=1.0)
    pid_file = tmp_path / "victim.pid"
    job = _job(
        tmp_path,
        "victim_job",
        0,
        sleep_seconds=60.0,
        deadline_seconds=0.2,
        pid_file=pid_file,
    )

    started = time.monotonic()
    report = pool.run([job])
    elapsed = time.monotonic() - started
    result = report.results[0]

    assert result.exit_classification == "TIMED_OUT"
    assert result.cancellation.requested is True
    assert result.cancellation.process_confirmed_terminated is True
    assert elapsed < 8.0, "cancellation must be bounded, not open-ended"
    assert pid_file.is_file()
    pid = int(pid_file.read_text(encoding="utf-8").strip())
    assert not _process_exists(pid), "the cancelled child process must not be leaked"


def test_stdout_capture_is_bounded_and_hashed(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(max_capture_bytes=1024)
    job = _job(tmp_path, "loud_job", 0, stdout_bytes=200_000)

    report = pool.run([job])
    result = report.results[0]

    assert result.succeeded is True
    assert len(result.stdout_excerpt) <= 1024
    assert result.stdout_byte_count == 200_000
    assert result.stdout_sha256 == hashlib.sha256(b"A" * 200_000).hexdigest()


def test_secret_shaped_environment_values_never_persisted(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    job = _job(
        tmp_path,
        "secret_job",
        0,
        environment={"MY_API_TOKEN": "leak-me-please-12345", "PATH": "irrelevant-value"},
    )

    report = pool.run([job])

    assert "leak-me-please-12345" not in report.model_dump_json()
    result = report.results[0]
    assert "MY_API_TOKEN" not in result.environment_names
    assert "PATH" in result.environment_names


def test_identical_job_specs_produce_identical_contract_hash(tmp_path: Path) -> None:
    kwargs = {
        "job_id": "same_job",
        "input_ordinal": 0,
        "org_repo": "acme/same-job",
        "action": "test-action",
        "argv": (sys.executable, str(FIXTURE_SCRIPT)),
        "work_dir": tmp_path / "w",
        "output_dir": tmp_path / "o",
        "evidence_dir": tmp_path / "e",
    }
    job_a = RepositoryJobSpecV1(**kwargs)
    job_b = RepositoryJobSpecV1(**kwargs)

    assert job_a is not job_b
    assert job_a.contract_hash() == job_b.contract_hash()


def test_module_imports_no_mission_state_apis() -> None:
    module_path = Path(repository_worker_pool.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "readme_agent" not in imported_roots


def test_no_automatic_retry_on_failure(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool()
    counter_file = tmp_path / "counter.txt"
    job = _job(tmp_path, "flaky_job", 0, exit_code=3, counter_file=counter_file)

    report = pool.run([job])

    assert report.results[0].exit_classification == "CHILD_NONZERO_EXIT"
    assert counter_file.read_text(encoding="utf-8").splitlines() == ["1"]


def test_named_non_provider_resource_class_is_bounded(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(
        repository_concurrency=4, extra_resource_limits={"jdk_toolchain_provisioning": 1}
    )
    jobs = [
        _job(
            tmp_path,
            f"jdk_job_{i}",
            i,
            sleep_seconds=0.15,
            resource_classes=("jdk_toolchain_provisioning",),
        )
        for i in range(3)
    ]

    report = pool.run(jobs)

    assert report.observed_max_resource_concurrency["jdk_toolchain_provisioning"] == 1
    assert all(result.succeeded for result in report.results)


def test_multi_resource_class_jobs_do_not_deadlock(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(
        repository_concurrency=2,
        provider_concurrency=1,
        extra_resource_limits={"jdk_toolchain_provisioning": 1},
    )
    job_a = _job(
        tmp_path,
        "job_a",
        0,
        sleep_seconds=0.1,
        resource_classes=("provider", "jdk_toolchain_provisioning"),
    )
    job_b = _job(
        tmp_path,
        "job_b",
        1,
        sleep_seconds=0.1,
        resource_classes=("jdk_toolchain_provisioning", "provider"),
    )

    started = time.monotonic()
    report = pool.run([job_a, job_b])
    elapsed = time.monotonic() - started

    assert all(result.succeeded for result in report.results)
    assert elapsed < 5.0, "fixed-order resource acquisition must not deadlock"


def test_child_environment_is_exactly_job_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RWP_TEST_PARENT_ONLY_VAR", "should-not-leak")
    pool = RepositoryWorkerPool()
    job = _job(
        tmp_path,
        "env_job",
        0,
        environment={"RWP_TEST_CHILD_VAR": "present"},
        print_env=("RWP_TEST_PARENT_ONLY_VAR", "RWP_TEST_CHILD_VAR"),
    )

    report = pool.run([job])
    result = report.results[0]

    assert result.succeeded is True
    assert "RWP_TEST_PARENT_ONLY_VAR=MISSING" in result.stdout_excerpt
    assert "RWP_TEST_CHILD_VAR=present" in result.stdout_excerpt
