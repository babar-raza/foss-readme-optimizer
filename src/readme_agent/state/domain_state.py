"""Per-domain state writes (`MEM-004`, Decision #34) -- the caller-side
composition a Wave 6+ specialist uses to safely patch its own
`RunStateV1.domain_states[domain]` entry without clobbering another
specialist's already-accepted result in the same `org_repo` record.

No change to `StateBackend.save()`'s signature or `GitStateBackend`'s
whole-blob-replace mechanics is needed for this -- `save_domain()` is pure
caller-side composition of the existing `load()`/`save()`/`acquire_lock()`/
`release_lock()` primitives, exactly as the `StateBackend` Protocol already
allows.

Two layers, in priority order (both matter -- a lease is a timeout, not a
hard mutex):
  1. `acquire_lock`/`release_lock` (`MEM-002`, already live-tested) is the
     *primary* serialization mechanism -- each specialist wraps its whole
     load-patch-save cycle in the lease.
  2. `state_version` compare-and-swap is a correctness *backstop* for the
     lease-expiry edge case (a slow specialist's lease expiring mid-write
     while it's still working) -- always re-patches onto a freshly reloaded
     copy, so another domain's already-accepted result is carried forward
     automatically on retry, never overwritten.
"""

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import SaveResult, StateBackend
from readme_agent.state.schema import DomainStateV1, RunStateV1


def save_domain(
    backend: StateBackend,
    org_repo: str,
    domain: str,
    domain_state: DomainStateV1,
    *,
    max_retries: int = 5,
) -> SaveResult:
    """Load -> patch only `domain_states[domain]` on a freshly reloaded
    copy -> save(expected_version=fresh.state_version) -> on `stale`,
    reload and retry, bounded."""
    lock = backend.acquire_lock(org_repo)
    if lock is None:
        raise StateBackendError(
            f"could not acquire lock for {org_repo!r} to save domain {domain!r}"
        )
    try:
        for _ in range(max_retries):
            current = backend.load(org_repo)
            expected_version = current.state_version if current is not None else None
            base = current if current is not None else RunStateV1(org_repo=org_repo)
            updated = base.model_copy(
                update={"domain_states": {**base.domain_states, domain: domain_state}}
            )
            result = backend.save(org_repo, updated, expected_version)
            if result.outcome != "stale":
                return result
        raise StateBackendError(
            f"save_domain for {org_repo!r}/{domain!r} did not converge after {max_retries} retries"
        )
    finally:
        backend.release_lock(lock)
