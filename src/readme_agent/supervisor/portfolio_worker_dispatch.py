"""Build and reduce process-isolated jobs for already-eligible portfolio members."""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import win_long_path
from readme_agent.registry.models import ProductEntry
from readme_agent.supervisor.portfolio_proof_engine.repository_worker_pool import (
    RepositoryJobSpecV1,
    ResourceRequirementV1,
    WorkerResultV1,
)
from readme_agent.supervisor.portfolio_worker_runtime import PortfolioWorkerReceiptV2


def _read_receipt_text(receipt_path: Path) -> str | None:
    """Long-path-safe existence check and read, in one place.

    ACL-ORCH-RECEIPT-VISIBILITY-LAG's MAX_PATH fix (`portfolio_proof_engine/
    repository_worker_execution.py::_receipt_exists`) only ever patched the check that sets
    `WorkerResultV1.receipt_observed` -- it never touched this module, which does its own,
    completely independent, still-unfixed `Path.is_file()`/`Path.read_text()` here. Found live:
    a real receipt at a real, confirmed 261-character path was correctly observed as present by
    the fixed check (`receipt_observed: True` in the batch report) and still discarded as
    `receipt_rejected` by `load_worker_receipt()`, because this second, separate check never got
    the same fix. Both `load_worker_receipt()` and `describe_worker_receipt_rejection()` below
    must go through this one function so a future long-path fix can never again land in only one
    of the (it turns out, more than one) places that independently re-derive the same check.
    """

    target = win_long_path(receipt_path) if os.name == "nt" else str(receipt_path)
    if not os.path.isfile(target):
        return None
    with open(target, encoding="utf-8") as handle:
        return handle.read()


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
    """Load only an identity-matching, exit-code-consistent receipt; subprocess status
    alone never means success, and a receipt alone never means success either.

    `CHILD_NONZERO_EXIT` deliberately still proceeds to the checks below: the worker's own
    `cmd_supervise` CLI returns a nonzero exit code for a completed, legitimate non-error
    disposition (e.g. `BLOCKED`), not only for a crash -- discarding every such receipt
    misclassified real `BLOCKED` repositories as portfolio-level `SYSTEM_FAILURE`, confirmed
    live on a full portfolio pass. But a receipt existing and matching identity is not enough
    on its own either: `run_portfolio_worker()` (`portfolio_worker_runtime.py`) writes its
    receipt, `return`s the matching `exit_code`, and only then runs its `finally` cleanup
    (`reset_registry_revision`) -- if that cleanup step itself raises, the process's real exit
    code can end up disagreeing with what the already-written receipt honestly recorded, and a
    stale file surviving from an unrelated earlier invocation despite matching identity is not
    ruled out either. The receipt's own `result.exit_code` is therefore additionally required
    to agree with the process's actual observed `return_code` -- the one field a genuinely
    consistent, current-invocation receipt can never disagree with itself on.

    Every other classification (`TIMED_OUT`, `SPAWN_FAILED`, `MISSING_EXPECTED_RECEIPT`,
    `REJECTED_DUPLICATE`, `NOT_STARTED_DEADLINE_EXPIRED`) still means no trustworthy receipt
    can exist and must still return `None` here.
    """

    if worker_result.exit_classification not in ("SUCCEEDED", "CHILD_NONZERO_EXIT"):
        return None
    if worker_result.expected_receipt_path is None:
        return None
    receipt_path = Path(worker_result.expected_receipt_path)
    receipt_text = _read_receipt_text(receipt_path)
    if receipt_text is None:
        return None
    receipt = PortfolioWorkerReceiptV2.model_validate_json(receipt_text)
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
        or receipt.result.exit_code != worker_result.return_code
    ):
        return None
    return receipt


def describe_worker_receipt_rejection(
    worker_result: WorkerResultV1,
    *,
    registry_revision_id: str,
    expected_source_revision: str | None,
    persisted_source_revision: str | None,
) -> str | None:
    """Diagnose why `load_worker_receipt()` returned `None`, purely for operator visibility.

    Mirrors every gate in `load_worker_receipt()` in the same order but reports which one
    failed instead of silently discarding the receipt. This function makes no trust
    decision of its own and must never be substituted for `load_worker_receipt()` --
    ACL-ORCH-SILENT-RECEIPT-REJECTION found this the hard way: a fully valid, identity-
    and source-revision-matching receipt for aspose-email-foss/Aspose.Email-FOSS-for-Python
    was discarded as `SYSTEM_FAILURE` with an empty reason (both `failure_reason` and
    `stderr_excerpt` were empty), and confirming *why* required manually cross-referencing
    a surviving `evidence/worker-receipt.json` against durable state by hand because nothing
    in the normal run output said which check failed. Returns `None` if the receipt would
    in fact have been accepted (should not happen when called only after `load_worker_receipt`
    itself returned `None`) or if the failure isn't a receipt-rejection case at all.
    """

    if worker_result.exit_classification not in ("SUCCEEDED", "CHILD_NONZERO_EXIT"):
        return None
    if worker_result.expected_receipt_path is None:
        return "no expected receipt path was configured for this worker"
    receipt_path = Path(worker_result.expected_receipt_path)
    receipt_text = _read_receipt_text(receipt_path)
    if receipt_text is None:
        return f"no receipt file exists at the expected path {receipt_path}"
    try:
        receipt = PortfolioWorkerReceiptV2.model_validate_json(receipt_text)
    except Exception as exc:  # noqa: BLE001 -- diagnostic only, must never itself crash
        return f"receipt file exists but failed to parse: {type(exc).__name__}: {exc}"
    expected_invocation_id = receipt_path.parent.parent.name
    mismatches: list[str] = []
    if receipt.registry_revision_id != registry_revision_id:
        mismatches.append(
            f"registry_revision_id receipt={receipt.registry_revision_id!r} "
            f"expected={registry_revision_id!r}"
        )
    if receipt.result.org_repo != worker_result.org_repo:
        mismatches.append(
            f"org_repo receipt={receipt.result.org_repo!r} expected={worker_result.org_repo!r}"
        )
    if receipt.worker_invocation_id != expected_invocation_id:
        mismatches.append(
            f"worker_invocation_id receipt={receipt.worker_invocation_id!r} "
            f"path_derived={expected_invocation_id!r}"
        )
    if persisted_source_revision is None:
        mismatches.append(
            "persisted_source_revision is None (durable state has no lifecycle "
            "source_revision yet for this org_repo)"
        )
    elif receipt.source_revision != persisted_source_revision:
        mismatches.append(
            f"source_revision receipt={receipt.source_revision!r} "
            f"persisted={persisted_source_revision!r}"
        )
    if expected_source_revision is not None and receipt.source_revision != expected_source_revision:
        mismatches.append(
            f"source_revision receipt={receipt.source_revision!r} "
            f"expected_by_parent={expected_source_revision!r}"
        )
    if receipt.result.exit_code != worker_result.return_code:
        mismatches.append(
            f"exit_code receipt={receipt.result.exit_code!r} "
            f"observed_return_code={worker_result.return_code!r}"
        )
    if not mismatches:
        return None
    return "; ".join(mismatches)
