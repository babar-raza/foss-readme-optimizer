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

import sys
from datetime import UTC, datetime

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import SaveResult, StateBackend, safe_release_lock
from readme_agent.state.schema import DomainStateV1, RunStateV1, SupervisorStateV1

# Reasons that recur by design, forever, for structurally out-of-scope repos
# -- e.g. a `mode: "disabled"` registry entry with no `policy_profile`
# configured (confirmed by direct inspection of `data/products.json`: 22/25
# entries), which makes `get_product_facts`-dependent domains `ERROR` every
# run, permanently, by design, not as a genuine unexplained failure. Data,
# not a special-cased `if` inside `record_failure_or_reset()` itself -- a
# future carve-out is a one-line addition here.
#
# `disabled_mode` found live (Wave 8e full-registry pass, 2026-07-21):
# `readme_presentation`'s own `require_permitted()` call raises `NotAllowlistedError`
# for every one of the 22 `mode: "disabled"` entries -- a *different* message
# than `missing_policy_profile`'s ValueError, so it fell through the existing
# carve-out uncaught. Confirmed via live evidence: `consecutive_failure_count`
# reached 2 (of the threshold-3 `escalation_alert`) for a `mode: "disabled"`
# repo across two real consecutive runs this session, one run away from a
# false alarm on all 22 disabled entries simultaneously -- the exact failure
# mode this carve-out mechanism exists to prevent, just for a different real
# error class than the one first anticipated.
NON_ESCALATING_FAILURE_REASONS: frozenset[str] = frozenset(
    {"missing_policy_profile", "disabled_mode"}
)


def merge_details(state: DomainStateV1, **updates: object) -> dict:
    """Every specialist node that returns a `details` update MUST build it
    via this helper, never a bare `{"details": {...}}` return.

    `DomainStateV1.details` has no LangGraph merge reducer -- a plain,
    un-annotated `dict` field -- so a `StateGraph(DomainStateV1)` node's
    returned `details` dict fully REPLACES the field; it does not merge.
    Invisible with today's two-or-three-node specialist graphs (at most one
    node writes a `details` key before the next reads it), but a real,
    silent-crash-on-every-run hazard the moment three or more sequential
    nodes each need to see accumulating keys -- found during Wave 8 design
    (external adversarial review): a naively-written verify node inserted
    between `render` and `commit` in `specialists/readme_presentation.py`
    would have erased `render_result` before `_commit_node`'s own `assert
    render_result is not None` runs, on the accept path, on every run.

    Deliberately a helper function, not a blanket `Annotated[dict, reducer]`
    schema change -- that would make `details` accumulate silently across an
    entire run for every specialist, including large transient payloads
    (e.g. `render_result`'s full candidate text) that are deliberately not
    meant to survive into the durably-persisted record. This preserves that
    drop-by-omission behavior for callers that don't opt in, while giving
    the one sequence that needs an intermediate value passed forward an
    explicit, tested way to do it."""
    return {**state.details, **updates}


def record_failure_or_reset(
    prior_count: int, prior_reason: str | None, current_reason: str | None
) -> tuple[int, str | None]:
    """`VER-002`/production-reliability pass: distinguishes "this failed
    once" from "this has failed identically N times in a row and nothing is
    fixing it" -- nothing in this codebase bounded *repeated* failures
    across reruns before this (`check_repair_exhausted()` only bounds turns
    *within* one run). `current_reason` is a caller-supplied, already-
    normalized reason key (e.g. `"verification_rejected"`,
    `"missing_policy_profile"`) -- never a raw exception message, which can
    carry volatile detail (a hash, a timestamp) that would never compare
    equal twice even for the exact same underlying problem.

    `current_reason is None` means success/no-error this run -> resets to
    `(0, None)`. A reason in `NON_ESCALATING_FAILURE_REASONS` always reports
    `(0, current_reason)` -- a stable, expected, permanent condition, never
    an escalating alarm. Otherwise: the same reason as last time increments;
    a differing reason (or the first-ever failure) restarts the count at 1."""
    if current_reason is None:
        return 0, None
    if current_reason in NON_ESCALATING_FAILURE_REASONS:
        return 0, current_reason
    if current_reason == prior_reason:
        return prior_count + 1, current_reason
    return 1, current_reason


def save_domain(
    backend: StateBackend,
    org_repo: str,
    domain: str,
    domain_state: DomainStateV1,
    *,
    current_revision: str | None = None,
    max_retries: int = 5,
) -> SaveResult:
    """Load -> patch only `domain_states[domain]` on a freshly reloaded
    copy -> save(expected_version=fresh.state_version) -> on `stale`,
    reload and retry, bounded.

    `current_revision` (Wave 8.6, `ORC-003` reversal prerequisite): every
    caller reaching this function already only does so on a genuine accept
    (guarded by `not accepted_status.startswith("ERROR:")`), so stamping
    `upstream_revision_at_accept` here -- rather than after `run_domain()`
    returns -- is the one place that survives durable persistence (the
    reverse order would be "trivially complete by construction," the exact
    mistake `domain_coverage_complete`'s own presence-only check made once
    already). Also resets a domain's skip streak: a real accept means this
    domain was NOT skipped this run, regardless of what produced it."""
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
            stamped_state = (
                domain_state.model_copy(
                    update={
                        "upstream_revision_at_accept": current_revision,
                        "skipped_this_run": False,
                        "consecutive_skip_count": 0,
                    }
                )
                if current_revision is not None
                else domain_state
            )
            updated = base.model_copy(
                update={"domain_states": {**base.domain_states, domain: stamped_state}}
            )
            result = backend.save(org_repo, updated, expected_version)
            if result.outcome != "stale":
                return result
        raise StateBackendError(
            f"save_domain for {org_repo!r}/{domain!r} did not converge after {max_retries} retries"
        )
    finally:
        safe_release_lock(backend.release_lock, lock, label="lock")


def _classify_error_reason(accepted_status: str) -> str:
    """Extract a stable reason key from an `"ERROR:"`-prefixed
    `accepted_status` -- never the full message, which can carry volatile
    detail (a hash, a timestamp) that would never compare equal twice even
    for the identical underlying problem. A known, permanent, config-driven
    condition (a missing `policy_profile`, confirmed by direct inspection of
    `data/products.json`: 22/25 real registry entries) is recognized by
    content, not just the `"ERROR:"` prefix's own outcome-class segment, so
    it reliably matches `NON_ESCALATING_FAILURE_REASONS` regardless of which
    capability/domain produced it.

    `"with an enabled mode"` (found live, Wave 8e, 2026-07-21) is `orchestrator.
    require_permitted()`'s own exact, distinguishing wording -- unlike `require_
    listed()`'s "is not in data/products.json" (no mode mention at all), which
    fires for a genuinely-unlisted repo the supervisor's own upstream entry gate
    would already have hard-rejected long before any specialist runs. By the
    time a specialist's own `require_permitted()` call raises this exact
    message, the repo is confirmed listed (already past that earlier gate) --
    the only remaining reason left is `mode == "disabled"`, a known, permanent,
    config-driven condition for 22/25 real registry entries, the same class of
    non-escalating steady state `missing_policy_profile` already is."""
    if "policy_profile" in accepted_status:
        return "missing_policy_profile"
    if "with an enabled mode" in accepted_status:
        return "disabled_mode"
    parts = accepted_status.split(":", 2)
    return parts[1] if len(parts) > 1 else accepted_status


def _next_domain_state_with_failure_tracking(
    base: RunStateV1,
    domain: str,
    domain_state: DomainStateV1,
    *,
    current_revision: str | None = None,
) -> DomainStateV1:
    """The per-domain patch logic shared by `save_domain_with_failure_
    tracking()` (one domain, its own retry loop) and `merge_unrecorded_
    failures()` (potentially several domains, folded into a caller's own
    already-in-flight `RunStateV1`) -- one rule, two call shapes, not two
    copies of the escalation bookkeeping.

    `current_revision` (Wave 8.6): stamped into `upstream_revision_at_accept`
    only on the real-accept branch -- the error branch deliberately never
    touches it, preserving the existing "never persist a bad baseline"
    guarantee. Both branches reset a domain's skip streak: an error is a
    real attempt, not a skip."""
    prior_domain_state = base.domain_states.get(domain)
    prior_count = prior_domain_state.consecutive_failure_count if prior_domain_state else 0
    prior_reason = prior_domain_state.last_failure_reason if prior_domain_state else None

    accepted_status = domain_state.accepted_status or ""
    is_error = accepted_status.startswith("ERROR:")
    current_reason = _classify_error_reason(accepted_status) if is_error else None
    new_count, new_reason = record_failure_or_reset(prior_count, prior_reason, current_reason)
    escalation_update = {
        "consecutive_failure_count": new_count,
        "last_failure_reason": new_reason,
    }

    if is_error:
        return (prior_domain_state or DomainStateV1(domain=domain)).model_copy(
            update={
                **escalation_update,
                "last_run_timestamp": domain_state.last_run_timestamp,
                "skipped_this_run": False,
                "consecutive_skip_count": 0,
            }
        )
    stamp_update = (
        {
            "upstream_revision_at_accept": current_revision,
            "skipped_this_run": False,
            "consecutive_skip_count": 0,
        }
        if current_revision is not None
        else {}
    )
    return domain_state.model_copy(update={**escalation_update, **stamp_update})


def save_domain_with_failure_tracking(
    backend: StateBackend,
    org_repo: str,
    domain: str,
    domain_state: DomainStateV1,
    *,
    current_revision: str | None = None,
    max_retries: int = 5,
) -> SaveResult:
    """Like `save_domain()`, but ALSO persists `consecutive_failure_count`/
    `last_failure_reason` even when `domain_state.accepted_status` is
    `"ERROR:"`-prefixed -- preserving the existing "never persist a bad
    baseline" guarantee (`accepted_facts_hash`/`accepted_status`/`details`
    stay at their last-good values on a failure), while still recording
    that a failure happened and how many times in a row. `VER-002`/
    "repair loops": without this, a repeated identical failure looks
    identical to ordinary one-off noise in evidence, forever, since nothing
    else in this codebase bounds *repeated* failures across reruns
    (`check_repair_exhausted()` only bounds turns *within* one run).

    Callers replace their own `if not (...).startswith("ERROR:"): save_
    domain(...)` guard with an unconditional call to this function instead.
    Wired into `specialists/readme_presentation.py`'s own record node -- the
    one domain with a real write, so it always self-persists immediately.
    The other eight specialists still use the plain `save_domain()` guard-
    and-skip convention on success (unchanged, `VER-005` confirmed this must
    stay immediate so same-run siblings can read a fresh result); their own
    unrecorded *failures* are instead folded into the supervisor's own
    existing end-of-run write via `merge_unrecorded_failures()` below, not
    retrofitted onto this same per-domain-lock-cycle function -- doing that
    would have cost a full `acquire_lock`/fetch/push cycle per failing
    domain, per run, confirmed by direct trace during that fix's own design."""
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
            next_state = _next_domain_state_with_failure_tracking(
                base, domain, domain_state, current_revision=current_revision
            )
            updated = base.model_copy(
                update={"domain_states": {**base.domain_states, domain: next_state}}
            )
            result = backend.save(org_repo, updated, expected_version)
            if result.outcome != "stale":
                return result
        raise StateBackendError(
            f"save_domain_with_failure_tracking for {org_repo!r}/{domain!r} did not converge "
            f"after {max_retries} retries"
        )
    finally:
        safe_release_lock(backend.release_lock, lock, label="lock")


def merge_unrecorded_failures(
    base: RunStateV1, failures: dict[str, DomainStateV1], *, current_revision: str | None = None
) -> RunStateV1:
    """`VER-005`: folds domains that never durably recorded themselves this
    run -- the guard-and-skip pattern 8 of 9 specialists still use on
    failure, or a crash escaping a specialist's own graph entirely before its
    record node ever runs -- into `base.domain_states`, applying the same
    per-domain escalation bookkeeping `save_domain_with_failure_tracking()`
    uses, for however many domains need it, patched onto one already-loaded
    `RunStateV1`.

    Deliberately does NOT acquire a lock or call `backend.save()` itself --
    callers fold the result into whatever single save they are already about
    to make (`supervisor/loop.py`'s own end-of-tier `SupervisorStateV1`
    write, at both its existing call sites) instead of this issuing a second,
    independent write. This is the whole point of the cost mitigation: a
    healthy run with an empty `failures` dict returns `base` unchanged, no
    new write; a run with failures enriches the *existing* write's payload
    rather than adding N new lock/fetch/push cycles.

    `base` must be the freshly-reloaded `RunStateV1` the caller is about to
    patch and save -- never a stale copy, so a concurrent writer's own
    already-accepted result for a different domain is never clobbered."""
    updated_domain_states = dict(base.domain_states)
    for domain, domain_state in failures.items():
        updated_domain_states[domain] = _next_domain_state_with_failure_tracking(
            base, domain, domain_state, current_revision=current_revision
        )
    return base.model_copy(update={"domain_states": updated_domain_states})


def is_domain_covered(domain_state: DomainStateV1 | None, current_revision: str | None) -> bool:
    """Wave 8.6 (`ORC-003` reversal prerequisite): revision-aware
    replacement for the former presence-only coverage check (`set(all_
    domains()) <= set(domain_states.keys())`), which could not tell a domain
    recomputed against the CURRENT upstream revision apart from a stale
    record left over from a run several revisions ago -- exactly the hole a
    literal specialist-selection reversal would otherwise reopen (a domain
    skipped for a few runs would still look "covered" forever, letting
    `is_fresh()`'s coarse shortcut mask a real missed change).

    A permanent, by-design non-outcome (`NON_ESCALATING_FAILURE_REASONS`) is
    always covered, never "incomplete" -- without this carve-out, 22/25 real
    registry entries (disabled-mode / no-policy-profile repos) would never
    satisfy a naive revision match for the domains that permanently error
    for them, permanently defeating `is_fresh()` and forcing the full
    specialist tier (live GitHub API calls included) on every run forever --
    the exact regression this fix must not introduce.

    A domain honestly skipped this run (`skipped_this_run`) is covered only
    if the skip itself was recorded against the current revision -- a skip
    recorded against a now-stale revision (state carried across an
    unexpectedly-long gap) is correctly treated as incomplete."""
    if domain_state is None:
        return False
    if domain_state.last_failure_reason in NON_ESCALATING_FAILURE_REASONS:
        return True
    if domain_state.skipped_this_run:
        return (
            current_revision is not None
            and domain_state.details.get("skipped_at_revision") == current_revision
        )
    return (
        current_revision is not None
        and domain_state.upstream_revision_at_accept == current_revision
    )


def compute_domain_coverage_complete(
    base: RunStateV1, specialist_domains: list[str], current_revision: str | None
) -> bool:
    """Wave 8.6: revision-aware replacement for `supervisor/loop.py`'s
    former `set(specialists_registry.all_domains()) <= set(base.domain_
    states.keys())` check -- see `is_domain_covered()`'s own docstring for
    why presence alone was insufficient."""
    return all(
        is_domain_covered(base.domain_states.get(domain), current_revision)
        for domain in specialist_domains
    )


def mark_specialist_tier_started(
    backend: StateBackend, org_repo: str, run_id: str, specialist_domains: list[str]
) -> None:
    """TC-23 (decision #46/#48): a best-effort CAS write recording that a
    specialist tier for `run_id` is about to attempt `specialist_domains`,
    called immediately BEFORE `supervisor/loop.py`'s domain loop begins --
    the one durable write in this whole mechanism that happens *before* the
    work it describes, mirroring `effect_ledger.py`'s own pending-before-
    execute discipline one level up. Cleared naturally by the next ordinary
    `_record_supervisor_state()` write at the end of a run that actually
    finishes (that call always constructs a fresh `SupervisorStateV1` with
    these fields left at their `None`/`[]` defaults, since callers never set
    them) -- no separate "clear" write is needed on the success path.

    Best-effort, matching `_record_supervisor_state()`'s own posture
    exactly: never able to fail the run by itself. A write that fails here
    only means the crash-detection this enables is unavailable for this one
    run, never that the run itself should be blocked -- the same tradeoff
    this project already accepted for every other durable-state write in
    this module."""
    try:
        current = backend.load(org_repo)
        expected_version = current.state_version if current else None
        base = current or RunStateV1(org_repo=org_repo)
        prior_supervisor_state = base.supervisor_state or SupervisorStateV1()
        updated_supervisor_state = prior_supervisor_state.model_copy(
            update={"in_flight_run_id": run_id, "in_flight_domains": list(specialist_domains)}
        )
        new_state = base.model_copy(update={"supervisor_state": updated_supervisor_state})
        result = backend.save(org_repo, new_state, expected_version)
        # A `stale` result here is not retried -- this is a best-effort
        # crash-detection aid, not a correctness-critical write; the next
        # attempt (or the run's own final write) will reflect current
        # reality regardless. Retrying would risk the exact kind of added
        # write-cost this project is already deliberately conservative about
        # (`SCL-004`/`SCL-005`'s own cost-consciousness).
        del result
    except StateBackendError as exc:
        print(
            f"warning: specialist-tier-started marker write failed for {org_repo!r}, "
            f"continuing without it: {exc}",
            file=sys.stderr,
        )


def effective_domain_coverage_complete(prior: SupervisorStateV1 | None) -> bool | None:
    """TC-23 (decision #46/#48, Phase 13 §13.1's precise `VER-005` boundary):
    a stale, uncleared `in_flight_run_id` means the run that wrote it never
    reached its own completing write -- a hard process/runner kill during
    the specialist tier, not a caught exception (those already produce a
    real `ERROR:` `DomainStateV1` via the existing mechanism). Forces the
    same honest full specialist-tier retry `is_fresh()`'s
    `check_domain_coverage` gate already performs for `None`/`False`,
    regardless of what `domain_coverage_complete` itself last recorded --
    that flag was necessarily computed and saved *before* this run's own
    completion, if `in_flight_run_id` is still non-`None`, so it cannot be
    trusted to describe the outcome of the run that set it."""
    if prior is None:
        return None
    if prior.in_flight_run_id is not None:
        return False
    return prior.domain_coverage_complete


def mark_domain_skipped(
    backend: StateBackend,
    org_repo: str,
    domain: str,
    current_revision: str,
    *,
    skip_reason: str,
    max_consecutive_skips: int,
    max_retries: int = 5,
) -> DomainStateV1:
    """Wave 8.6 (`ORC-003` reversal, `supervisor/specialist_selection.py`):
    durably records that `domain`'s detection dispatch was skipped this run
    rather than actually executed. Mirrors `save_domain()`'s own lock/CAS/
    retry shape.

    Deliberately leaves `accepted_status`/`accepted_facts_hash`/
    `upstream_revision_at_accept` untouched -- this domain was NOT
    reclassified this run, so none of its accepted baseline may honestly
    advance. The `max_consecutive_skips` check here is the last line of
    defense (`supervisor/specialist_selection.py::decide_skips()` already
    checks this before ever offering the domain to the LLM as skippable) --
    raising rather than silently capping means a caller that reaches this
    despite that earlier check has a real bug worth surfacing loudly, not
    papering over."""
    lock = backend.acquire_lock(org_repo)
    if lock is None:
        raise StateBackendError(
            f"could not acquire lock for {org_repo!r} to mark domain {domain!r} skipped"
        )
    try:
        for _ in range(max_retries):
            current = backend.load(org_repo)
            expected_version = current.state_version if current is not None else None
            base = current if current is not None else RunStateV1(org_repo=org_repo)
            prior = base.domain_states.get(domain) or DomainStateV1(domain=domain)
            if prior.consecutive_skip_count >= max_consecutive_skips:
                raise StateBackendError(
                    f"refusing to skip domain {domain!r} for {org_repo!r}: "
                    f"consecutive_skip_count={prior.consecutive_skip_count} already at/over "
                    f"max_consecutive_skips={max_consecutive_skips} -- caller must force a real run"
                )
            skipped_state = prior.model_copy(
                update={
                    "skipped_this_run": True,
                    "consecutive_skip_count": prior.consecutive_skip_count + 1,
                    "details": {
                        **prior.details,
                        "skipped_at_revision": current_revision,
                        "skip_reason": skip_reason,
                    },
                    "last_run_timestamp": datetime.now(UTC).isoformat(),
                }
            )
            updated = base.model_copy(
                update={"domain_states": {**base.domain_states, domain: skipped_state}}
            )
            result = backend.save(org_repo, updated, expected_version)
            if result.outcome != "stale":
                return skipped_state
        raise StateBackendError(
            f"mark_domain_skipped for {org_repo!r}/{domain!r} did not converge after "
            f"{max_retries} retries"
        )
    finally:
        safe_release_lock(backend.release_lock, lock, label="lock")
