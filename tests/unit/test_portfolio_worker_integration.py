from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

from readme_agent.supervisor.portfolio_worker_dispatch import (
    JDK_TOOLCHAIN_RESOURCE,
    build_repository_worker_job,
)
from readme_agent.supervisor.portfolio_worker_runtime import (
    PortfolioWorkerReceiptV1,
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
    receipt = PortfolioWorkerReceiptV1.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    assert receipt.registry_revision_id == "a" * 64
    assert receipt.result.org_repo == args.repo
    assert receipt.result.status == "FACTS_READY"
    assert receipt.result.llm_call_count == 0
