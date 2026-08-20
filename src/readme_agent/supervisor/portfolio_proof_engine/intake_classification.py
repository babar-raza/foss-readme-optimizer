"""Registry-wide intake classification -- the PREFLIGHT mode's sole implementation.

Wraps the existing `supervisor/intake.py::run_readonly_intake_preflight()` (itself backed by
`registry/intake.py::classify_readonly_intake()`, which already implements the generic
no-substantive-content processability rule live) once per registry entry. No new classification
logic, no Qwen call, no candidate generated -- exactly the PREFLIGHT mode's contract.
"""

from __future__ import annotations

import time
from typing import Literal

from readme_agent.registry.intake import intake_contract_hash
from readme_agent.registry.models import ProductEntry
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import IntakePreflightOutcomeV1
from readme_agent.supervisor.intake import run_readonly_intake_preflight
from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    ProofStageReceiptV1,
    ProofStageV1,
)

# The generic no-substantive-content rule (and archived/inactive) -- terminally out of scope,
# never a hard-coded repository identity. See registry/intake.py::_classify_tree_processability.
_TERMINAL_SKIP_OUTCOMES: frozenset[IntakePreflightOutcomeV1] = frozenset(
    {"BLOCKED_NO_SUBSTANTIVE_CONTENT", "NOT_APPLICABLE"}
)
_BLOCKED_INPUT_OUTCOMES: frozenset[IntakePreflightOutcomeV1] = frozenset(
    {"BLOCKED_EVIDENCE", "BLOCKED_CLASSIFICATION", "BLOCKED_ACCESS", "BLOCKED_UNSUPPORTED"}
)


def classify_intake(entry: ProductEntry, backend: StateBackend) -> ProofStageReceiptV1:
    """Run (or resume, via the existing intake dedup key) one repository's read-only intake
    preflight and translate its outcome into an INTAKE/TERMINAL_SKIPPED/BLOCKED_INPUT/
    SYSTEM_FAILURE proof-stage receipt."""

    started = time.monotonic()
    try:
        execution = run_readonly_intake_preflight(entry, backend)
    except Exception as exc:  # noqa: BLE001 -- classify the failure, never crash the pass
        return ProofStageReceiptV1(
            org_repo=entry.org_repo,
            ecosystem=entry.ecosystem,
            contract_hash=intake_contract_hash(entry),
            stage="SYSTEM_FAILURE",
            status="FAILED",
            failure_reason=f"{type(exc).__name__}: {exc}"[:500],
            elapsed_seconds=time.monotonic() - started,
            provider_call_count=0,
        )
    binding = execution.binding
    elapsed = time.monotonic() - started
    outcome = binding.outcome
    stage: ProofStageV1
    status: Literal["OK", "FAILED"]
    reason: str | None
    if outcome in _TERMINAL_SKIP_OUTCOMES:
        stage, status, reason = "TERMINAL_SKIPPED", "OK", None
    elif outcome in _BLOCKED_INPUT_OUTCOMES:
        stage, status, reason = "BLOCKED_INPUT", "FAILED", binding.reason[:500]
    elif outcome == "SYSTEM_FAILURE":
        stage, status, reason = "SYSTEM_FAILURE", "FAILED", binding.reason[:500]
    else:
        stage, status, reason = "INTAKE", "OK", None
    return ProofStageReceiptV1(
        org_repo=entry.org_repo,
        ecosystem=entry.ecosystem,
        source_revision=(binding.source_revision if binding.source_revision_resolved else None),
        contract_hash=intake_contract_hash(entry),
        stage=stage,
        status=status,
        failure_reason=reason,
        elapsed_seconds=elapsed,
        provider_call_count=0,
    )
