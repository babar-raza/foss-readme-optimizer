"""Finalize one CLI supervision result, its evidence, and trigger lifecycle."""

from __future__ import annotations

import argparse

from readme_agent import paths
from readme_agent.evidence.writer import generate_run_id
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle import LifecycleRecorder, activate_lifecycle
from readme_agent.state.lifecycle_schema import FailureClassificationV1, TriggerStatusV2
from readme_agent.supervisor import evidence as evidence_module
from readme_agent.supervisor.execution_profile import ExecutionProfileV1
from readme_agent.supervisor.models import SuperviseResult


def complete_supervise_command(
    args: argparse.Namespace,
    result: SuperviseResult,
    *,
    profile: ExecutionProfileV1 | None,
    state_backend: StateBackend | None,
    lifecycle_recorder: LifecycleRecorder | None,
) -> int:
    """Write required proof, settle the trigger, print, and expose portfolio state."""

    if profile is not None and profile.require_evidence_bundle and result.evidence_dir is None:
        fallback_run_id = (
            lifecycle_recorder.run_id if lifecycle_recorder is not None else generate_run_id()
        )
        result.evidence_dir = paths.evidence_dir(fallback_run_id)
        with activate_lifecycle(lifecycle_recorder):
            evidence_module.write_supervise_evidence(
                result.evidence_dir,
                fallback_run_id,
                args.repo,
                result.status,
                result.task_graph,
                result.decisions,
            )
        evidence_module.assert_evidence_complete(result.evidence_dir)

    lifecycle_status: TriggerStatusV2 | None = None
    if lifecycle_recorder is not None:
        if state_backend is None:
            raise RuntimeError("a durable lifecycle recorder requires its state backend")
        failure_classification: FailureClassificationV1 | None = None
        failure_detail: str | None = result.status
        if result.status == "BLOCKED":
            if result.blocked_category == "agent_fixable":
                lifecycle_status = "retryable"
                failure_classification = "validation_failed"
            else:
                transient = bool(
                    result.blocked_reason
                    and (
                        result.blocked_reason.startswith("baseline_clone_failed:")
                        or result.blocked_reason.startswith("planner_llm_failure:")
                        or result.blocked_reason == "readonly_intake:BLOCKED_ACCESS"
                        or result.blocked_reason in {"lock_held", "run_lock_held"}
                    )
                )
                if transient:
                    lifecycle_status = "retryable"
                    failure_classification = "transient"
                else:
                    failure_classification = (
                        "unsupported"
                        if result.blocked_reason
                        and (
                            result.blocked_reason.startswith("unsupported_ecosystem:")
                            or result.blocked_reason == "not_onboarded"
                        )
                        else "validation_failed"
                    )
                    lifecycle_status = "blocked"
            failure_detail = result.blocked_reason
        else:
            lifecycle_status = "completed"

        if lifecycle_status in {"blocked", "completed"}:
            lifecycle_recorder.checkpoint_final_acceptance(
                lifecycle_status,
                detail=failure_detail,
                failure_classification=failure_classification,
            )
        try:
            if result.evidence_dir is None:
                raise RuntimeError(
                    "GitHub execution profile did not produce a terminal evidence bundle"
                )
            evidence_module.finalize_run_manifest_v3(
                result.evidence_dir,
                lifecycle_recorder,
                lifecycle_status,
            )
            evidence_module.assert_evidence_complete(result.evidence_dir)
        except Exception as exc:
            from readme_agent.state.lifecycle import transition_trigger

            transition_trigger(
                state_backend,
                args.repo,
                lifecycle_recorder.envelope.dedup_key,
                "retryable",
                failure_classification="validation_failed",
                failure_detail=f"terminal_evidence_failure:{type(exc).__name__}",
            )
            raise
        lifecycle_recorder.transition(
            lifecycle_status,
            detail=failure_detail,
            failure_classification=failure_classification,
        )

    from readme_agent.llm.call_ledger import current_llm_accounting_summary

    llm_summary = current_llm_accounting_summary()
    print(
        f"{args.repo}: {result.status}"
        + (
            f" ({result.blocked_reason}; category={result.blocked_category})"
            if result.blocked_reason
            else ""
        )
        + (
            f" [llm_accounting={llm_summary.status}; "
            f"provider_calls={llm_summary.provider_call_count}; "
            f"cache_reuse={llm_summary.cache_reuse_count}]"
        )
    )
    for decision in result.decisions:
        print(f"  [{decision.turn}] {decision.kind}: {decision.detail}")

    from readme_agent.supervisor.status import terminal_exit_code

    args._terminal_supervise_result = result
    args._llm_accounting_summary = llm_summary
    return terminal_exit_code(result)
