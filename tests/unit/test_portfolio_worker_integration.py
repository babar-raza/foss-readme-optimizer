from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

from readme_agent.supervisor.portfolio import PortfolioRepositoryResultV1
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_pool import WorkerResultV1
from readme_agent.supervisor.portfolio_worker_dispatch import (
    JDK_TOOLCHAIN_RESOURCE,
    build_repository_worker_job,
    load_worker_receipt,
)
from readme_agent.supervisor.portfolio_worker_runtime import (
    PortfolioWorkerReceiptV2,
    run_portfolio_worker,
)


def _entry(org_repo: str, ecosystem: str = "python") -> SimpleNamespace:
    return SimpleNamespace(org_repo=org_repo, ecosystem=ecosystem)


def test_job_uses_canonical_cli_and_disjoint_scratch_while_retaining_repo_cwd(
    monkeypatch, tmp_path: Path
) -> None:
    import readme_agent.paths as paths

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    args = argparse.Namespace(max_readme_poc_stage="FACTS_READY", resume_trigger_key="trigger-1")
    job = build_repository_worker_job(
        args,
        _entry("org/repo", "java"),
        ordinal=3,
        registry_revision_id="a" * 64,
        source_revision="b" * 40,
    )

    assert job.command_cwd == Path.cwd().resolve()
    assert job.command_cwd != job.work_dir
    assert "--no-registry-heal" in job.argv
    assert "--portfolio-worker" in job.argv
    assert "--portfolio-worker-invocation-id" in job.argv
    assert job.argv[job.argv.index("--repo") + 1] == "org/repo"
    assert job.argv[job.argv.index("--portfolio-revision-id") + 1] == "a" * 64
    assert JDK_TOOLCHAIN_RESOURCE in job.resource.resource_classes
    assert job.expected_receipt_path is not None
    assert job.expected_receipt_path.is_relative_to(tmp_path / "runs" / "portfolio-workers")


def test_two_canonical_jobs_have_disjoint_writable_contracts(monkeypatch, tmp_path: Path) -> None:
    import readme_agent.paths as paths

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    args = argparse.Namespace(max_readme_poc_stage="INTAKE_READY", resume_trigger_key=None)
    jobs = [
        build_repository_worker_job(
            args,
            _entry("org/one"),
            ordinal=0,
            registry_revision_id="a" * 64,
            source_revision=None,
        ),
        build_repository_worker_job(
            args,
            _entry("org/two"),
            ordinal=1,
            registry_revision_id="a" * 64,
            source_revision=None,
        ),
    ]

    assert jobs[0].job_id != jobs[1].job_id
    assert set(jobs[0].writable_roots()).isdisjoint(jobs[1].writable_roots())


def test_command_cwd_is_not_treated_as_a_shared_writable_root(monkeypatch, tmp_path: Path) -> None:
    import readme_agent.paths as paths

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    args = argparse.Namespace(max_readme_poc_stage=None, resume_trigger_key=None)
    first = build_repository_worker_job(
        args,
        _entry("org/one"),
        ordinal=0,
        registry_revision_id="a" * 64,
        source_revision=None,
    )
    second = build_repository_worker_job(
        args,
        _entry("org/two"),
        ordinal=1,
        registry_revision_id="a" * 64,
        source_revision=None,
    )
    assert first.command_cwd == second.command_cwd
    assert set(first.writable_roots()).isdisjoint(second.writable_roots())


def test_worker_binds_exact_revision_and_writes_terminal_receipt(
    monkeypatch, tmp_path: Path
) -> None:
    import readme_agent.paths as paths
    import readme_agent.supervisor.portfolio_worker_runtime as runtime

    revision = SimpleNamespace(
        revision_id="a" * 64,
        admitted_repositories=["aspose-note-foss/Aspose.Note-FOSS-for-Python"],
    )
    backend = SimpleNamespace(load=lambda org_repo: None)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(runtime, "load_current_registry_revision", lambda: revision)
    monkeypatch.setattr(
        runtime,
        "evaluate_registry_revision",
        lambda revision, products: SimpleNamespace(eligible=True),
    )
    monkeypatch.setattr(runtime, "default_local_poc_state_backend", lambda: backend)
    receipt_path = tmp_path / "runs" / "portfolio-workers" / "worker-receipt.json"
    args = argparse.Namespace(
        repo="aspose-note-foss/Aspose.Note-FOSS-for-Python",
        execution_profile="local_poc",
        no_registry_heal=True,
        portfolio_revision_id="a" * 64,
        portfolio_worker_receipt=str(receipt_path),
        portfolio_worker_invocation_id="c" * 32,
        portfolio_source_revision="b" * 40,
        max_readme_poc_stage="FACTS_READY",
    )

    def _invoke(member_args: argparse.Namespace) -> int:
        member_args._terminal_supervise_result = SimpleNamespace(
            processability_disposition=None,
            readme_lifecycle_status="FACTS_READY",
            blocked_reason=None,
            blocked_category=None,
        )
        return 0

    assert run_portfolio_worker(args, _invoke) == 0
    receipt = PortfolioWorkerReceiptV2.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    assert receipt.registry_revision_id == "a" * 64
    assert receipt.worker_invocation_id == "c" * 32
    assert receipt.source_revision == "b" * 40
    assert receipt.result.org_repo == args.repo
    assert receipt.result.status == "FACTS_READY"
    assert receipt.result.llm_call_count == 0


def test_failed_current_worker_cannot_reuse_a_stale_success_receipt(
    monkeypatch, tmp_path: Path
) -> None:
    import readme_agent.paths as paths

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    job = build_repository_worker_job(
        argparse.Namespace(max_readme_poc_stage="FACTS_READY", resume_trigger_key=None),
        _entry("org/repo"),
        ordinal=0,
        registry_revision_id="a" * 64,
        source_revision="b" * 40,
    )
    invocation_id = job.argv[job.argv.index("--portfolio-worker-invocation-id") + 1]
    assert job.expected_receipt_path is not None
    job.expected_receipt_path.parent.mkdir(parents=True)
    job.expected_receipt_path.write_text(
        PortfolioWorkerReceiptV2(
            registry_revision_id="a" * 64,
            worker_invocation_id=invocation_id,
            source_revision="b" * 40,
            result=PortfolioRepositoryResultV1(
                org_repo="org/repo",
                status="FACTS_READY",
                exit_code=0,
            ),
        ).model_dump_json(),
        encoding="utf-8",
    )
    failed = WorkerResultV1(
        job_id=job.job_id,
        input_ordinal=job.input_ordinal,
        org_repo=job.org_repo,
        contract_hash=job.contract_hash(),
        exit_classification="CHILD_NONZERO_EXIT",
        succeeded=False,
        return_code=1,
        duration_seconds=0.1,
        output_dir=str(job.output_dir),
        evidence_dir=str(job.evidence_dir),
        expected_receipt_path=str(job.expected_receipt_path),
        receipt_observed=True,
    )

    assert (
        load_worker_receipt(
            failed,
            registry_revision_id="a" * 64,
            expected_source_revision="b" * 40,
        )
        is None
    )
