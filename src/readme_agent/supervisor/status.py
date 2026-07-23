"""Canonical process-exit classification for supervisor terminal states."""

from readme_agent.supervisor.models import SuperviseResult

CONVERGED_STATUSES = frozenset(
    {"CONVERGED_NO_CHANGE", "CONVERGED_APPLIED", "CONVERGED_NO_TRACKED_CHANGE"}
)


def terminal_exit_code(result: SuperviseResult) -> int:
    """Return zero only for an explicitly converged supervisor result."""

    return 0 if result.status in CONVERGED_STATUSES else 1
