"""Two-phase effect ledger (Wave 5, `EFF-002`/`EFF-003`) -- dispatch-tier,
matching decision #26's own phrase "Wave 5's dispatcher-retry-wrapper work":
any future caller of `dispatch_tool_call` gets this, not just the Wave 5
supervisor.

Wraps `dispatch_tool_call()` unchanged (imported, not modified) around a
durable pending/applied record so a process killed mid-effect leaves a
`pending` trace behind, and a resumed run does not blindly re-apply.

Deliberately does NOT reuse `plans/investigations/capability-dispatch-production-readiness.md`'s
original proposal of writing the intent record to local evidence-dir JSON
(`runs/evidence/{run_id}/effect_intents/...`) -- that is exactly the storage
Wave 4 built `GitStateBackend` to stop depending on. A pending record in a
local file would be lost on the precise "runner dies mid-effect, retried on
a fresh runner" scenario this ledger exists to survive. The record lives in
the same durable backend `state/domain_state.py::save_domain()` already
proved live, under the same per-repo lock (`MEM-002`).
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, cast

from readme_agent.authorization import registry as authorization_registry
from readme_agent.authorization.schema import EffectClass
from readme_agent.capabilities import registry
from readme_agent.capabilities.dispatcher import DispatchResult, dispatch_tool_call
from readme_agent.capabilities.effect_identity import build_effect_identity
from readme_agent.capabilities.schema import CapabilityManifest, PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.state.backend import StateBackend, safe_release_lock
from readme_agent.state.schema import CapabilityOutputCacheEntry, RunStateV1

# side_effect_class values at or above this index require going through this
# ledger rather than plain dispatch_tool_call() -- matches registry.py's own
# _MUTATING_PERMISSION_CLASSES threshold.
_MUTATING_PERMISSION_CLASSES = ("local_write", "remote_write")

GatedOutcome = Literal[
    "dispatched",  # proceeded to a real dispatch_tool_call(); check .dispatch.outcome for the
    # actual result -- this does NOT mean the effect succeeded, only that the ledger allowed
    # the attempt.
    "already_applied",
    "blocked_pending_reconciliation",
    # Wave 13.3 (`AUTH-004`): a capability declaring one or more
    # `effect_classes` has no authorization record covering all of them for
    # this org_repo -- checked before any pending entry is written, same
    # positioning/rationale as a rejecting precheck() below.
    "blocked_pending_authorization",
]


@dataclass
class GatedDispatchResult:
    outcome: GatedOutcome
    dispatch: DispatchResult | None = None
    cached_result: dict | None = None
    detail: str | None = None


def idempotency_key(capability_id: str, arguments: dict, idempotency_inputs: list[str]) -> str:
    """Deterministic hash of `(capability_id, idempotency_inputs-selected
    argument fields)` -- directly analogous to `facts_hash` (decision #11):
    same inputs -> same key -> same decision about whether to act again.
    Only the *declared* fields participate (`idempotency_inputs`, already a
    manifest field), never every argument -- a documented per-case choice,
    same as `facts_hash`'s deliberate exclusion of `gap_report`.

    Wave 9.6 (`EFF-006`): when `final_text` is one of the declared
    `idempotency_inputs` -- today only `commit_readme_write`/
    `open_presentation_pr` -- the key is built from a typed
    `EffectIdentityV1` (`effect_identity.py`) instead of the plain per-field
    dict below, so the *rendered candidate's own bytes*
    (`candidate_byte_hash = sha256(final_text)`), not just the pre-render
    upstream baseline (`fresh_fingerprint`), participate in the hash. This
    fixes the confirmed live bug where two different generated candidates
    against an unchanged upstream collided on one key -- see
    `effect_identity.py`'s own docstring for the full trace."""
    if "final_text" in idempotency_inputs:
        identity = build_effect_identity(
            effect_type=capability_id,
            org_repo=arguments.get("org_repo", ""),
            facts_hash=arguments.get("facts_hash", ""),
            fresh_fingerprint=arguments.get("fresh_fingerprint", ""),
            final_text=arguments.get("final_text", ""),
        )
        return hashlib.sha256(identity.canonical_json().encode()).hexdigest()
    selected = {name: arguments.get(name) for name in sorted(idempotency_inputs)}
    canonical = json.dumps(selected, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{capability_id}:{canonical}".encode()).hexdigest()


def retry_is_safe(manifest: CapabilityManifest) -> bool:
    """`EFF-003`: retry is structurally inert for any capability at
    `side_effect_class >= local_write` unless it declares
    `retry_policy="idempotent_only"`. Read-only capabilities are always
    safe to retry (re-observing reality has no side effect)."""
    if manifest.side_effect_class not in _MUTATING_PERMISSION_CLASSES:
        return True
    return manifest.retry_policy == "idempotent_only"


def _find_entry(state: RunStateV1, key: str) -> CapabilityOutputCacheEntry | None:
    for entry in state.capability_outputs:
        if entry.fingerprint == key:
            return entry
    return None


def _save_entry_with_retry(
    backend: StateBackend,
    org_repo: str,
    entry: CapabilityOutputCacheEntry,
    *,
    max_retries: int = 5,
) -> None:
    """Load -> patch only this entry (by `fingerprint`) onto a *freshly
    reloaded* copy -> `save(expected_version=fresh.state_version)` -> on
    `stale`, reload and retry, bounded. Mirrors `save_domain()`'s exact
    shape (`state/domain_state.py`) so a concurrent writer's own entry is
    always carried forward, never overwritten by a stale retry -- re-reading
    `current` on *every* attempt, not just the first, is what makes that
    true."""
    for _ in range(max_retries):
        current = backend.load(org_repo)
        expected_version = current.state_version if current is not None else None
        base = current if current is not None else RunStateV1(org_repo=org_repo)
        without = [e for e in base.capability_outputs if e.fingerprint != entry.fingerprint]
        updated = base.model_copy(update={"capability_outputs": [*without, entry]})
        result = backend.save(org_repo, updated, expected_version)
        if result.outcome != "stale":
            return
    raise StateBackendError(
        f"effect ledger save for {org_repo!r}/{entry.fingerprint!r} did not converge "
        f"after {max_retries} retries"
    )


def dispatch_gated_effect(
    tool_call: dict,
    allowed_permissions: set[PermissionClass],
    backend: StateBackend,
    org_repo: str,
    caller_domain: str | None = None,
    *,
    max_retries: int = 5,
) -> GatedDispatchResult:
    """The `EFF-002` two-phase apply, composed around `dispatch_tool_call()`
    -- that function's own gates (unknown capability, permission, domain,
    argument validation) are untouched and run first, inside the executed
    branch below, so a request that would be rejected for any of those
    reasons is rejected exactly as it always was, without ever touching the
    ledger.

    Lock is lock-primary (`MEM-002`, mirrors `save_domain()`): held for the
    entire pending-write -> execute -> applied-write sequence, not just the
    individual saves, so no other writer can interleave a conflicting
    pending record for the same idempotency key while this one is in
    flight. `state_version` CAS is the backstop for the lease-expiry edge
    case, same two-layer discipline `save_domain()` already established."""
    function = tool_call.get("function", {})
    capability_id = function.get("name")
    manifest = registry.get(capability_id)
    if manifest is None or manifest.side_effect_class not in _MUTATING_PERMISSION_CLASSES:
        # Not a gated effect at all -- plain dispatch, the ledger has nothing to add.
        return GatedDispatchResult(
            outcome="dispatched",
            dispatch=dispatch_tool_call(
                tool_call, allowed_permissions, caller_domain, state_backend=backend
            ),
        )

    raw_arguments = function.get("arguments")
    try:
        arguments = (
            json.loads(raw_arguments) if isinstance(raw_arguments, str) else (raw_arguments or {})
        )
    except json.JSONDecodeError:
        arguments = {}

    # Wave 13.3 (`AUTH-004`, authorization enforcement cutover): checked
    # first, ahead of precheck() below -- "is this action authorized at
    # all" is a more fundamental gate than "is this specific call's payload
    # valid," and both must run before the lock is acquired or any pending
    # entry is written (same cheap, side-effect-free rationale as precheck()
    # itself). Only a capability that actually declares `effect_classes`
    # (today: only `open_presentation_pr`) is affected -- an empty list
    # (every other capability's default) is a no-op here, unchanged from
    # before this wave. `authorization_dir` is passed explicitly, re-reading
    # the module attribute at call time, so a test can monkeypatch
    # `authorization_registry.AUTHORIZATION_DIR` and have it actually take
    # effect (its own bound-default parameter, evaluated once at import
    # time, would not see a later monkeypatch -- the same hazard already
    # found and fixed once in `commands.py::cmd_authorization_validate`).
    unauthorized_effect_classes = [
        effect_class
        for effect_class in manifest.effect_classes
        if authorization_registry.authorized_for(
            org_repo,
            cast(EffectClass, effect_class),
            authorization_dir=authorization_registry.AUTHORIZATION_DIR,
        )
        is None
    ]
    if unauthorized_effect_classes:
        return GatedDispatchResult(
            outcome="blocked_pending_authorization",
            detail=(
                f"{org_repo!r} has no authorization record covering "
                f"{unauthorized_effect_classes!r} for capability {capability_id!r} -- "
                "AUTH-004: no capability may infer authorization from mode == 'full' alone"
            ),
        )

    # Wave 8 (production-reliability pass): checked BEFORE the lock/pending
    # write below, not after -- a cheap, side-effect-free rejection here
    # never touches the ledger at all. Found by direct trace: every one of
    # `dispatch_tool_call()`'s own checks (unknown capability, permission
    # denied, domain denied, missing argument) already ran *after* a pending
    # entry was written, meaning any caller-side mistake -- not just this new
    # precondition class -- has the exact same signature as a genuine
    # crash-mid-effect and permanently jams that idempotency key behind
    # `blocked_pending_reconciliation`, since `reconciliation_check()` can
    # only confirm "did it land," never "should this have been attempted at
    # all." `precheck()` exists specifically so a capability-declared
    # precondition (e.g. `commit_readme_write`'s `verification_verdict`)
    # fails cheaply instead.
    precheck = registry.get_precheck(capability_id)
    if precheck is not None:
        rejection_reason = precheck(arguments)
        if rejection_reason is not None:
            return GatedDispatchResult(
                outcome="dispatched",
                dispatch=DispatchResult(
                    outcome="rejected_precondition_failed", error=rejection_reason
                ),
            )

    key = idempotency_key(capability_id, arguments, manifest.idempotency_inputs)

    lock = backend.acquire_lock(org_repo)
    if lock is None:
        return GatedDispatchResult(
            outcome="blocked_pending_reconciliation",
            detail=f"could not acquire lock for {org_repo!r}",
        )
    try:
        current = backend.load(org_repo) or RunStateV1(org_repo=org_repo)
        existing = _find_entry(current, key)

        if existing is not None and existing.status == "applied":
            return GatedDispatchResult(outcome="already_applied", cached_result=existing.result)

        if existing is not None and existing.status == "pending":
            # A prior attempt started and never finished -- the actual crash
            # signature EFF-002 exists to catch. Note this fires regardless
            # of retry_policy -- "did the effect land" is genuinely unknown
            # here, which is a strictly stronger reason to refuse than
            # retry_policy alone would be. retry_policy's own enforcement
            # point is one layer up (`supervisor/repair.py::
            # create_repair_task()`, `EFF-003`): whether to even *propose*
            # dispatching this capability+arguments again in the first
            # place, checked before this function is ever called a second
            # time for the same task.
            #
            # Wave 7 (`EFF-001`'s remaining gap): a registered capability MAY
            # answer "does this effect already exist in observable reality?"
            # itself, via `registry.get_reconciliation_check()`. A `dict`
            # result means yes -- backfill the stale `pending` record to
            # `applied` (correcting the ledger's own audit trail) instead of
            # leaving it permanently stuck; a `None` result (or no check
            # registered at all) falls through to the same honest
            # AGT-004 genuine-blocker every capability without a check gets.
            reconciliation_check = registry.get_reconciliation_check(capability_id)
            if reconciliation_check is not None:
                reconciled_result = reconciliation_check(arguments)
                if reconciled_result is not None:
                    applied_entry = CapabilityOutputCacheEntry(
                        capability_id=capability_id,
                        fingerprint=key,
                        result=reconciled_result,
                        status="applied",
                    )
                    _save_entry_with_retry(
                        backend, org_repo, applied_entry, max_retries=max_retries
                    )
                    return GatedDispatchResult(
                        outcome="already_applied", cached_result=reconciled_result
                    )
            return GatedDispatchResult(
                outcome="blocked_pending_reconciliation",
                detail=(
                    f"a prior attempt for {capability_id!r} (key {key[:12]}...) never "
                    "completed and no reconciliation check could confirm it landed -- "
                    "refusing to blindly re-execute"
                ),
            )

        pending_entry = CapabilityOutputCacheEntry(
            capability_id=capability_id, fingerprint=key, result={}, status="pending"
        )
        _save_entry_with_retry(backend, org_repo, pending_entry, max_retries=max_retries)

        dispatch = dispatch_tool_call(
            tool_call, allowed_permissions, caller_domain, state_backend=backend
        )

        lock_loss_detail = None
        if dispatch.outcome == "executed":
            # Decision #46/#48 (`EFF-005`, Phase 13 §13.1's F4 finding): the
            # effector above may have run long enough that another runner
            # legitimately reclaimed this lease while this call believed it
            # still held it -- re-verify by holder identity immediately
            # before the one write that would otherwise assert sole
            # authority over this effect. This does not undo the real side
            # effect the effector already performed (nothing here could);
            # it only decides whether THIS caller may honestly claim
            # exclusive credit for it in the ledger.
            if backend.lock_still_held(lock):
                applied_entry = CapabilityOutputCacheEntry(
                    capability_id=capability_id,
                    fingerprint=key,
                    result=dispatch.result or {},
                    status="applied",
                )
                _save_entry_with_retry(backend, org_repo, applied_entry, max_retries=max_retries)
            else:
                # Leave the pending record exactly as-is -- do NOT write
                # applied. A future dispatch attempt for this same key hits
                # blocked_pending_reconciliation and must go through a real
                # reconciliation_check() before either runner's copy of this
                # effect is trusted, rather than two runners both silently
                # believing they alone applied it.
                lock_loss_detail = (
                    f"lock for {org_repo!r} was reclaimed by another holder before the "
                    f"terminal applied-write for {capability_id!r} (key {key[:12]}...) -- "
                    "effect executed, but NOT recorded as applied; left pending for "
                    "reconciliation_check() to resolve"
                )
        # Any other outcome: the pending record correctly stays pending,
        # reflecting reality -- it is not flipped to applied, and it is not
        # removed. A future call with the same key hits the
        # blocked_pending_reconciliation path above, not a silent retry.

        return GatedDispatchResult(outcome="dispatched", dispatch=dispatch, detail=lock_loss_detail)
    finally:
        safe_release_lock(backend.release_lock, lock, label="lock")
