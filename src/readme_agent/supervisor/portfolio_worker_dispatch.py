"""Build and reduce process-isolated jobs for already-eligible portfolio members."""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path

from readme_agent import paths
from readme_agent.registry.models import ProductEntry
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_pool import (
    RepositoryJobSpecV1,
    ResourceRequirementV1,
    WorkerResultV1,
)
from readme_agent.supervisor.portfolio_worker_runtime import PortfolioWorkerReceiptV2

JDK_TOOLCHAIN_RESOURCE = "jdk_toolchain_provisioning"
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def build_repository_worker_job(
    args: argparse.Namespace,
    entry: ProductEntry,
    *,
    ordinal: int,
    registry_revision_id: str,
    source_revision: str | None,
) -> RepositoryJobSpecV1:
    """Translate one coordinator-approved member into an exact canonical CLI invocation."""

    safe_repo = _SAFE_ID.sub("_", entry.org_repo)
    job_id = f"{ordinal:03d}-{safe_repo}"
    invocation_id = uuid.uuid4().hex
    job_root = (
        paths.runs_dir() / "portfolio-workers" / registry_revision_id / job_id / invocation_id
    )
    receipt = job_root / "evidence" / "worker-receipt.json"
    argv = [
        sys.executable,
        "-m",
        "readme_agent.cli",
        "supervise",
        "--repo",
        entry.org_repo,
        "--execution-profile",
        "local_poc",
        "--no-registry-heal",
        "--portfolio-worker",
        "--portfolio-revision-id",
        registry_revision_id,
        "--portfolio-worker-receipt",
        str(receipt.resolve()),
        "--portfolio-worker-invocation-id",
        invocation_id,
    ]
    stage_limit = getattr(args, "max_readme_poc_stage", None)
    if stage_limit:
        argv.extend(("--max-readme-poc-stage", stage_limit))
    resume_trigger_key = getattr(args, "resume_trigger_key", None)
    if resume_trigger_key:
        argv.extend(("--resume-trigger-key", resume_trigger_key))
    if source_revision:
        argv.extend(("--portfolio-source-revision", source_revision))

    resource_classes = ["provider"]
    if entry.ecosystem == "java":
        resource_classes.append(JDK_TOOLCHAIN_RESOURCE)
    return RepositoryJobSpecV1(
        job_id=job_id,
        input_ordinal=ordinal,
        org_repo=entry.org_repo,
        source_revision=source_revision,
        action="canonical_local_poc_supervise",
        argv=tuple(argv),
        command_cwd=Path.cwd().resolve(),
        work_dir=job_root / "work",
        output_dir=job_root / "output",
        evidence_dir=job_root / "evidence",
        environment=dict(os.environ),
        resource=ResourceRequirementV1(resource_classes=tuple(resource_classes)),
        expected_receipt_path=receipt,
    )


def load_worker_receipt(
    worker_result: WorkerResultV1,
    *,
    registry_revision_id: str,
    expected_source_revision: str | None,
    persisted_source_revision: str | None,
) -> PortfolioWorkerReceiptV2 | None:
    """Load only an identity-matching receipt; subprocess status alone never means success."""

    if not worker_result.succeeded or worker_result.exit_classification != "SUCCEEDED":
        return None
    if worker_result.expected_receipt_path is None:
        return None
    receipt_path = Path(worker_result.expected_receipt_path)
    if not receipt_path.is_file():
        return None
    receipt = PortfolioWorkerReceiptV2.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    expected_invocation_id = receipt_path.parent.parent.name
    if (
        receipt.registry_revision_id != registry_revision_id
        or receipt.result.org_repo != worker_result.org_repo
        or receipt.worker_invocation_id != expected_invocation_id
        or persisted_source_revision is None
        or receipt.source_revision != persisted_source_revision
        or (
            expected_source_revision is not None
            and receipt.source_revision != expected_source_revision
        )
    ):
        return None
    return receipt
