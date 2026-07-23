"""Shared bounded compare-and-swap state updates."""

from __future__ import annotations

from collections.abc import Callable

from readme_agent.errors import StateBackendError
from readme_agent.retry import RETRY_POLICIES, RetryableOperationError, run_with_retry
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import RunStateV2

StatePatch = Callable[[RunStateV2], RunStateV2]


def load_required_state(backend: StateBackend, org_repo: str) -> RunStateV2:
    state = backend.load(org_repo)
    if state is None:
        raise StateBackendError(f"durable lifecycle state for {org_repo!r} disappeared")
    return state


def save_state_patch(
    backend: StateBackend,
    org_repo: str,
    patch: StatePatch,
    *,
    max_retries: int = RETRY_POLICIES["state_cas"].max_attempts,
) -> RunStateV2:
    """Apply one fresh-state patch under the shared bounded CAS policy."""

    def attempt() -> RunStateV2:
        current = backend.load(org_repo)
        expected_version = current.state_version if current is not None else None
        base = current or RunStateV2(org_repo=org_repo)
        updated = patch(base)
        result = backend.save(org_repo, updated, expected_version)
        if result.outcome == "saved":
            return updated.model_copy(update={"state_version": result.new_version or 0})
        if result.outcome == "stale":
            raise RetryableOperationError(
                f"lifecycle CAS for {org_repo!r} observed a stale version"
            )
        raise StateBackendError(
            f"lifecycle save for {org_repo!r} was rejected as {result.outcome!r}"
        )

    try:
        return run_with_retry("state_cas", attempt, max_attempts=max_retries)
    except RetryableOperationError as exc:
        raise StateBackendError(
            f"lifecycle save for {org_repo!r} did not converge after {max_retries} attempts"
        ) from exc
