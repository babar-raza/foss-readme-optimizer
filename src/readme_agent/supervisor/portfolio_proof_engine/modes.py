"""PREFLIGHT and FACTS-ONLY: the two no-Qwen-call, no-candidate portfolio proof engine modes.

CANARIES/FLEET/FAILED-ONLY (which drive the full pipeline to acceptance) live in
`full_pipeline_modes.py`. See that module's docstring for why the split.
"""

from __future__ import annotations

import time
from pathlib import Path

from readme_agent.state.backend import StateBackend
from readme_agent.supervisor.portfolio_proof_engine.contracts import campaign_id_for_mode
from readme_agent.supervisor.portfolio_proof_engine.deadline import DeadlineBudget
from readme_agent.supervisor.portfolio_proof_engine.mode_shared import (
    ModePassResultV1,
    SuperviseCallable,
    build_registry_supervise_namespace,
    classify_and_record_intake,
    default_state_backend,
    default_supervise_call,
)
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import (
    default_output_root,
    write_receipt,
)
from readme_agent.supervisor.portfolio_proof_engine.registry_cohort import load_portfolio_entries
from readme_agent.supervisor.portfolio_proof_engine.stage_classifier import (
    classify_repository_stage,
)


def run_preflight(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    state_backend: StateBackend | None = None,
    max_deterministic_workers: int = 1,
) -> ModePassResultV1:
    """PREFLIGHT: resolve every registry entry, apply intake classification, bind source
    revisions and contracts. No Qwen calls, no candidates -- `intake_classification.py` alone,
    the earliest gate point in the real production runtime."""

    entries = list(load_portfolio_entries(registry_path))
    backend = state_backend or default_state_backend()
    resolved_output_root = output_root or default_output_root()
    campaign_id = campaign_id_for_mode("preflight")

    receipts = classify_and_record_intake(
        entries,
        backend,
        resolved_output_root,
        campaign_id,
        max_deterministic_workers=max_deterministic_workers,
    )
    return ModePassResultV1(
        mode="preflight",
        campaign_id=campaign_id,
        output_root=resolved_output_root,
        receipts=receipts,
    )


def run_facts_only(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    state_backend: StateBackend | None = None,
    supervise_call: SuperviseCallable | None = None,
    deadline: DeadlineBudget | None = None,
) -> ModePassResultV1:
    """FACTS-ONLY: for every processable repository (intake outcome not TERMINAL_SKIPPED), drive
    the existing local_poc runtime to exactly FACTS_READY via `--max-readme-poc-stage
    FACTS_READY`. No Qwen calls, no candidates -- entirely the existing bounded-stage mechanism."""

    entries = list(load_portfolio_entries(registry_path))
    backend = state_backend or default_state_backend()
    resolved_output_root = output_root or default_output_root()
    campaign_id = campaign_id_for_mode("facts-only")
    supervise = supervise_call or default_supervise_call()

    receipts = classify_and_record_intake(
        entries, backend, resolved_output_root, campaign_id, max_deterministic_workers=1
    )
    processable = [
        entry
        for entry, receipt in zip(entries, receipts, strict=True)
        if receipt.stage != "TERMINAL_SKIPPED"
    ]
    if deadline is not None and deadline.expired():
        return ModePassResultV1(
            mode="facts-only",
            campaign_id=campaign_id,
            output_root=resolved_output_root,
            receipts=receipts,
            deadline_expired=True,
        )
    if not processable:
        return ModePassResultV1(
            mode="facts-only",
            campaign_id=campaign_id,
            output_root=resolved_output_root,
            receipts=receipts,
        )

    started = time.monotonic()
    remaining = deadline.remaining() if deadline is not None else None
    budget = 300.0 if remaining is None else remaining
    namespace = build_registry_supervise_namespace(
        registry_path=str(registry_path) if registry_path else "data/products.json",
        only=[entry.org_repo for entry in processable],
        max_readme_poc_stage="FACTS_READY",
        portfolio_time_budget_seconds=budget,
    )
    supervise(namespace)
    per_repo_elapsed = (time.monotonic() - started) / len(processable)

    predecessors = {receipt.org_repo: receipt for receipt in receipts}
    for entry in processable:
        stage_receipt = classify_repository_stage(
            entry.org_repo,
            backend,
            predecessor=predecessors.get(entry.org_repo),
            ecosystem=entry.ecosystem,
            elapsed_seconds=per_repo_elapsed,
            provider_call_count=0,
        )
        write_receipt(resolved_output_root, campaign_id, stage_receipt)
        receipts.append(stage_receipt)

    return ModePassResultV1(
        mode="facts-only",
        campaign_id=campaign_id,
        output_root=resolved_output_root,
        receipts=receipts,
    )
