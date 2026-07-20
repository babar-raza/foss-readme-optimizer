"""Failure classification and repair-task creation (`ORC-002`/`VER-002`).

Kept as plain functions, not a class, so Wave 8's real independent verifier
can later satisfy the same call shape without a rewrite (`VER-001`: a
verifier must be distinct from the author -- this function boundary is
where that swap happens later; Wave 5 does not build the independent-
verifier part itself).
"""

from typing import Literal

from readme_agent.capabilities.dispatcher import DispatchResult
from readme_agent.capabilities.effect_ledger import retry_is_safe
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.supervisor.task import Task, TaskGraph

FailureClass = Literal["dispatch_rejected", "execution_error", "validation_failed"]

_REJECTED_OUTCOMES = frozenset(
    {
        "rejected_unknown_capability",
        "rejected_permission_denied",
        "rejected_domain_denied",
        "rejected_invalid_arguments",
    }
)


def classify_failure(dispatch_result: DispatchResult) -> FailureClass:
    """Maps `dispatcher.Outcome` onto the three classes `ORC-002`/`VER-002`
    reason about. `"validation_failed"` is reachable once a capability
    declares `validators` and the loop checks them post-execution -- none of
    today's four do, so it's forward-looking, not yet organically reachable."""
    if dispatch_result.outcome in _REJECTED_OUTCOMES:
        return "dispatch_rejected"
    return "execution_error"


def create_repair_task(
    graph: TaskGraph,
    failed_task: Task,
    classification: FailureClass,
    manifest: CapabilityManifest | None,
) -> Task | None:
    """`None` means "no automatic repair -- escalate to `BLOCKED`", not
    "nothing happened": the caller (`supervisor/loop.py`) marks
    `failed_task` `BLOCKED` with a reason in that case. A real repair task
    (same capability, same arguments, `depends_on=[failed_task.task_id]`) is
    only ever proposed for `execution_error` when the manifest declares
    `retry_policy="idempotent_only"` (`EFF-003` -- retry must never be a
    guess). `dispatch_rejected` (permission/domain-denied, unknown
    capability, malformed arguments) is never auto-repaired: those are
    genuine blockers/gaps, not transient failures a blind retry could fix.
    `validation_failed` is also never auto-repaired here -- picking a
    genuinely different strategy needs the planner's next turn, not a
    scripted guess; the failure is fed back into the planning conversation
    instead (`supervisor/loop.py`), same as any other observation."""
    if classification != "execution_error":
        return None
    if manifest is None or not retry_is_safe(manifest):
        return None

    return graph.add_task(
        Task(
            capability_id=failed_task.capability_id,
            arguments=failed_task.arguments,
            depends_on=[failed_task.task_id],
        )
    )
