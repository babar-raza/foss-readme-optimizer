"""Trigger identity and deduplication (Wave 9.5, `RUN-006`) -- pure caller-side composition of
the existing `StateBackend` load/save/lock primitives, exactly like `domain_state.py::save_domain()`
next to it. No change to `StateBackend`'s own contract or `GitStateBackend`'s mechanics is needed.

This closes the trigger-identity/dedup half of `RUN-006`. The row's full text also asks for a
durable, checkpointed intake *queue* recovering accepted-but-unfinished work after a runner is
lost -- a materially larger undertaking (would need `supervise_repo()`'s own internals
instrumented at every stage, not just entry/exit) that stays open, tracked, not built this pass.
"""

from readme_agent.errors import StateBackendError
from readme_agent.retry import RetryableOperationError, run_with_retry
from readme_agent.state.backend import StateBackend, safe_release_lock
from readme_agent.state.schema import RunStateV1, TriggerRecordV1

# Bounds `RunStateV1.trigger_records`' growth -- the oldest entries (by
# `accepted_at`) are pruned once this many are recorded for one `org_repo`,
# so a long-lived, frequently-triggered repo's state record cannot grow
# unbounded. Generous enough that legitimate dedup windows (a retried
# `workflow_dispatch` within the same day) are never pruned away in practice.
MAX_TRIGGER_RECORDS_PER_REPO = 200


def is_duplicate_trigger(backend: StateBackend, org_repo: str, trigger: TriggerRecordV1) -> bool:
    """True if an equivalent trigger (same `dedup_key()`) was already accepted for this repo --
    checked BEFORE any clone/specialist/planner work starts, so a duplicate event costs one cheap
    state read, not a full re-run."""
    try:
        current = backend.load(org_repo)
    except StateBackendError:
        # Fail-closed callers (a `github_*` execution profile) already refuse to proceed when
        # `state_backend` load fails elsewhere (`commands.py::cmd_supervise()`) -- this function
        # itself stays conservative and reports "not a duplicate" rather than raising, since a
        # dedup check that cannot read state has no basis to claim a match either way; the
        # fail-closed refusal happens at the caller's own explicit gate, not silently in here.
        return False
    if current is None:
        return False
    return trigger.dedup_key() in current.trigger_records


def record_trigger(
    backend: StateBackend,
    org_repo: str,
    trigger: TriggerRecordV1,
    *,
    max_retries: int = 5,
) -> TriggerRecordV1:
    """Records `trigger` as accepted (or, if its `dedup_key()` already exists, returns the
    existing record unchanged with `status="deduplicated"` -- never double-counted). Same
    load -> patch-on-fresh-copy -> CAS-save -> retry-on-stale shape as `save_domain()`."""
    lock = backend.acquire_lock(org_repo)
    if lock is None:
        raise StateBackendError(f"could not acquire lock for {org_repo!r} to record trigger")
    try:

        def attempt() -> TriggerRecordV1:
            current = backend.load(org_repo)
            expected_version = current.state_version if current is not None else None
            base = current if current is not None else RunStateV1(org_repo=org_repo)

            key = trigger.dedup_key()
            existing = base.trigger_records.get(key)
            if existing is not None:
                return existing.model_copy(update={"status": "deduplicated"})

            pruned = dict(base.trigger_records)
            if len(pruned) >= MAX_TRIGGER_RECORDS_PER_REPO:
                oldest_key = min(pruned, key=lambda k: pruned[k].accepted_at)
                del pruned[oldest_key]
            pruned[key] = trigger

            updated = base.model_copy(update={"trigger_records": pruned})
            result = backend.save(org_repo, updated, expected_version)
            if result.outcome == "stale":
                raise RetryableOperationError("legacy trigger CAS was stale")
            if result.outcome == "saved":
                return trigger
            raise StateBackendError(
                f"record_trigger for {org_repo!r} was rejected as {result.outcome!r}"
            )

        try:
            return run_with_retry("state_cas", attempt, max_attempts=max_retries)
        except RetryableOperationError as exc:
            raise StateBackendError(
                f"record_trigger for {org_repo!r} did not converge after {max_retries} retries"
            ) from exc
    finally:
        safe_release_lock(backend.release_lock, lock, label="lock")
