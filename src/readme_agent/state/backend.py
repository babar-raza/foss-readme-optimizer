"""Backend-independent durable-state interface (`MEM-003`): the chosen
backend (`state/git_backend.py`) can be evaluated and swapped without
changing callers. `SaveResult`/`Lock` are internal return values, not
serialized contracts -- plain dataclasses, mirroring `validation/result.py`'s
`RuleResult` (contrast `schema.py`'s pydantic `RunStateV1`, which *is*
serialized).
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from readme_agent.state.schema import ModelRouteStatusV1, RunStateV1, RunStateV2

SaveOutcome = Literal["saved", "stale", "lock_held"]


@dataclass
class SaveResult:
    outcome: SaveOutcome
    new_version: int | None


@dataclass
class Lock:
    org_repo: str
    holder_id: str
    leased_until: str


def safe_release_lock(release_fn: Callable[[Lock], None], lock: Lock, *, label: str) -> None:
    """Every `finally: backend.release_lock(lock)` in this codebase (six
    call sites as of Wave 8.6: `domain_state.py` x3, `effect_ledger.py`,
    `supervisor/loop.py` x2) was equally exposed to the same real bug, found
    live 2026-07-22: a genuine, non-stale-lease push failure during release
    (a hung git subprocess, a transient network error) raises inside a
    `finally:` block, which per Python's own semantics *replaces* whatever
    value or exception the corresponding `try` block was already
    returning/raising -- silently discarding an already-successful result
    (in `effect_ledger.py`'s case, evidence of a real write that just
    landed) and surfacing only as an unrelated crash.

    Caught and logged here, once, for every caller: this project's own lock
    design already tolerates "a runner died before releasing" as a normal,
    bounded condition (the lease expires and a later run reclaims it) --
    "released but the push itself failed" is strictly the same risk,
    already accepted, not a new one this introduces."""
    try:
        release_fn(lock)
    except Exception as exc:  # noqa: BLE001 -- see docstring: deliberately broad, never re-raised
        print(
            f"warning: releasing {label} for {lock.org_repo!r} failed, will self-heal "
            f"via lease expiry: {exc}",
            file=sys.stderr,
        )


class StateBackend(Protocol):
    def load(self, org_repo: str) -> RunStateV2 | None: ...

    def save(
        self,
        org_repo: str,
        state: RunStateV1 | RunStateV2,
        expected_version: int | None,
    ) -> SaveResult:
        """CAS: rejected with `outcome="stale"` if the backend's current
        `state_version` no longer matches `expected_version`.
        `expected_version=None` is only valid for the first-ever write to a
        new `org_repo`."""
        ...

    def acquire_lock(self, org_repo: str) -> Lock | None:
        """Per-repository lease (`MEM-002`). `None` means another holder has
        an unexpired lease -- callers must not proceed as if they hold it."""
        ...

    def release_lock(self, lock: Lock) -> None: ...

    def lock_still_held(self, lock: Lock) -> bool:
        """`EFF-005`/Decision #46+47: re-verify, by holder identity (not
        wall-clock alone), that `lock` is still this caller's exclusive
        lease *right now* -- called immediately before a gated effect's
        terminal `applied` write (`effect_ledger.py::dispatch_gated_effect()`),
        closing the window where a slow effector could outlive
        `LOCK_LEASE_SECONDS` and let a second runner legitimately reclaim the
        lease before the first runner's own terminal write lands. `False`
        means someone else now holds (or the lease was released and nothing
        holds) this lock -- the caller must not treat its own effect as the
        sole authoritative one; it should leave any pending ledger record
        exactly as-is rather than mark it `applied`, so a later
        `reconciliation_check()` decides, instead of two runners both
        silently believing they alone applied the effect."""
        ...

    def acquire_run_lock(self, org_repo: str) -> Lock | None:
        """SCL-005 extension (Wave 8.5): a second, coarser, run-scoped lease
        on a different underlying ref than `acquire_lock()` -- covers the
        whole `supervise_repo()` call (specialist tier through the planner
        loop), not just one narrow per-write section. `None` means another
        holder has an unexpired lease -- callers must not proceed as if they
        hold it, same contract as `acquire_lock()`."""
        ...

    def release_run_lock(self, lock: Lock) -> None: ...

    def load_model_route_status(self, job: str) -> ModelRouteStatusV1 | None:
        """Wave 8.6 (`OPS-011` extension): `None` means either no global
        model-route registry exists yet, or `job` has no recorded status --
        both cases mean "enabled" (the permissive default; disablement is
        always an explicit, recorded action, never an absence-based
        inference)."""
        ...

    def save_model_route_status(self, status: ModelRouteStatusV1) -> None:
        """Load-patch-save the global registry's one `job` entry, on a
        freshly-reloaded copy, retrying on CAS conflict -- mirrors `state/
        domain_state.py::save_domain()`'s own shape, one level up (a global
        registry, not a per-`org_repo` record)."""
        ...
