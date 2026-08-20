"""PREFLIGHT and FACTS-ONLY: the two no-Qwen-call, no-candidate portfolio proof engine modes.

CANARIES/FLEET/FAILED-ONLY (which drive the full pipeline to acceptance) live in
`full_pipeline_modes.py`. See that module's docstring for why the split.
"""

from __future__ import annotations

import time
from pathlib import Path

from readme_agent.state.backend import StateBackend
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    ProofStageReceiptV1,
    campaign_id_for_mode,
)
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
from readme_agent.supervisor.portfolio_proof_engine.registry_cohort import (
    filter_entries,
    load_portfolio_entries,
)
from readme_agent.supervisor.portfolio_proof_engine.stage_classifier import (
    classify_repository_stage,
)

_PER_REPO_SLICE_SECONDS = 300.0
_FACTS_READY_OR_LATER_FOR_FACTS_ONLY = frozenset(
    {"FACTS_READY", "SECTION_PACKETS_READY", "SECTIONS_AUTHORED"}
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
        targeted_count=len(entries),
        completed_count=len(receipts),
    )


def _is_current_facts_ready(
    stage_receipt: ProofStageReceiptV1, current_revision: str | None
) -> bool:
    """A repository counts as genuinely, currently FACTS_READY only when its classified receipt
    is compatible with *this pass's own* observed source revision and carries a real, bound
    contract and facts hash -- a historical lifecycle state from another source revision (or one
    still missing a canonical facts hash) is never reported as current."""

    return (
        stage_receipt.status == "OK"
        and stage_receipt.stage in _FACTS_READY_OR_LATER_FOR_FACTS_ONLY
        and current_revision is not None
        and stage_receipt.source_revision == current_revision
        and bool(stage_receipt.contract_hash)
        and bool(stage_receipt.facts_hash)
    )


def run_facts_only(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    state_backend: StateBackend | None = None,
    supervise_call: SuperviseCallable | None = None,
    deadline: DeadlineBudget | None = None,
    only: list[str] | None = None,
    platform: str | None = None,
    family: str | None = None,
) -> ModePassResultV1:
    """FACTS-ONLY: for every processable, filter-selected repository, drive the existing
    local_poc runtime to exactly FACTS_READY via `--max-readme-poc-stage FACTS_READY`. No Qwen
    calls, no candidates.

    Dispatches one repository at a time (serial -- see the RUNTIME-TRUTH CLOSURE task's provider-
    concurrency note) so the deadline can be honestly checked *between* repositories: a repository
    the loop never reaches before the deadline is explicitly counted pending, never silently
    reported as processed, and a repository whose durable lifecycle turns out stale relative to
    this pass's own observed source revision is likewise left pending rather than over-claimed.
    """

    entries = filter_entries(
        load_portfolio_entries(registry_path), only=only, platform=platform, family=family
    )
    backend = state_backend or default_state_backend()
    resolved_output_root = output_root or default_output_root()
    campaign_id = campaign_id_for_mode("facts-only")
    supervise = supervise_call or default_supervise_call()

    intake_receipts = classify_and_record_intake(
        entries, backend, resolved_output_root, campaign_id, max_deterministic_workers=1
    )
    intake_by_repo = {receipt.org_repo: receipt for receipt in intake_receipts}
    processable = [
        entry for entry in entries if intake_by_repo[entry.org_repo].stage != "TERMINAL_SKIPPED"
    ]

    receipts: list[ProofStageReceiptV1] = list(intake_receipts)
    completed = 0
    failed = 0
    pending_entries = list(processable)

    for entry in processable:
        if deadline is not None and deadline.expired():
            break  # everything still in pending_entries stays truthfully pending

        remaining = deadline.remaining() if deadline is not None else None
        slice_budget = (
            _PER_REPO_SLICE_SECONDS
            if remaining is None
            else min(_PER_REPO_SLICE_SECONDS, remaining)
        )
        namespace = build_registry_supervise_namespace(
            registry_path=str(registry_path) if registry_path else "data/products.json",
            only=[entry.org_repo],
            max_readme_poc_stage="FACTS_READY",
            portfolio_time_budget_seconds=slice_budget,
        )
        started = time.monotonic()
        supervise(namespace)
        elapsed = time.monotonic() - started

        current_revision = intake_by_repo[entry.org_repo].source_revision
        stage_receipt = classify_repository_stage(
            entry.org_repo,
            backend,
            predecessor=intake_by_repo[entry.org_repo],
            ecosystem=entry.ecosystem,
            elapsed_seconds=elapsed,
            provider_call_count=0,  # FACTS_READY never calls the provider -- a known, true zero.
        )

        if _is_current_facts_ready(stage_receipt, current_revision):
            write_receipt(resolved_output_root, campaign_id, stage_receipt)
            receipts.append(stage_receipt)
            completed += 1
            pending_entries.remove(entry)
        elif stage_receipt.status == "FAILED":
            write_receipt(resolved_output_root, campaign_id, stage_receipt)
            receipts.append(stage_receipt)
            failed += 1
            pending_entries.remove(entry)
        # else: not yet current/complete for this pass -- no receipt written, stays pending;
        # never a fake stage receipt manufactured merely to reach the denominator.

    return ModePassResultV1(
        mode="facts-only",
        campaign_id=campaign_id,
        output_root=resolved_output_root,
        receipts=receipts,
        deadline_expired=bool(deadline and deadline.expired()),
        targeted_count=len(processable),
        completed_count=completed,
        pending_count=len(pending_entries),
        failed_count=failed,
        pending_org_repos=tuple(entry.org_repo for entry in pending_entries),
    )
