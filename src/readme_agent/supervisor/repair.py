"""Failure classification and repair-task creation (`ORC-002`/`VER-002`).

Kept as plain functions, not a class, so Wave 8's real independent verifier
can later satisfy the same call shape without a rewrite (`VER-001`: a
verifier must be distinct from the author -- this function boundary is
where that swap happens later; Wave 5 does not build the independent-
verifier part itself).
"""

import json
from string import Template
from typing import Literal

from readme_agent.capabilities.dispatcher import DispatchResult
from readme_agent.capabilities.effect_ledger import retry_is_safe
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.errors import LLMError
from readme_agent.llm import prompt_registry
from readme_agent.llm.planner_client import PlannerClient
from readme_agent.supervisor.task import Task, TaskGraph

FailureClass = Literal[
    "dispatch_rejected", "execution_error", "validation_failed", "verification_rejected"
]

# Wave 8.6 (`VER-006` reversal): no operational history yet to justify a
# different value -- mirrors ESCALATION_ALERT_THRESHOLD's/DOSSIER_TOKEN_
# BUDGET's own precedent reasoning. Bounds BOTH the existing blind
# execution_error retry and the new LLM-driven alternative-selection path,
# per-original-failure, via `supervisor/loop.py::_dispatch_and_record()`'s
# own `depth` parameter.
MAX_REPAIR_ATTEMPTS = 2

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


def classify_verification(verdict: dict) -> FailureClass:
    """Maps a verifier's own verdict dict (`{"verdict": "accept"|"reject",
    "reason": ..., ...}`, `verification/schema.py::VerificationVerdictV1`'s
    shape) onto the same `FailureClass` vocabulary `classify_failure()`
    already uses for dispatch-level failures -- `VER-001`'s independent
    verifier plugs into exactly this function boundary, per this module's
    own original docstring. Callers only invoke this once a verdict is
    already known to be a rejection (mirrors `classify_failure()`'s own
    contract: both classify an already-failed outcome, neither is used to
    detect failure in the first place)."""
    assert verdict.get("verdict") == "reject", (
        "classify_verification() called on a non-reject verdict"
    )
    return "verification_rejected"


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


def select_repair_alternative(
    graph: TaskGraph,
    failed_task: Task,
    classification: FailureClass,
    reason: str,
    tools: list[dict],
    planner_client: PlannerClient,
) -> Task | None:
    """Wave 8.6 (`VER-006` reversal): a real, model-driven repair choice,
    consulted only for `dispatch_rejected`/`validation_failed`/
    `verification_rejected` -- `execution_error` keeps `create_repair_
    task()`'s existing cheap, no-LLM blind retry unchanged; there is no
    reason to spend an LLM call picking an "alternative" when a plain retry
    is already the correct, safe fix for a transient failure.

    Reuses the SAME unscoped tool menu (`tools`, `registry.all_tool_
    schemas()`) the main planner already sees -- the model can only ever
    propose a `Task`, never execute anything itself; the proposed
    capability still flows through the exact same dispatcher/permission/
    domain/idempotency checks as any other capability call once the caller
    dispatches it. Returns `None` (escalate -- the same meaning `create_
    repair_task()`'s own `None` already has) on the planner declining to
    call a tool, a malformed response, or any `LLMError` -- fail closed,
    never guess."""
    manifest = prompt_registry.get("repair_capability_selection")
    assert manifest is not None, "prompts/planning/repair_capability_selection.yaml missing"
    assert manifest.user_template is not None

    messages = [
        {"role": "system", "content": manifest.system.strip()},
        {
            "role": "user",
            "content": Template(manifest.user_template)
            .substitute(
                capability_id=failed_task.capability_id or "",
                arguments=json.dumps(failed_task.arguments),
                classification=classification,
                reason=reason,
            )
            .strip(),
        },
    ]

    try:
        plan = planner_client.plan(messages, tools)
    except LLMError:
        return None
    if plan.tool_call is None:
        return None

    function = plan.tool_call.get("function", {})
    capability_id = function.get("name")
    if not capability_id:
        return None
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError:
        return None

    return graph.add_task(
        Task(capability_id=capability_id, arguments=arguments, depends_on=[failed_task.task_id])
    )
