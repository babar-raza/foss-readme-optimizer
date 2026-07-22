"""Wave 8.6 (`OPS-011`): the two metrics OPS-011's own acceptance text says
need NO new instrumentation -- both already durable in `SupervisorStateV1`
(`capability_gaps`, `repair_history`), written by every real `supervise_repo()`
call today. Reads across the enabled portfolio's already-recorded state;
never dispatches anything, never mutates anything."""

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend


def aggregate_production_metrics(state_backend: StateBackend, org_repos: list[str]) -> dict:
    hallucinated_capability_count = 0
    repair_attempts = 0
    repair_alternatives_selected = 0
    repair_escalated = 0
    repos_with_state = 0

    for org_repo in org_repos:
        try:
            state = state_backend.load(org_repo)
        except StateBackendError:
            continue
        if state is None or state.supervisor_state is None:
            continue
        repos_with_state += 1
        supervisor_state = state.supervisor_state
        hallucinated_capability_count += len(supervisor_state.capability_gaps)
        for entry in supervisor_state.repair_history:
            repair_attempts += 1
            if entry.get("kind") == "repair_alternative_selected":
                repair_alternatives_selected += 1
            elif entry.get("kind") == "repair_escalated":
                repair_escalated += 1

    return {
        "repos_with_state": repos_with_state,
        "hallucinated_capability_count": hallucinated_capability_count,
        "repair_attempts": repair_attempts,
        "repair_alternatives_selected": repair_alternatives_selected,
        "repair_escalated": repair_escalated,
    }
