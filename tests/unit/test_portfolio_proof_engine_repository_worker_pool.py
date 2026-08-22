from __future__ import annotations

import ast
import hashlib
import os
import subprocess
import sys
import time
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


def test_bounded_cancellation_leaves_no_leaked_process(tmp_path: Path) -> None:
    pool = RepositoryWorkerPool(grace_period_seconds=1.0)
    pid_file = tmp_path / "victim.pid"
    job = _job(
        tmp_path,
        "victim_job",
        0,
        sleep_seconds=60.0,
        deadline_seconds=0.5,
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
    module_dir = Path(repository_worker_pool.__file__).parent
    implementation_prefix = "readme_agent.supervisor.portfolio_proof_engine.repository_worker_"
    disallowed: list[tuple[str, str]] = []
    for module_path in sorted(module_dir.glob("repository_worker_*.py")):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for name in imported:
                if name.startswith("readme_agent.") and not name.startswith(implementation_prefix):
                    disallowed.append((module_path.name, name))

    assert disallowed == []


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
