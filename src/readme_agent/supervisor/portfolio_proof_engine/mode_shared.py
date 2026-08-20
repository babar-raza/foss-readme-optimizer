"""Shared collaborator types/defaults/helpers for the mode drivers in `modes.py` and
`full_pipeline_modes.py`. Kept separate so neither mode-driver module has to import the other.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from readme_agent.registry.models import ProductEntry
from readme_agent.state.backend import StateBackend
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    ProofModeV1,
    ProofStageReceiptV1,
    RubricAcceptanceOutcome,
)
from readme_agent.supervisor.portfolio_proof_engine.intake_classification import classify_intake
from readme_agent.supervisor.portfolio_proof_engine.provider_concurrency import (
    run_deterministic_fanout,
)
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import write_receipt

SuperviseCallable = Callable[[argparse.Namespace], int]
RubricEvaluator = Callable[[str, StateBackend], RubricAcceptanceOutcome]


@dataclass
class ModePassResultV1:
    mode: ProofModeV1
    campaign_id: str
    output_root: Path
    receipts: list[ProofStageReceiptV1] = field(default_factory=list)
    deadline_expired: bool = False


def default_supervise_call() -> SuperviseCallable:
    from readme_agent.commands_supervision import cmd_supervise

    return cmd_supervise


def default_state_backend() -> StateBackend:
    from readme_agent.state.local_poc_backend import default_local_poc_state_backend

    return default_local_poc_state_backend()


def default_rubric_evaluator() -> RubricEvaluator:
    from readme_agent.supervisor.portfolio_proof_engine.rubric import evaluate_repository

    return evaluate_repository


def build_registry_supervise_namespace(
    *,
    registry_path: str,
    only: list[str] | None,
    max_readme_poc_stage: str | None,
    portfolio_time_budget_seconds: float,
    retry_blocked: bool = False,
) -> argparse.Namespace:
    """Mirrors the CLI's own `p_supervise` defaults (see `cli.py`) for every field
    `_cmd_supervise_registry` reads -- constructed directly (never via `argparse.parse_args`) so
    this engine can drive the existing scheduler in-process against an explicit cohort."""

    return argparse.Namespace(
        command="supervise",
        repo=None,
        registry=registry_path,
        mission_task_graph=None,
        mission_action="evaluate",
        mission_task_id=None,
        mission_control_input=None,
        mission_to_status=None,
        mission_observer="portfolio-proof-engine",
        mission_reason=None,
        mission_evidence=[],
        durable_state=False,
        resume_trigger_key=None,
        max_readme_poc_stage=max_readme_poc_stage,
        portfolio_time_budget_seconds=portfolio_time_budget_seconds,
        retry_blocked=retry_blocked,
        qualified_cohort_manifest=None,
        bounded_verified_canary=False,
        domain=None,
        no_registry_heal=True,
        execution_profile="local_poc",
        enable_dynamic_planning=False,
        only=",".join(only) if only else None,
    )


def classify_and_record_intake(
    entries: list[ProductEntry],
    backend: StateBackend,
    output_root: Path,
    campaign_id: str,
    *,
    max_deterministic_workers: int,
) -> list[ProofStageReceiptV1]:
    def _one(entry: ProductEntry) -> ProofStageReceiptV1:
        receipt = classify_intake(entry, backend)
        write_receipt(output_root, campaign_id, receipt)
        return receipt

    return run_deterministic_fanout(entries, _one, max_workers=max_deterministic_workers)
