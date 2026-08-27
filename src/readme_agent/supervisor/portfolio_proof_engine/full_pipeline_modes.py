"""CANARIES, FLEET, and FAILED-ONLY: the three portfolio proof engine modes that drive the full
pipeline through to acceptance (unlike PREFLIGHT/FACTS-ONLY in `modes.py`, which never call the
provider). Split into its own module purely for size (repo's "no monoliths" rule) -- all three
share `_run_full_pipeline_cohort` and the collaborators in `mode_shared.py`.

Per the task's own instruction, none of these three is executed live by this implementation task
while the facts/Qwen layers are still changing -- they are built and tested against fakes only.
"""

from __future__ import annotations

import time
from pathlib import Path

from readme_agent.registry.models import ProductEntry
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.supervisor.portfolio_proof_engine.acceptance_contract import (
    portfolio_acceptance_contract_hash,
)
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    ProofModeV1,
    ProofStageReceiptV1,
    RubricAcceptanceOutcome,
    campaign_id_for_mode,
)
from readme_agent.supervisor.portfolio_proof_engine.deadline import DeadlineBudget
from readme_agent.supervisor.portfolio_proof_engine.intake_classification import classify_intake
from readme_agent.supervisor.portfolio_proof_engine.mode_shared import (
    ModePassResultV1,
    RubricEvaluator,
    SuperviseCallable,
    build_registry_supervise_namespace,
    default_rubric_evaluator,
    default_state_backend,
    default_supervise_call,
    real_provider_call_count,
)
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import (
    default_output_root,
    find_accepted_receipt,
    write_receipt,
)
from readme_agent.supervisor.portfolio_proof_engine.registry_cohort import (
    filter_entries,
    load_portfolio_entries,
    resolve_fleet_remaining,
    resolve_seven_canaries,
)
from readme_agent.supervisor.portfolio_proof_engine.retry_policy import evaluate_retry
from readme_agent.supervisor.portfolio_proof_engine.stage_classifier import (
    classify_repository_stage,
)

_REVIEW_STAGES_ELIGIBLE_FOR_RUBRIC = frozenset({"FACTUAL_REVIEWED", "VISITOR_REVIEWED"})


def _run_full_pipeline_cohort(
    _mode: ProofModeV1,
    cohort: list[ProductEntry],
    *,
    output_root: Path,
    campaign_id: str,
    state_backend: StateBackend,
    supervise_call: SuperviseCallable,
    rubric_evaluator: RubricEvaluator,
    registry_path: Path | None,
    deadline: DeadlineBudget | None,
    retry_blocked: bool = False,
) -> list[ProofStageReceiptV1]:
    """Run each repository through the existing runtime to its natural terminal state, classify
    the resulting stage, and -- once review is complete -- run the 30-point rubric to distinguish
    RUBRIC_SCORED from ACCEPTED."""

    receipts: list[ProofStageReceiptV1] = []
    for entry in cohort:
        if deadline is not None and deadline.expired():
            break
        started = time.monotonic()
        remaining = deadline.remaining() if deadline is not None else None
        budget = 300.0 if remaining is None else remaining
        namespace = build_registry_supervise_namespace(
            registry_path=str(registry_path) if registry_path else "data/products.json",
            only=[entry.org_repo],
            max_readme_poc_stage=None,
            portfolio_time_budget_seconds=budget,
            retry_blocked=retry_blocked,
        )
        # Captured, never discarded: a repository can exit supervise_call non-zero while its
        # lifecycle state still classifies as a healthy-looking stage (e.g. a crash after the
        # last successful state save) -- dropping this return value silently hid that split.
        exit_code = supervise_call(namespace)
        elapsed = time.monotonic() - started
        # The real count of provider calls this supervise_call just made, read from the existing
        # LLM call ledger -- never a fabricated 0 for a stage that can genuinely call Qwen.
        call_count = real_provider_call_count()

        provisional = classify_repository_stage(
            entry.org_repo,
            state_backend,
            ecosystem=entry.ecosystem,
            elapsed_seconds=elapsed,
            provider_call_count=call_count,
            supervise_exit_code=exit_code,
        )
        rubric_result: RubricAcceptanceOutcome | None = None
        if provisional.stage in _REVIEW_STAGES_ELIGIBLE_FOR_RUBRIC:
            try:
                rubric_result = rubric_evaluator(entry.org_repo, state_backend)
            except Exception:  # noqa: BLE001 -- missing evidence scores 0, never crashes the pass
                rubric_result = None
        if rubric_result is None:
            final_receipt = provisional
        else:
            # The final receipt names the review-stage receipt as its predecessor. Persist that
            # exact predecessor before the final write so dashboard/replay readers can resolve a
            # complete chain rather than dropping a valid acceptance as an orphan.
            write_receipt(output_root, campaign_id, provisional)
            final_receipt = classify_repository_stage(
                entry.org_repo,
                state_backend,
                predecessor=provisional,
                ecosystem=entry.ecosystem,
                elapsed_seconds=elapsed,
                provider_call_count=call_count,
                supervise_exit_code=exit_code,
                rubric_result=rubric_result,
            )
        write_receipt(output_root, campaign_id, final_receipt)
        receipts.append(final_receipt)
    return receipts


def _pipeline_counts(
    cohort: list[ProductEntry], pipeline_receipts: list[ProofStageReceiptV1]
) -> tuple[int, int, tuple[str, ...]]:
    """`_run_full_pipeline_cohort` writes exactly one receipt per cohort member it actually
    attempts (breaking early on deadline expiry) -- so an entry with no corresponding receipt
    was never reached this pass and stays truthfully pending, not silently reported as done."""

    attempted = {receipt.org_repo for receipt in pipeline_receipts}
    completed = sum(1 for receipt in pipeline_receipts if receipt.status == "OK")
    failed = sum(1 for receipt in pipeline_receipts if receipt.status == "FAILED")
    pending = tuple(entry.org_repo for entry in cohort if entry.org_repo not in attempted)
    return completed, failed, pending


def run_canaries(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    state_backend: StateBackend | None = None,
    supervise_call: SuperviseCallable | None = None,
    rubric_evaluator: RubricEvaluator | None = None,
    deadline: DeadlineBudget | None = None,
    retry_blocked: bool = False,
) -> ModePassResultV1:
    """CANARIES: the fixed seven-ecosystem cohort, registry-resolved (`registry_cohort.py`),
    driven to acceptance."""

    entries = load_portfolio_entries(registry_path)
    cohort = resolve_seven_canaries(entries)
    backend = state_backend or default_state_backend()
    resolved_output_root = output_root or default_output_root()
    campaign_id = campaign_id_for_mode("canaries")
    receipts = _run_full_pipeline_cohort(
        "canaries",
        cohort,
        output_root=resolved_output_root,
        campaign_id=campaign_id,
        state_backend=backend,
        supervise_call=supervise_call or default_supervise_call(),
        rubric_evaluator=rubric_evaluator or default_rubric_evaluator(),
        registry_path=registry_path,
        deadline=deadline,
        retry_blocked=retry_blocked,
    )
    completed, failed, pending = _pipeline_counts(cohort, receipts)
    return ModePassResultV1(
        mode="canaries",
        campaign_id=campaign_id,
        output_root=resolved_output_root,
        receipts=receipts,
        deadline_expired=bool(deadline and deadline.expired()),
        targeted_count=len(cohort),
        completed_count=completed,
        pending_count=len(pending),
        failed_count=failed,
        pending_org_repos=pending,
    )


def run_fleet(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    state_backend: StateBackend | None = None,
    supervise_call: SuperviseCallable | None = None,
    rubric_evaluator: RubricEvaluator | None = None,
    deadline: DeadlineBudget | None = None,
    platform: str | None = None,
    family: str | None = None,
    only: list[str] | None = None,
    retry_blocked: bool = False,
) -> ModePassResultV1:
    """FLEET: every processable repository not already ACCEPTED. Never restarts a successful
    facts/section/review/candidate stage -- `commands_supervision.py`'s own cache layers already
    guarantee that for whatever this pass re-invokes the existing scheduler on."""

    entries: list[ProductEntry] = filter_entries(
        load_portfolio_entries(registry_path), only=only, platform=platform, family=family
    )
    backend = state_backend or default_state_backend()
    resolved_output_root = output_root or default_output_root()
    campaign_id = campaign_id_for_mode("fleet")

    accepted = {
        entry.org_repo
        for entry in entries
        if _accepted_receipt_is_current(
            find_accepted_receipt(resolved_output_root, entry.org_repo),
            state_backend=backend,
        )
    }
    remaining = resolve_fleet_remaining(entries, accepted)
    intake_receipts = [classify_intake(entry, backend) for entry in remaining]
    processable = [
        entry
        for entry, receipt in zip(remaining, intake_receipts, strict=True)
        if receipt.stage != "TERMINAL_SKIPPED"
    ]
    for receipt in intake_receipts:
        write_receipt(resolved_output_root, campaign_id, receipt)

    pipeline_receipts = _run_full_pipeline_cohort(
        "fleet",
        processable,
        output_root=resolved_output_root,
        campaign_id=campaign_id,
        state_backend=backend,
        supervise_call=supervise_call or default_supervise_call(),
        rubric_evaluator=rubric_evaluator or default_rubric_evaluator(),
        registry_path=registry_path,
        deadline=deadline,
        retry_blocked=retry_blocked,
    )
    receipts = list(intake_receipts)
    receipts.extend(pipeline_receipts)
    completed, failed, pending = _pipeline_counts(processable, pipeline_receipts)
    return ModePassResultV1(
        mode="fleet",
        campaign_id=campaign_id,
        output_root=resolved_output_root,
        receipts=receipts,
        deadline_expired=bool(deadline and deadline.expired()),
        targeted_count=len(processable),
        completed_count=completed,
        pending_count=len(pending),
        failed_count=failed,
        pending_org_repos=pending,
    )


def _accepted_receipt_is_current(
    receipt: ProofStageReceiptV1 | None,
    *,
    state_backend: StateBackend,
) -> bool:
    """Require an accepted receipt to match live lifecycle and acceptance contracts."""

    if receipt is None or receipt.status != "OK" or receipt.stage != "ACCEPTED":
        return False
    state = state_backend.load(receipt.org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        return False
    return bool(
        receipt.source_revision == lifecycle.source_revision
        and receipt.facts_hash == lifecycle.facts_hash
        and receipt.candidate_hash == lifecycle.candidate_hash
        and receipt.version_hash == portfolio_acceptance_contract_hash()
    )


def run_failed_only(
    *,
    registry_path: Path | None = None,
    output_root: Path | None = None,
    state_backend: StateBackend | None = None,
    supervise_call: SuperviseCallable | None = None,
    rubric_evaluator: RubricEvaluator | None = None,
    deadline: DeadlineBudget | None = None,
    retry_blocked: bool = False,
) -> ModePassResultV1:
    """FAILED-ONLY: retry only failed stages/sections, and only when an explicit causal
    fingerprint changed since the last failure (`retry_policy.py`, itself reusing
    `blocked_decision_cache.py`). Two same-fingerprint failures mark REASSESS_REQUIRED instead of
    looping -- never a third equivalent attempt."""

    entries = load_portfolio_entries(registry_path)
    backend = state_backend or default_state_backend()
    resolved_output_root = output_root or default_output_root()
    campaign_id = campaign_id_for_mode("failed-only")

    failed_entries: list[ProductEntry] = []
    receipts: list[ProofStageReceiptV1] = []
    reassessed = 0
    refused = 0
    for entry in entries:
        latest = classify_repository_stage(entry.org_repo, backend, ecosystem=entry.ecosystem)
        if latest.status != "FAILED" or latest.stage == "TERMINAL_SKIPPED":
            continue
        # Reuse the revision this proof engine already bound the failure to, rather than a
        # fresh live network probe here: the next preflight/facts-only pass is what re-binds
        # `source_revision` if the registry HEAD actually moved.
        decision = evaluate_retry(entry, current_source_revision=latest.source_revision)
        if decision.reassess_required:
            receipt = ProofStageReceiptV1(
                org_repo=entry.org_repo,
                ecosystem=entry.ecosystem,
                source_revision=latest.source_revision,
                stage="REASSESS_REQUIRED",
                status="FAILED",
                failure_reason=decision.reason[:500],
                elapsed_seconds=0.0,
                provider_call_count=0,
                predecessor_receipt_hash=latest.canonical_hash(),
            )
            write_receipt(resolved_output_root, campaign_id, receipt)
            receipts.append(receipt)
            reassessed += 1
            continue
        if not decision.eligible:
            # No causal fingerprint change: refuse the retry, leave the prior receipt standing.
            refused += 1
            continue
        failed_entries.append(entry)

    pipeline_receipts: list[ProofStageReceiptV1] = []
    if failed_entries:
        pipeline_receipts = _run_full_pipeline_cohort(
            "failed-only",
            failed_entries,
            output_root=resolved_output_root,
            campaign_id=campaign_id,
            state_backend=backend,
            supervise_call=supervise_call or default_supervise_call(),
            rubric_evaluator=rubric_evaluator or default_rubric_evaluator(),
            registry_path=registry_path,
            deadline=deadline,
            retry_blocked=retry_blocked,
        )
        receipts.extend(pipeline_receipts)

    completed, failed, pending = _pipeline_counts(failed_entries, pipeline_receipts)
    return ModePassResultV1(
        mode="failed-only",
        campaign_id=campaign_id,
        output_root=resolved_output_root,
        receipts=receipts,
        deadline_expired=bool(deadline and deadline.expired()),
        targeted_count=len(failed_entries) + reassessed + refused,
        completed_count=completed,
        pending_count=len(pending),
        failed_count=failed + reassessed + refused,
        pending_org_repos=pending,
    )
