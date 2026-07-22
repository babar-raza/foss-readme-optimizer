"""The production supervisor (`AGT-001`/`AGT-002`): observe -> plan -> execute
-> observe -> replan, promoting Wave 1's spike
(`plans/investigations/tools/prove_agentic_loop.py`) into durable, tested
production code -- the same framing `capabilities/dispatcher.py`'s own
docstring already uses for its own promotion from the same spike.

Additive alongside `orchestrator.py`, which stays exactly as it is -- the
CLI's existing `generate`/`run`/`run-registry` commands are untouched. New
opt-in CLI command `readme-agent supervise`, mirroring `--durable-state`'s
never-a-default convention. Cutting the GitHub Actions workflow over to
`supervise` instead of `run` is a separate, deliberately deferred decision.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent import paths
from readme_agent.capabilities import registry
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION, README_PRESENTATION
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.capabilities.stop import CAPABILITY_ID as STOP_CAPABILITY_ID
from readme_agent.errors import LLMError, StateBackendError
from readme_agent.evidence.writer import generate_run_id
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline, remote_head_sha
from readme_agent.llm import prompt_registry
from readme_agent.llm.planner_client import LivePlannerClient, PlannerClient
from readme_agent.registry.loader import find_entry, require_listed
from readme_agent.specialists import registry as specialists_registry
from readme_agent.state.backend import StateBackend, safe_release_lock
from readme_agent.state.domain_state import (
    compute_domain_coverage_complete,
    effective_domain_coverage_complete,
    mark_domain_skipped,
    mark_specialist_tier_started,
    merge_unrecorded_failures,
)
from readme_agent.state.schema import DomainStateV1, RunStateV1, SupervisorStateV1
from readme_agent.supervisor import dossier, repair, specialist_selection
from readme_agent.supervisor.convergence import (
    ConvergenceOutcome,
    check_repair_exhausted,
    compute_control_plane_fingerprint,
    final_status,
    is_fresh,
)
from readme_agent.supervisor.task import Task, TaskGraph

DEFAULT_MAX_TURNS = 8
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}
# Wave 8d (`VER-002`/"repair loops"): a tunable, not a settled constant --
# no operational history exists yet to justify a different value. Revisit
# once this wave has real run history.
ESCALATION_ALERT_THRESHOLD = 3
# AGT-008/Wave 8.5: a defensive circuit-breaker, not a routinely-approached
# limit -- real, live-measured evidence (this session's corrected gateway
# probe, plans/investigations/llm-gateway-context-ceiling-corrected.md)
# showed a realistic dossier-shaped round trip at 639-686 tokens, ~35x below
# this threshold, against a proven-safe real ceiling of ~71,069 tokens. No
# operational history yet to justify a different value.
DOSSIER_TOKEN_BUDGET = 25_000


@dataclass
class DecisionSummary:
    """`AGT-003`: every autonomous decision recorded as a concise summary in
    evidence, not only as hidden model reasoning."""

    turn: int
    kind: str  # "capability_selected" | "repair" | "stop" | "token_budget_exceeded" | ...
    detail: str


@dataclass
class SuperviseResult:
    status: str
    org_repo: str
    task_graph: TaskGraph
    decisions: list[DecisionSummary] = field(default_factory=list)
    blocked_reason: str | None = None
    evidence_dir: Path | None = None


def _current_upstream_revision(baseline_path: Path) -> str | None:
    result = run_git(["rev-parse", "HEAD"], cwd=baseline_path)
    return result.stdout.strip() if result.returncode == 0 else None


def _load_supervisor_state(backend: StateBackend | None, org_repo: str) -> SupervisorStateV1 | None:
    if backend is None:
        return None
    try:
        state = backend.load(org_repo)
    except StateBackendError as exc:
        print(f"warning: durable state read failed, continuing without it: {exc}", file=sys.stderr)
        return None
    return state.supervisor_state if state else None


def _record_supervisor_state(
    backend: StateBackend,
    org_repo: str,
    supervisor_state: SupervisorStateV1,
    *,
    failures: dict[str, DomainStateV1] | None = None,
) -> None:
    """Best-effort CAS write-back, mirrors `orchestrator._record_accepted_state()`
    exactly -- never able to fail the run by itself.

    `VER-005`: also folds `failures` (domains that never durably recorded
    themselves this run via their own guard-and-skip persistence, or a crash
    escaping a specialist's own graph entirely) into `domain_states` via
    `merge_unrecorded_failures()`, using the SAME freshly-loaded state this
    function already reads for its own CAS check -- not a second write, no
    added lock/fetch/push cost beyond this call's own existing one. Computes
    `domain_coverage_complete` from that same enriched state (does
    `specialists_registry.all_domains()` fully appear in `domain_states`
    afterward?) and sets it on `supervisor_state` before saving -- deliberately
    from this freshly-reloaded, about-to-be-saved state, never from the
    in-memory `specialist_results` dict a crashed process's own death would
    make irrelevant to any later process's check."""
    try:
        current = backend.load(org_repo)
        expected_version = current.state_version if current else None
        base = current or RunStateV1(org_repo=org_repo)
        if failures:
            base = merge_unrecorded_failures(
                base, failures, current_revision=supervisor_state.last_observed_upstream_revision
            )
        # Wave 8.6 (`ORC-003` reversal prerequisite): revision-aware, not
        # merely presence-aware -- see `compute_domain_coverage_complete()`'s
        # own docstring for why a key-presence-only check could not safely
        # coexist with the specialist-selection skip mechanism below.
        domain_coverage_complete = compute_domain_coverage_complete(
            base,
            specialists_registry.all_domains(),
            supervisor_state.last_observed_upstream_revision,
        )
        new_state = base.model_copy(
            update={
                "supervisor_state": supervisor_state.model_copy(
                    update={"domain_coverage_complete": domain_coverage_complete}
                )
            }
        )
        result = backend.save(org_repo, new_state, expected_version)
        if result.outcome == "stale":
            reloaded = backend.load(org_repo)
            if reloaded is None or (
                reloaded.supervisor_state
                and reloaded.supervisor_state.last_run_id != supervisor_state.last_run_id
            ):
                return  # a genuine conflicting write won; do not clobber it
    except StateBackendError as exc:
        print(
            f"warning: durable state write-back failed, continuing without it: {exc}",
            file=sys.stderr,
        )


def _dispatch_and_record(
    graph: TaskGraph,
    task: Task,
    *,
    backend: StateBackend | None,
    org_repo: str,
    decisions: list[DecisionSummary],
    turn: int,
    depth: int = 0,
    extra_kwargs: dict | None = None,
    repair_planner_client: PlannerClient | None = None,
    tools: list[dict] | None = None,
) -> Task:
    """Dispatches `task`, marks it terminal, and -- on a repairable failure
    -- creates and immediately dispatches a repair task, bounded by
    `repair.MAX_REPAIR_ATTEMPTS` per original failure (a reasoned, per-task
    bound, not the arbitrary global iteration cap `AGT-004` forbids).

    Returns the `Task` that actually carries the final word: `task` itself
    if it passed or was blocked outright, or the repair task if one was
    attempted -- callers must use the return value, not the `task` they
    passed in, since `TaskGraph.mark()` returns a *new* object rather than
    mutating in place (every other pydantic model in this codebase is
    treated as immutable the same way).

    `extra_kwargs` (AGT-008/Wave 8.5): supplied only by this function's own
    caller (wiring code, never the LLM) -- see `capabilities/dispatcher.py::
    dispatch_tool_call()`'s own docstring for the full reasoning. Threaded
    through the repair-retry recursion too, so a repaired `get_domain_
    findings` call still receives its `state_backend`.

    `repair_planner_client`/`tools` (Wave 8.6, `VER-006` reversal):
    optional, defaulting to `None` -- every existing caller is unaffected,
    since `repair.create_repair_task()`'s existing blind `execution_error`
    retry is tried first, unchanged, and `repair.select_repair_alternative()`
    is only ever consulted when that returns `None` AND a client was
    supplied."""
    graph.mark(task.task_id, "EXECUTING")
    tool_call = {"function": {"name": task.capability_id, "arguments": json.dumps(task.arguments)}}
    manifest = registry.get(task.capability_id) if task.capability_id else None
    write_capable = manifest is not None and manifest.side_effect_class in (
        "local_write",
        "remote_write",
    )

    if write_capable:
        # require_listed() (decision #40) means supervise_repo()'s entry gate
        # no longer implies mode == "full" -- this is the actual write-cycle
        # enforcement point: a write-capable capability must never dispatch
        # against a repo whose push access hasn't been verified.
        write_entry = find_entry(org_repo)
        if write_entry is None or write_entry.mode != "full":
            mode = write_entry.mode if write_entry else "unlisted"
            return graph.mark(
                task.task_id,
                "BLOCKED",
                blocked_reason=(
                    f"{task.capability_id!r} is write-capable but {org_repo} has "
                    f"mode={mode!r}, not 'full' -- refusing to dispatch"
                ),
            )

    if backend is not None and write_capable:
        gated = dispatch_gated_effect(
            tool_call, _READ_ONLY_PERMISSIONS | {"local_write", "remote_write"}, backend, org_repo
        )
        if gated.outcome == "already_applied":
            return graph.mark(task.task_id, "PASSED", result=gated.cached_result)
        if gated.outcome == "blocked_pending_reconciliation":
            return graph.mark(task.task_id, "BLOCKED", blocked_reason=gated.outcome)
        dispatch = gated.dispatch
    else:
        from readme_agent.capabilities.dispatcher import dispatch_tool_call

        dispatch = dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS, extra_kwargs=extra_kwargs)

    assert dispatch is not None
    if dispatch.outcome == "executed":
        return graph.mark(task.task_id, "PASSED", result=dispatch.result)

    classification = repair.classify_failure(dispatch)
    if dispatch.outcome == "rejected_unknown_capability":
        return graph.mark(task.task_id, "BLOCKED", blocked_reason=classification, gap=dispatch.gap)

    if depth < repair.MAX_REPAIR_ATTEMPTS:
        repair_task = repair.create_repair_task(graph, task, classification, manifest)
        repair_kind = "repair"
        if repair_task is None and repair_planner_client is not None and tools is not None:
            # Wave 8.6 (`VER-006` reversal): consulted only when the cheap
            # blind retry above found nothing to do (wrong classification,
            # or not idempotent-safe) AND a repair planner was actually
            # configured for this run -- every existing caller (no client
            # supplied) is byte-for-byte unaffected.
            repair_task = repair.select_repair_alternative(
                graph,
                task,
                classification,
                dispatch.error or classification,
                tools,
                repair_planner_client,
            )
            repair_kind = "repair_alternative_selected"
        if repair_task is not None:
            graph.mark(task.task_id, "FAILED", blocked_reason=dispatch.error)
            detail = (
                f"{task.capability_id!r} failed ({classification}); retrying once"
                if repair_kind == "repair"
                else (
                    f"{task.capability_id!r} failed ({classification}); repair planner "
                    f"selected {repair_task.capability_id!r}"
                )
            )
            decisions.append(DecisionSummary(turn=turn, kind=repair_kind, detail=detail))
            return _dispatch_and_record(
                graph,
                repair_task,
                backend=backend,
                org_repo=org_repo,
                decisions=decisions,
                turn=turn,
                depth=depth + 1,
                extra_kwargs=extra_kwargs,
                repair_planner_client=repair_planner_client,
                tools=tools,
            )
        if repair_planner_client is not None:
            decisions.append(
                DecisionSummary(
                    turn=turn,
                    kind="repair_escalated",
                    detail=(
                        f"{task.capability_id!r} failed ({classification}); no repair "
                        "alternative found -- escalating"
                    ),
                )
            )

    return graph.mark(task.task_id, "BLOCKED", blocked_reason=dispatch.error or classification)


def supervise_repo(
    org_repo: str,
    *,
    planner_client: PlannerClient | None = None,
    state_backend: StateBackend | None = None,
    write_evidence_bundle: bool = True,
    max_turns: int = DEFAULT_MAX_TURNS,
    # Wave 8.6 (`ORC-003` reversal): defaults fully off, mirroring
    # `--durable-state`'s own "never a default" convention -- every existing
    # caller/test is unaffected. When `False` (the default), `skip_plan`
    # below is unconditionally empty and `specialist_selection.decide_skips()`
    # is never invoked: zero behavior change, zero new cost.
    enable_specialist_skip: bool = False,
    specialist_selection_client: PlannerClient | None = None,
    # Wave 8.6 (`VER-006` reversal): defaults fully off, same convention as
    # the two params above -- every existing caller/test is unaffected.
    # When `None` (the default), `_dispatch_and_record()`'s own guard means
    # `repair.select_repair_alternative()` is never invoked.
    repair_planner_client: PlannerClient | None = None,
) -> SuperviseResult:
    # require_listed(), not require_permitted() (decision #40): most of a
    # supervised run is read-only planning/observation, so mode is not
    # itself a reason to refuse the whole run -- _dispatch_and_record()
    # is where a write-capable capability is actually mode-gated, per turn.
    entry = require_listed(org_repo)

    # Wave 8.6 (`OPS-011` extension): checked before any clone/specialist
    # work -- a disabled route means "known to be performing below
    # threshold," never a reason to still pay the full run's cost first.
    # Never a silent model substitution: this blocks the run outright,
    # exactly like `lock_held`/`run_lock_held`, until an explicit,
    # human-authored re-enable (`readme-agent model-route enable`).
    if state_backend is not None:
        route_status = state_backend.load_model_route_status("supervisor_planning")
        if route_status is not None and route_status.status == "disabled":
            return SuperviseResult(
                status="BLOCKED",
                org_repo=org_repo,
                task_graph=TaskGraph(),
                blocked_reason=f"model_route_disabled:supervisor_planning:{route_status.reason}",
            )

    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    current_control_plane_fingerprint = compute_control_plane_fingerprint(entry.policy_profile)
    prior = _load_supervisor_state(state_backend, org_repo)

    # Wave 8.5 (`ORC-006`): a cheap pre-clone SHA probe, mirroring
    # `profile/cached.py::get_or_build_profile()`'s already-proven "probe ->
    # compare to prior -> return cached on match -> else fall through" shape.
    # Only ever used for THIS early-return comparison -- anything persisted
    # downstream always comes from the post-clone, authoritative value below
    # (`_current_upstream_revision()`), preserving today's trust boundary
    # exactly: the two SHAs should normally agree, but only the clone-derived
    # one is ever trusted for state writes. `None` on any probe failure
    # (unreachable remote, no durable backend) falls through to the real
    # clone path unchanged, never treated as a false "unchanged" signal.
    probed_revision = remote_head_sha(entry.clone_url) if state_backend is not None else None
    if probed_revision is not None and is_fresh(
        prior.last_observed_upstream_revision if prior else None,
        probed_revision,
        recorded_control_plane_fingerprint=prior.control_plane_fingerprint if prior else None,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        recorded_domain_coverage_complete=effective_domain_coverage_complete(prior),
        check_domain_coverage=True,
    ):
        graph = TaskGraph()
        return SuperviseResult(
            status="CONVERGED_NO_CHANGE",
            org_repo=org_repo,
            task_graph=graph,
            decisions=[
                DecisionSummary(
                    turn=0,
                    kind="stop",
                    detail=(
                        f"upstream unchanged since last converged run (pre-clone probe, "
                        f"{probed_revision}); zero clone, zero planning calls"
                    ),
                )
            ],
        )

    clone_baseline(entry, baseline_path)
    current_revision = _current_upstream_revision(baseline_path)
    if is_fresh(
        prior.last_observed_upstream_revision if prior else None,
        current_revision,
        recorded_control_plane_fingerprint=prior.control_plane_fingerprint if prior else None,
        current_control_plane_fingerprint=current_control_plane_fingerprint,
        recorded_domain_coverage_complete=effective_domain_coverage_complete(prior),
        check_domain_coverage=True,
    ):
        graph = TaskGraph()
        return SuperviseResult(
            status="CONVERGED_NO_CHANGE",
            org_repo=org_repo,
            task_graph=graph,
            decisions=[
                DecisionSummary(
                    turn=0,
                    kind="stop",
                    detail=(
                        f"upstream unchanged since last converged run "
                        f"({current_revision}); zero planning calls"
                    ),
                )
            ],
        )

    # Wave 8.5 (`SCL-005` extension): a second, coarser, run-scoped lock,
    # acquired right after the freshness shortcuts above and BEFORE the
    # specialist tier starts -- closing the lock-race where two concurrent
    # supervise_repo() calls for the same org_repo could both pay for the
    # full specialist tier (including live GitHub API calls) before either
    # was rejected, because the narrower per-op lock below is acquired only
    # after that tier completes. This `try` wraps everything through the end
    # of the function -- including the `CONVERGED_NO_TRACKED_CHANGE`
    # shortcut below and the existing per-op lock's own nested try/finally --
    # closing the exact leak an adversarial review caught in an earlier
    # design draft: a version that only wrapped the specialist tier through
    # the per-op lock's own try block, but not the shortcut return, would
    # leak this lock for its full lease on that (plausibly common) path. Two
    # genuinely different git refs, both non-blocking optimistic-CAS
    # acquisitions (never a wait) -- no circular-wait is possible against the
    # per-op lock below, or against each specialist's own internal use of it.
    run_lock = None
    if state_backend is not None:
        run_lock = state_backend.acquire_run_lock(org_repo)
        if run_lock is None:
            return SuperviseResult(
                status="BLOCKED",
                org_repo=org_repo,
                task_graph=TaskGraph(),
                blocked_reason="run_lock_held",
            )
    try:
        # Wave 6 (decision #39): a second, finer-grained convergence tier, run
        # BEFORE the supervisor's own per-op lock is acquired below -- each
        # specialist's `record` step (`save_domain()`) acquires and releases
        # this exact per-org_repo lock internally, so holding it here first
        # would deadlock. Registry-driven, not hardcoded: Wave 7 adding a
        # specialist changes only `specialists/registry.py`, never this loop.
        #
        # Wave 7 failure isolation: `run_domain()` is called for each of
        # potentially seven independent specialists; before this fix, an
        # unhandled exception in any *one* of them propagated straight out of
        # `supervise_repo()` -- before the bootstrap dispatch and the main
        # try/finally block below even start -- discarding every other
        # specialist's already-computed result and never reaching the planner
        # loop at all. Contradicts `SCL-001`'s already-accepted "one failure does
        # not corrupt another's result" principle, applied one level down inside
        # a single repo's run. Mirrors `dispatch_tool_call`'s own "never let an
        # exception propagate" convention one layer down: a failing domain gets a
        # visible, recorded soft-failure entry (never silently swallowed, and
        # never mistaken for `NO_CHANGE` by the shortcut check below) and the
        # loop continues to the next domain.
        # Wave 8.6 (`ORC-003` reversal): computed once, before the specialist
        # tier loop, so a skip decision can be enforced inside it. Empty
        # unless the caller explicitly opts in -- see `enable_specialist_
        # skip`'s own docstring above.
        skip_plan = specialist_selection.SkipPlan()
        if enable_specialist_skip and state_backend is not None and current_revision is not None:
            try:
                prior_full_state = state_backend.load(org_repo)
            except StateBackendError:
                prior_full_state = None
            skip_plan = specialist_selection.decide_skips(
                org_repo=org_repo,
                baseline_path=baseline_path,
                prior_domain_states=(
                    prior_full_state.domain_states if prior_full_state is not None else {}
                ),
                current_revision=current_revision,
                specialist_selection_client=specialist_selection_client,
            )

        specialist_domains = specialists_registry.all_domains()
        specialist_results: dict[str, DomainStateV1] = {}
        # TC-23 (decision #46/#48): written BEFORE any domain is attempted,
        # not after -- a hard process/runner kill during the loop below
        # (unlike a caught Python exception, which the per-domain
        # try/except already turns into a real ERROR: state) leaves this
        # marker uncleared, detected as a stale `in_flight_run_id` by the
        # NEXT run's `effective_domain_coverage_complete()` check.
        if state_backend is not None:
            mark_specialist_tier_started(
                state_backend, org_repo, generate_run_id(), specialist_domains
            )
        for domain in specialist_domains:
            if domain in skip_plan.skip_domains:
                # decide_skips() only ever populates skip_domains inside the
                # guard above, which already requires both of these non-None.
                assert state_backend is not None
                assert current_revision is not None
                specialist_results[domain] = mark_domain_skipped(
                    state_backend,
                    org_repo,
                    domain,
                    current_revision,
                    skip_reason=skip_plan.reasons[domain],
                    max_consecutive_skips=specialist_selection.MAX_CONSECUTIVE_SKIPS,
                )
                continue
            try:
                result = specialists_registry.run_domain(
                    domain, org_repo, state_backend, current_revision=current_revision
                )
            except Exception as exc:  # noqa: BLE001 -- isolate one specialist's failure from the rest
                print(
                    f"warning: specialist domain {domain!r} raised, continuing with the "
                    f"others: {exc}",
                    file=sys.stderr,
                )
                # VER-005: must match the "ERROR:<reason>:<detail>" convention
                # every other failure in this codebase uses -- a bare "ERROR"
                # (no colon) fails `record_failure_or_reset()`'s own `is_error`
                # check, silently treating a genuine crash as a successful
                # accept once folded through `merge_unrecorded_failures()` below.
                result = DomainStateV1(
                    domain=domain,
                    accepted_status=f"ERROR:execution_error:{exc}",
                    details={"error": str(exc)},
                )
            if result is not None:
                specialist_results[domain] = result

        # VER-005: domains that never durably recorded themselves this run --
        # the guard-and-skip pattern 8 of 9 specialists still use on failure, or
        # the crash placeholder just above -- folded into whichever
        # `SupervisorStateV1` write this run makes (both call sites below), never
        # a separate write. `readme_presentation` is excluded: its own record
        # node already persists unconditionally via `save_domain_with_failure_
        # tracking()`, so folding it in here too would double-count its own
        # escalation counter. A specialist that succeeded already self-persisted
        # during the loop above -- nothing to fold in for it either.
        unrecorded_failures = {
            domain: result
            for domain, result in specialist_results.items()
            if domain != README_PRESENTATION and (result.accepted_status or "").startswith("ERROR:")
        }

        # Wave 8d (`VER-002`/"repair loops"): a domain crossing the failure-
        # escalation threshold gets a distinct, visible signal in evidence --
        # never silently folded into ordinary BLOCKED/ERROR noise. Read from
        # `independent_verification`'s own audit (Wave 8c), which already
        # surfaces every sibling's `consecutive_failure_count`/`last_failure_
        # reason` in one place, rather than requiring a human to check each
        # domain individually.
        independent_verification_result = specialist_results.get(INDEPENDENT_VERIFICATION)
        failure_escalations = (
            independent_verification_result.details.get("failure_escalations", {})
            if independent_verification_result is not None
            else {}
        )
        escalation_alerts = [
            DecisionSummary(
                turn=0,
                kind="escalation_alert",
                detail=(
                    f"{domain!r} has failed {info['consecutive_failure_count']} consecutive "
                    f"runs for the same reason ({info['last_failure_reason']!r}) -- human "
                    "attention needed"
                ),
            )
            for domain, info in failure_escalations.items()
            if info["consecutive_failure_count"] >= ESCALATION_ALERT_THRESHOLD
        ]

        # Wave 8.6 (`ORC-003` reversal): `and not r.skipped_this_run` is the
        # crux correctness guarantee -- a domain the skip mechanism carried
        # forward (never a fresh classification this run) must never
        # masquerade as a confirmed-unchanged NO_CHANGE for this shortcut's
        # purposes, even though its carried-forward `accepted_status` string
        # literally reads "NO_CHANGE". Any active skip forces the full,
        # safer, more expensive planner-loop path below instead.
        if specialist_domains and all(
            r.accepted_status == "NO_CHANGE" and not r.skipped_this_run
            for r in specialist_results.values()
        ):
            graph = TaskGraph()
            shortcut_decisions = [
                DecisionSummary(
                    turn=0,
                    kind="stop",
                    detail=(
                        f"upstream commit changed ({current_revision}), but every registered "
                        f"specialist domain reports NO_CHANGE ({sorted(specialist_results)}); "
                        "zero planning calls"
                    ),
                ),
                *escalation_alerts,
            ]
            if state_backend is not None and write_evidence_bundle:
                _record_supervisor_state(
                    state_backend,
                    org_repo,
                    SupervisorStateV1(
                        last_observed_upstream_revision=current_revision,
                        last_status="CONVERGED_NO_TRACKED_CHANGE",
                        last_run_timestamp=datetime.now(UTC).isoformat(),
                        control_plane_fingerprint=current_control_plane_fingerprint,
                    ),
                    failures=unrecorded_failures,
                )
            shortcut_evidence_dir = None
            if write_evidence_bundle:
                shortcut_run_id = generate_run_id()
                shortcut_evidence_dir = paths.evidence_dir(shortcut_run_id)
                _write_supervise_evidence(
                    shortcut_evidence_dir,
                    shortcut_run_id,
                    org_repo,
                    "CONVERGED_NO_TRACKED_CHANGE",
                    graph,
                    shortcut_decisions,
                    specialist_results,
                )
                _assert_evidence_complete(shortcut_evidence_dir)
            return SuperviseResult(
                status="CONVERGED_NO_TRACKED_CHANGE",
                org_repo=org_repo,
                task_graph=graph,
                decisions=shortcut_decisions,
                evidence_dir=shortcut_evidence_dir,
            )

        lock = None
        if state_backend is not None:
            lock = state_backend.acquire_lock(org_repo)
            if lock is None:
                # `StateBackend.acquire_lock()`'s own contract: `None` means
                # another holder has an unexpired lease -- "callers must not
                # proceed as if they hold it." A concurrent supervise_repo() for
                # the same org_repo is a genuine AGT-004 blocker, not silently
                # ignorable.
                return SuperviseResult(
                    status="BLOCKED",
                    org_repo=org_repo,
                    task_graph=TaskGraph(),
                    blocked_reason="lock_held",
                )
        try:
            graph = TaskGraph()
            decisions: list[DecisionSummary] = list(escalation_alerts)
            applied_any_effect = False

            bootstrap = graph.add_task(
                Task(capability_id="inspect_repository", arguments={"org_repo": org_repo})
            )
            bootstrap = _dispatch_and_record(
                graph,
                bootstrap,
                backend=state_backend,
                org_repo=org_repo,
                decisions=decisions,
                turn=0,
                repair_planner_client=repair_planner_client,
                tools=registry.all_tool_schemas(),
            )
            decisions.append(
                DecisionSummary(
                    turn=0, kind="capability_selected", detail="inspect_repository (bootstrap)"
                )
            )

            client = planner_client or LivePlannerClient(
                *_default_planner_args(),
            )

            # Wave 8.5 (`GOV-024`/`AGT-008`): the supervisor's own prompt now
            # lives in the categorical prompt registry, not a hardcoded
            # string literal, and every specialist domain gets a uniform
            # bounded summary (dossier.py) instead of the former special
            # case (8 domains reduced to a bare status enum, only
            # `independent_verification` getting full detail). Full,
            # untruncated findings for any domain remain available on demand
            # via the new `get_domain_findings` capability.
            supervisor_prompt = prompt_registry.get("supervisor_turn")
            assert supervisor_prompt is not None, "prompts/planning/supervisor_turn.yaml missing"
            initial_dossier = dossier.build_initial_dossier(specialist_results)
            tried_capability_ids: list[str] = []
            bootstrap_result = bootstrap.result or {}
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": supervisor_prompt.system},
                {
                    "role": "user",
                    "content": dossier.render_turn_context(
                        supervisor_prompt,
                        org_repo=org_repo,
                        turn_number=1,
                        max_turns=max_turns,
                        tried_capability_ids=tried_capability_ids,
                        bootstrap_result=bootstrap_result,
                        dossier=initial_dossier,
                    ),
                },
            ]

            turn = 0
            outcome = None
            while outcome is None:
                turn += 1
                outcome = check_repair_exhausted(turns_taken=turn, max_turns=max_turns)
                if outcome is not None:
                    break

                # Wave 8.5 (`GOV-024`): keep the situational turn-context
                # current -- overwritten in place (never appended), directly
                # countering the live-proven temperature=0.0 capability-menu
                # convergence bias (capability-dispatch-robustness.md
                # dimension 2: a static instruction converges to the same
                # choice every time; a per-turn-specific one does not).
                messages[1]["content"] = dossier.render_turn_context(
                    supervisor_prompt,
                    org_repo=org_repo,
                    turn_number=turn,
                    max_turns=max_turns,
                    tried_capability_ids=tried_capability_ids,
                    bootstrap_result=bootstrap_result,
                    dossier=initial_dossier,
                )

                # Wave 8.5 (D3): an uncaught planner-LLM failure used to
                # propagate straight out of supervise_repo(), past the
                # evidence-writing code below -- both locks still released
                # correctly (both are in `finally`), but zero evidence was
                # ever written for that attempt. Reuses the existing BLOCKED
                # status, exactly like "repair_exhausted"/"lock_held"/
                # "run_lock_held" -- no schema change needed.
                try:
                    plan = client.plan(messages, registry.all_tool_schemas())
                except LLMError as exc:
                    decisions.append(
                        DecisionSummary(
                            turn=turn, kind="stop", detail=f"planner_llm_failure: {exc}"
                        )
                    )
                    outcome = ConvergenceOutcome(
                        status="BLOCKED", blocked_reason=f"planner_llm_failure: {exc}"
                    )
                    break

                if plan.tool_call is None:
                    # The planner's own explicit stop signal -- the *only* normal
                    # way this loop concludes "converged" (see convergence.py's
                    # module docstring: graph emptiness alone is not a stop
                    # signal, it's trivially true after any single dispatch).
                    decisions.append(
                        DecisionSummary(
                            turn=turn, kind="stop", detail=plan.content or "planner stopped"
                        )
                    )
                    outcome = final_status(graph, applied_any_effect=applied_any_effect)
                    break

                function = plan.tool_call.get("function", {})
                capability_id = function.get("name")

                if capability_id == STOP_CAPABILITY_ID:
                    # TC-17 (decision #46, `AGT-006`): a real, registered stop
                    # call is telemetrically distinct from both the ordinary
                    # no-tool-call stop above AND an unrecognized/hallucinated
                    # capability name -- never dispatched, never reaches the
                    # task graph at all.
                    try:
                        stop_arguments = json.loads(function.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        stop_arguments = {}
                    decisions.append(
                        DecisionSummary(
                            turn=turn,
                            kind="stop",
                            detail=(f"stop capability called: {stop_arguments.get('reason', '')}"),
                        )
                    )
                    outcome = final_status(graph, applied_any_effect=applied_any_effect)
                    break

                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                # Unconditional override, not a default: the planner is never the
                # authority on which repo a dispatch targets. `setdefault` would
                # only fill this in when the model's own tool-call JSON omits
                # `org_repo` -- if the model supplies one itself (hallucination,
                # injected content, or a genuine mistake), that value would win
                # over the actual active run's trusted repo. There is no
                # legitimate reason for a single supervise_repo() call to ever
                # dispatch against a repo other than the one it was invoked for.
                arguments["org_repo"] = org_repo
                tried_capability_ids.append(capability_id or "")

                new_task = graph.add_task(Task(capability_id=capability_id, arguments=arguments))
                decisions.append(
                    DecisionSummary(
                        turn=turn, kind="capability_selected", detail=capability_id or ""
                    )
                )
                if new_task.state == "SUPERSEDED":
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"{capability_id} with these arguments was already answered "
                                f"this run: {json.dumps(new_task.result)}. Choose something "
                                "else, or stop."
                            ),
                        }
                    )
                    continue

                # AGT-008/Wave 8.5: wiring code (never the LLM) supplies the
                # live state_backend get_domain_findings needs -- see
                # capabilities/dispatcher.py::dispatch_tool_call()'s own
                # docstring for the full extra_kwargs reasoning.
                extra_kwargs = (
                    {"state_backend": state_backend}
                    if capability_id == "get_domain_findings"
                    else None
                )
                resolved = _dispatch_and_record(
                    graph,
                    new_task,
                    backend=state_backend,
                    org_repo=org_repo,
                    decisions=decisions,
                    turn=turn,
                    extra_kwargs=extra_kwargs,
                    repair_planner_client=repair_planner_client,
                    tools=registry.all_tool_schemas(),
                )
                if resolved.state == "PASSED":
                    resolved_manifest = (
                        registry.get(resolved.capability_id) if resolved.capability_id else None
                    )
                    if resolved_manifest is not None and resolved_manifest.side_effect_class in (
                        "local_write",
                        "remote_write",
                    ):
                        applied_any_effect = True
                messages.append(
                    {"role": "assistant", "content": plan.content, "tool_calls": [plan.tool_call]}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": plan.tool_call.get("id", ""),
                        "content": json.dumps(
                            {
                                "state": resolved.state,
                                "result": resolved.result,
                                "error": resolved.blocked_reason,
                            }
                        ),
                    }
                )

                # AGT-008/Wave 8.5: a defensive circuit breaker, not a
                # routinely-approached limit (see DOSSIER_TOKEN_BUDGET's own
                # module-level comment for the evidence backing this
                # threshold). Missing/partial usage data never trips this and
                # never crashes -- permissive by default, since the whole
                # point is a safety net, not a routine gate.
                usage = plan.meta.usage
                if (
                    usage is not None
                    and usage.prompt_tokens is not None
                    and usage.prompt_tokens > DOSSIER_TOKEN_BUDGET
                ):
                    decisions.append(
                        DecisionSummary(
                            turn=turn,
                            kind="token_budget_exceeded",
                            detail=f"prompt_tokens={usage.prompt_tokens}",
                        )
                    )
                    outcome = ConvergenceOutcome(
                        status="BLOCKED",
                        blocked_reason=f"dossier_token_budget_exceeded:{usage.prompt_tokens}",
                    )
                    break

            run_id = generate_run_id() if write_evidence_bundle else None
            if state_backend is not None and write_evidence_bundle:
                _record_supervisor_state(
                    state_backend,
                    org_repo,
                    SupervisorStateV1(
                        last_observed_upstream_revision=current_revision,
                        last_status=outcome.status,
                        last_run_id=run_id,
                        last_run_timestamp=datetime.now(UTC).isoformat(),
                        task_graph_snapshot=graph.snapshot(),
                        capability_gaps=[
                            t.gap.model_dump(mode="json") for t in graph.tasks.values() if t.gap
                        ],
                        # Wave 8.6 (`OPS-011`): includes the two new repair-
                        # planner decision kinds alongside the original blind-
                        # retry one, so golden_set/aggregation.py's repair-
                        # success/escalation metrics see every repair path.
                        repair_history=[
                            d.__dict__
                            for d in decisions
                            if d.kind
                            in ("repair", "repair_alternative_selected", "repair_escalated")
                        ],
                        control_plane_fingerprint=current_control_plane_fingerprint,
                    ),
                    failures=unrecorded_failures,
                )

            evidence_path = None
            if write_evidence_bundle:
                assert run_id is not None
                evidence_path = paths.evidence_dir(run_id)
                _write_supervise_evidence(
                    evidence_path,
                    run_id,
                    org_repo,
                    outcome.status,
                    graph,
                    decisions,
                    specialist_results,
                )
                _assert_evidence_complete(evidence_path)

            return SuperviseResult(
                status=outcome.status,
                org_repo=org_repo,
                task_graph=graph,
                decisions=decisions,
                blocked_reason=outcome.blocked_reason,
                evidence_dir=evidence_path,
            )
        finally:
            # See `state/backend.py::safe_release_lock()`'s own docstring for
            # the real bug this guards against (found live, 2026-07-22): a
            # release failure raising straight out of this `finally:` would
            # discard whatever `return SuperviseResult(...)` the `try` block
            # above was already returning.
            if lock is not None and state_backend is not None:
                safe_release_lock(state_backend.release_lock, lock, label="lock")
    finally:
        if run_lock is not None and state_backend is not None:
            safe_release_lock(state_backend.release_run_lock, run_lock, label="run-lock")


def _default_planner_args() -> tuple[str, str | None, str]:
    from readme_agent import env

    return env.llm_base_url(), env.llm_api_key(), env.llm_model_for_job("supervisor_planning")


def _write_supervise_evidence(
    evidence_dir: Path,
    run_id: str,
    org_repo: str,
    status: str,
    graph: TaskGraph,
    decisions: list[DecisionSummary],
    specialist_results: dict[str, DomainStateV1] | None = None,
) -> None:
    """Small, self-contained atomic-write helper -- duplicates
    `evidence/writer.py`'s `.tmp` + `os.replace` pattern rather than reusing
    its private `_atomic_write_json` (that function's redaction/jsonable
    conversion is tailored to `generate_repo()`'s specific payload shape).
    Flagged here rather than silently repeated uncredited.

    Wave 7: `specialist_results.json` is always written here, from every
    caller, on both the `CONVERGED_NO_TRACKED_CHANGE` shortcut path and the
    full planner-loop path -- before this fix, a specialist's findings were
    only ever visible embedded in the LLM's own conversation content on the
    full-loop path, and not recorded as evidence at all on the shortcut path.
    One canonical file to audit "what did every specialist find this run"
    regardless of which path the run took, growing cleanly as domain count
    increases. `manifest.json` also records `prompt_registry_content_hash`
    (Wave 8.5) so a human debugging a behavior change months later can
    directly check whether a prompt file changed, without recomputing the
    whole control-plane fingerprint."""
    evidence_dir.mkdir(parents=True, exist_ok=True)

    def _write(name: str, data: Any) -> None:
        tmp = evidence_dir / f"{name}.tmp"
        tmp.write_text(
            json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(tmp, evidence_dir / name)

    _write(
        "specialist_results.json",
        {
            domain: {
                "accepted_status": result.accepted_status,
                "skipped_this_run": result.skipped_this_run,
                "details": result.details,
            }
            for domain, result in (specialist_results or {}).items()
        },
    )
    _write("task_graph.json", graph.snapshot())
    _write(
        "decisions.json",
        [{"turn": d.turn, "kind": d.kind, "detail": d.detail} for d in decisions],
    )
    _write(
        "manifest.json",
        {
            "run_id": run_id,
            "org_repo": org_repo,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "prompt_registry_content_hash": prompt_registry.content_hash(),
        },
    )


_EXPECTED_EVIDENCE_FILES = (
    "specialist_results.json",
    "task_graph.json",
    "decisions.json",
    "manifest.json",
)


def _assert_evidence_complete(evidence_dir: Path) -> None:
    """Wave 8d: the run-level meaning of "evidence completeness gates"
    (distinct from Wave 8c's per-domain `check_evidence_complete()`) --
    closes the exact class of gap decision #41 already found once
    (specialist findings previously invisible on the `CONVERGED_NO_TRACKED_
    CHANGE` shortcut path, before that fix). Checks structural completeness
    (the file exists and is valid JSON), not semantic non-emptiness -- an
    empty task graph on the shortcut path is correct, honest content (zero
    tasks dispatched), not missing evidence."""
    for name in _EXPECTED_EVIDENCE_FILES:
        path = evidence_dir / name
        if not path.exists():
            raise RuntimeError(
                f"incomplete evidence bundle: {name!r} was not written to {evidence_dir}"
            )
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"incomplete evidence bundle: {name!r} in {evidence_dir} is not valid JSON"
            ) from exc
