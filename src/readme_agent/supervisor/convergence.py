"""Convergence / stop-condition logic (`AGT-004`): "MUST NOT stop on an
arbitrary global iteration limit; it stops only on defined convergence,
safe-proposal, missing-permission, or genuine-blocker conditions." Honestly
scoped to what Wave 5's actual capability surface (four read-only
capabilities, no mutation registered yet) can produce -- see
`plans/foamy-brewing-moonbeam.md`'s "Convergence" section for the full
reasoning this module implements.

`TaskGraph.is_converged()` (all current tasks terminal) is *not* by itself a
stop signal: it is trivially true after any single synchronous dispatch,
before the planner has ever been asked whether more work is worth
discovering. The real stop signal is the planner's own explicit turn with no
tool call (found live, via a smoke test: an earlier design checked
`is_converged()` at the top of every turn and stopped after the bootstrap
observation alone, never consulting the planner at all). This module
therefore splits into two independent checks: `check_repair_exhausted()`
(a bug-detector bound, evaluated every turn) and `final_status()` (classifies
the ending state, called only once the loop has actually stopped).
"""

from dataclasses import dataclass
from typing import Literal

from readme_agent.supervisor.task import TaskGraph

SuperviseStatus = Literal[
    "CONVERGED_NO_CHANGE",
    "CONVERGED_APPLIED",
    "PARTIAL_WITH_CAPABILITY_GAP",
    "BLOCKED",
    # Wave 6 (decision #39): the coarse `is_fresh()` check below found the
    # upstream commit had moved, but every registered specialist domain's
    # fine-grained classification came back NO_CHANGE (nothing tracked --
    # README/community files -- actually changed). Constructed directly in
    # `loop.py::supervise_repo()`, not via `final_status()` -- listed here
    # for the status vocabulary's own documentation completeness.
    "CONVERGED_NO_TRACKED_CHANGE",
]


@dataclass
class ConvergenceOutcome:
    status: SuperviseStatus
    blocked_reason: str | None = None


def is_fresh(recorded_revision: str | None, current_revision: str | None) -> bool:
    """The cheap pre-planning freshness check (`VER-003`): if the durable
    record's last-observed upstream revision equals the baseline clone's
    current HEAD, nothing has changed since the last converged run -- skip
    planning entirely. One clone-HEAD comparison, not a `facts_hash`
    recomputation (that's `generate_repo()`-specific and not meaningful
    without a capability that renders something)."""
    return (
        recorded_revision is not None
        and current_revision is not None
        and recorded_revision == current_revision
    )


def check_repair_exhausted(turns_taken: int, max_turns: int) -> ConvergenceOutcome | None:
    """A **bug detector**, not the normal stop path: if the loop is still
    going after `max_turns`, that is itself evidence of a stuck planner (a
    genuine-blocker condition, `AGT-004`'s own wording), recorded as a
    distinct `BLOCKED` reason -- never a silent, arbitrary stop."""
    if turns_taken >= max_turns:
        return ConvergenceOutcome(status="BLOCKED", blocked_reason="repair_exhausted")
    return None


def final_status(graph: TaskGraph, *, applied_any_effect: bool) -> ConvergenceOutcome:
    """Classifies the graph's ending state once the loop has actually
    stopped (the planner's own explicit turn with no tool call, or
    `check_repair_exhausted()` firing). Never called mid-loop to decide
    *whether* to stop -- only to decide *what happened* once it has."""
    blocked = [t for t in graph.tasks.values() if t.state == "BLOCKED"]
    if blocked:
        has_gap = any(t.gap is not None for t in blocked)
        if has_gap and any(t.state == "PASSED" for t in graph.tasks.values()):
            # GAP-001's "continue independent supported work": at least one
            # branch genuinely converged despite the gap.
            return ConvergenceOutcome(status="PARTIAL_WITH_CAPABILITY_GAP")
        return ConvergenceOutcome(
            status="BLOCKED", blocked_reason=blocked[0].blocked_reason or "blocked"
        )

    return ConvergenceOutcome(
        status="CONVERGED_APPLIED" if applied_any_effect else "CONVERGED_NO_CHANGE"
    )
