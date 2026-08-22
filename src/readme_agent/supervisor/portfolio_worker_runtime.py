"""Bind one process-isolated portfolio worker to the canonical local POC contracts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.registry.loader import PRODUCTS_PATH, require_listed
from readme_agent.registry.revision_gate import evaluate_registry_revision
from readme_agent.registry.revision_store import (
    bind_registry_revision,
    load_current_registry_revision,
    reset_registry_revision,
)
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.local_poc_backend import default_local_poc_state_backend
from readme_agent.supervisor.portfolio import PortfolioRepositoryResultV1


class PortfolioWorkerReceiptV1(BaseModel):
    """Reducer input written by a canonical child after its terminal classification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=1, ge=1, le=1)
    registry_revision_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: PortfolioRepositoryResultV1


class _LlmAccounting(TypedDict, total=False):
    llm_accounting_status: Literal["EXACT", "UNKNOWN_LEGACY"]
    llm_call_count: int | None
    llm_call_ids: list[str]
    llm_calls_by_job: dict[str, int]
    llm_fixture_call_count: int | None
    llm_cache_reuse_count: int | None


def _receipt_path(args: argparse.Namespace) -> Path:
    requested = Path(args.portfolio_worker_receipt).resolve()
    allowed_root = (paths.runs_dir() / "portfolio-workers").resolve()
    if not requested.is_relative_to(allowed_root):
        raise ValueError("portfolio worker receipt must be under runs/portfolio-workers")
    return requested


def _llm_accounting(args: argparse.Namespace) -> _LlmAccounting:
    if not getattr(args, "_llm_accounting_run_id", None):
        return {
            "llm_accounting_status": "EXACT",
            "llm_call_count": 0,
            "llm_call_ids": [],
            "llm_calls_by_job": {},
            "llm_fixture_call_count": 0,
            "llm_cache_reuse_count": 0,
        }

    from readme_agent.llm.call_ledger import current_llm_accounting_summary

    summary = current_llm_accounting_summary()
    if summary.status != "EXACT":
        return {}
    return {
        "llm_accounting_status": "EXACT",
        "llm_call_count": summary.provider_call_count,
        "llm_call_ids": summary.call_ids,
        "llm_calls_by_job": summary.calls_by_job,
        "llm_fixture_call_count": summary.fixture_call_count,
        "llm_cache_reuse_count": summary.cache_reuse_count,
    }


def build_portfolio_terminal_result(
    args: argparse.Namespace, exit_code: int
) -> PortfolioRepositoryResultV1:
    state_backend = args._state_backend_override
    persisted = state_backend.load(args.repo)
    lifecycle = persisted.readme_poc_lifecycle if persisted is not None else None
    terminal = getattr(args, "_terminal_supervise_result", None)
    stage_limit = getattr(args, "max_readme_poc_stage", None)
    if terminal is not None and terminal.processability_disposition is not None:
        status = terminal.processability_disposition
    elif stage_limit is not None and terminal is not None and terminal.readme_lifecycle_status:
        status = terminal.readme_lifecycle_status
    elif lifecycle is not None:
        status = lifecycle.status
    else:
        status = "NO_POC_LIFECYCLE" if exit_code == 0 else "NON_SUCCESS_TERMINAL"

    return PortfolioRepositoryResultV1(
        org_repo=args.repo,
        content_assurance=(
            lifecycle.content_assurance
            if isinstance(lifecycle, ReadmePocLifecycleStateV2)
            else "repository_verified"
        ),
        status=status,
        exit_code=exit_code,
        blocked_reason=terminal.blocked_reason if terminal is not None else None,
        blocked_category=terminal.blocked_category if terminal is not None else None,
        **_llm_accounting(args),
    )


def record_portfolio_blocked_decision(
    args: argparse.Namespace,
    result: PortfolioRepositoryResultV1,
    *,
    entry: Any | None = None,
) -> None:
    """Retain the existing best-effort blocked-decision behavior inside the child."""

    from readme_agent.supervisor.blocked_decision_cache import (
        clear_blocked_decision,
        record_blocked_outcome,
    )
    from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
    from readme_agent.supervisor.local_poc_cache import current_blocked_decision_dependencies

    entry = entry or require_listed(args.repo)
    persisted = args._state_backend_override.load(args.repo)
    lifecycle = persisted.readme_poc_lifecycle if persisted is not None else None
    org, repo = args.repo.split("/", maxsplit=1)
    decision_path = paths.readme_poc_blocked_decision_path(org, repo)
    pinned_revision = (
        lifecycle.source_revision
        if isinstance(lifecycle, ReadmePocLifecycleStateV2) and lifecycle.source_revision
        else getattr(args, "_portfolio_source_revision", None)
    )
    if result.blocked_reason is not None and pinned_revision:
        record_blocked_outcome(
            decision_path,
            org_repo=args.repo,
            status=result.status,
            exit_code=result.exit_code,
            blocked_reason=result.blocked_reason,
            blocked_category=result.blocked_category,
            dependencies=current_blocked_decision_dependencies(
                org_repo=args.repo,
                source_revision=pinned_revision,
                control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
                ecosystem=entry.ecosystem,
                family=getattr(entry, "family", None),
            ),
            run_id=getattr(args, "_llm_accounting_run_id", None),
        )
    else:
        clear_blocked_decision(decision_path)


def run_portfolio_worker(
    args: argparse.Namespace,
    invoke: Callable[[argparse.Namespace], int],
) -> int:
    """Validate the frozen parent contract, run one canonical member, and write a receipt."""

    if args.execution_profile != "local_poc" or not args.no_registry_heal:
        raise ValueError("portfolio workers require local_poc and --no-registry-heal")
    revision = load_current_registry_revision()
    if revision is None or revision.revision_id != args.portfolio_revision_id:
        raise ValueError("portfolio worker registry revision is missing or drifted")
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    gate = evaluate_registry_revision(revision, products)
    if not gate.eligible or args.repo not in revision.admitted_repositories:
        raise ValueError("portfolio worker repository is not admitted by the frozen revision")

    args._portfolio_member = True
    args._state_backend_override = default_local_poc_state_backend()
    args._portfolio_source_revision = getattr(args, "portfolio_source_revision", None)
    token = bind_registry_revision(revision)
    try:
        exit_code = invoke(args)
        result = build_portfolio_terminal_result(args, exit_code)
        try:
            record_portfolio_blocked_decision(args, result)
        except Exception:
            # This cache can only save a later retry; it cannot change the real terminal result.
            pass
        write_redacted_json(
            _receipt_path(args),
            PortfolioWorkerReceiptV1(
                registry_revision_id=revision.revision_id,
                result=result,
            ),
        )
        return exit_code
    finally:
        reset_registry_revision(token)
