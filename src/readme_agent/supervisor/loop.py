"""Canonical repository supervisor: observe, plan, verify, effect, reconcile."""

from datetime import UTC, datetime
from pathlib import Path

from readme_agent import paths
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.ecosystems.registry import known_manifest_globs
from readme_agent.errors import GitSafetyError
from readme_agent.evidence.writer import generate_run_id
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline, remote_head_sha
from readme_agent.llm.planner_client import PlannerClient
from readme_agent.registry.loader import require_listed
from readme_agent.state.backend import StateBackend, safe_release_lock
from readme_agent.state.freshness_contract import (
    DEFAULT_SURFACE_CONTRACTS,
    refresh_surface_contracts,
)
from readme_agent.state.schema import (
    DomainStateV1,
    SupervisorStateV1,
)
from readme_agent.supervisor.convergence import (
    compute_control_plane_fingerprint,
    no_change_gate_holds,
)
from readme_agent.supervisor.evidence import (
    assert_evidence_complete as _assert_evidence_complete,
)
from readme_agent.supervisor.evidence import write_supervise_evidence as _write_supervise_evidence
from readme_agent.supervisor.models import DecisionSummary, SuperviseResult
from readme_agent.supervisor.planner_loop import run_planner_loop
from readme_agent.supervisor.specialist_tier import run_specialist_tier
from readme_agent.supervisor.state_tracking import (
    load_prior_run_state as _load_prior_run_state,
)
from readme_agent.supervisor.state_tracking import (
    record_supervisor_state as _record_supervisor_state,
)
from readme_agent.supervisor.task import TaskGraph

DEFAULT_MAX_TURNS = 8
# TC-18 (Pillar A.2, decision #46's own rerun-consistency redesign): a
# code-computed termination backstop, independent of the planner ever
# emitting a real stop call -- AGT-006's own known failure mode (the planner
# repeatedly proposing an already-answered or unrecognized capability) would
# otherwise burn every remaining turn toward BLOCKED/repair_exhausted instead
# of a correct CONVERGED_* status. "No forward progress" here means a turn
# whose task ended up SUPERSEDED (an exact duplicate of an already-answered
# call this run) or BLOCKED (rejected/failed dispatch) rather than PASSED --
# a deliberately coarse, honest proxy for "nothing useful is left to try,"
# not a claim that the task graph is provably exhausted in the abstract (see
# plans/master.md's Decision Ledger for the tradeoff this scope narrowing
# accepts). Tunable, no operational history yet to justify a different
# value -- mirrors ESCALATION_ALERT_THRESHOLD's own precedent.
NO_PROGRESS_TURN_LIMIT = 3
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


def _current_upstream_revision(baseline_path: Path) -> str | None:
    result = run_git(["rev-parse", "HEAD"], cwd=baseline_path)
    return result.stdout.strip() if result.returncode == 0 else None


def _surface_observed_hashes(
    specialist_results: dict[str, DomainStateV1],
) -> dict[str, str | None]:
    """Wave 9.7 (`FRESH-010`): the four non-git-tracked domains' own
    `accepted_facts_hash`, as just (re)computed by a real specialist-tier
    run this turn -- fed to `refresh_surface_contracts()` so `observed_hash`
    reflects what was actually seen, not merely that a check happened."""
    return {
        surface_id: specialist_results[surface_id].accepted_facts_hash
        for surface_id in DEFAULT_SURFACE_CONTRACTS
        if surface_id in specialist_results
    }


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
    # Wave 9.4 (execution profiles): optional, defaulting to `None`, which
    # preserves today's exact hardcoded permission set -- every existing
    # caller/test is unaffected. `commands.py::cmd_supervise()` resolves this
    # from `--execution-profile` and passes it through; direct callers/tests
    # may pass it explicitly too.
    allowed_permission_classes: set[PermissionClass] | None = None,
) -> SuperviseResult:
    # require_listed(), not require_permitted() (decision #40): most of a
    # supervised run is read-only planning/observation, so mode is not
    # itself a reason to refuse the whole run -- _dispatch_and_record()
    # is where a write-capable capability is actually mode-gated, per turn.
    entry = require_listed(org_repo)

    if entry.ecosystem is None and entry.platform not in known_manifest_globs():
        return SuperviseResult(
            status="BLOCKED",
            org_repo=org_repo,
            task_graph=TaskGraph(),
            blocked_reason=f"unsupported_ecosystem:{entry.platform}",
            decisions=[
                DecisionSummary(
                    turn=0,
                    kind="capability_gap",
                    detail=(
                        f"no parser is registered for ecosystem/platform {entry.platform!r}; "
                        "the run is explicitly unsupported, never silently converged"
                    ),
                )
            ],
        )

    # Wave 8.7: a registry entry missing ecosystem/policy_profile ("not yet
    # onboarded" -- confirmed live, 2026-07-22: 28 of 31 real registry
    # entries) previously produced four different observable outcomes
    # depending on which capability the planner happened to reach first:
    # orchestrator.py's render path raising NotAllowlistedError (checks both
    # fields), verification/checks.py::independently_verify_readme_candidate()
    # raising NotAllowlistedError (checks policy_profile only), capabilities/
    # get_product_facts.py::execute() raising ValueError (checks
    # policy_profile only), or -- if none of those capabilities happened to
    # be reached early enough -- a slow, confusing DEFAULT_MAX_TURNS-turn
    # burn ending in BLOCKED/repair_exhausted via convergence.py::
    # check_repair_exhausted(). One check here, right after the allow-list
    # gate and before any clone, specialist tier, or planner turn, replaces
    # all four with a single, fast (seconds, not turns), unambiguous
    # BLOCKED/"not_onboarded" for anything reached through supervise_repo().
    # The three existing raise sites are deliberately left in place -- they
    # remain the correct gate for entry points that don't go through
    # supervise_repo() (direct `readme-agent generate`/`inspect` CLI
    # commands, direct capability invocations, or tests that exercise those
    # functions directly).
    if entry.ecosystem is None or entry.policy_profile is None:
        return SuperviseResult(
            status="BLOCKED",
            org_repo=org_repo,
            task_graph=TaskGraph(),
            blocked_reason="not_onboarded",
        )

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
    prior_full_state = _load_prior_run_state(state_backend, org_repo)
    prior = prior_full_state.supervisor_state if prior_full_state else None

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
    #
    # Wave 9.7 (`FRESH-010`): uses the full 7-condition `no_change_gate_
    # holds()`, not the bare 3-condition `is_fresh()` -- this is the
    # cheapest, most-likely-to-fire shortcut (skips even cloning), so
    # leaving it on the narrower gate would keep the "Git-SHA-only no-op"
    # bug alive on the path most likely to hide it.
    probed_revision = remote_head_sha(entry.clone_url) if state_backend is not None else None
    if probed_revision is not None and no_change_gate_holds(
        prior_full_state,
        probed_revision,
        current_control_plane_fingerprint,
        now=datetime.now(UTC),
    ):
        graph = TaskGraph()
        probe_decisions = [
            DecisionSummary(
                turn=0,
                kind="sha_probe_shortcut",
                detail=(
                    f"upstream unchanged since last converged run (pre-clone probe, "
                    f"{probed_revision}); zero clone, zero planning calls"
                ),
            )
        ]
        # Wave 8.7 (Item N): found live, 2026-07-22, that this shortcut wrote
        # no evidence at all -- only the console line above -- unlike its
        # post-clone sibling (CONVERGED_NO_TRACKED_CHANGE, below), which has
        # written a full run_id/manifest/decisions bundle since decision #41.
        # A human debugging months later could not tell, from evidence
        # alone, that this (cheapest, zero-clone) shortcut fired versus the
        # run never happening at all. `kind="sha_probe_shortcut"` (not the
        # generic "stop" every other stop condition uses) lets evidence
        # distinguish this specific, cost-free path from every other one.
        if state_backend is not None:
            _record_supervisor_state(
                state_backend,
                org_repo,
                SupervisorStateV1(
                    last_observed_upstream_revision=probed_revision,
                    last_status="CONVERGED_NO_CHANGE",
                    last_run_timestamp=datetime.now(UTC).isoformat(),
                    control_plane_fingerprint=current_control_plane_fingerprint,
                    # Wave 9.7: carried forward unchanged -- this shortcut never
                    # runs the specialist tier, so nothing new was learned about
                    # any non-git surface; `no_change_gate_holds()` already
                    # confirmed every tracked surface was still within its TTL
                    # at the moment this shortcut fired.
                    surface_freshness=prior.surface_freshness if prior else {},
                ),
            )
        probe_evidence_dir = None
        if write_evidence_bundle:
            probe_run_id = generate_run_id()
            probe_evidence_dir = paths.evidence_dir(probe_run_id)
            _write_supervise_evidence(
                probe_evidence_dir,
                probe_run_id,
                org_repo,
                "CONVERGED_NO_CHANGE",
                graph,
                probe_decisions,
                control_plane_fingerprint=current_control_plane_fingerprint,
                upstream_revision=probed_revision,
                surface_freshness=prior.surface_freshness if prior else {},
            )
            _assert_evidence_complete(probe_evidence_dir)
        return SuperviseResult(
            status="CONVERGED_NO_CHANGE",
            org_repo=org_repo,
            task_graph=graph,
            decisions=probe_decisions,
            evidence_dir=probe_evidence_dir,
        )

    # SCL-009 (2026-07-22): clone_baseline() itself validates its own memo
    # against a cheap remote_head_sha() probe before reusing a prior clone
    # (see clone.py's own module docstring) -- this call is always correct
    # whether this is the first or the Nth call to supervise_repo() in this
    # process, with no invalidation bookkeeping needed here.
    try:
        clone_baseline(entry, baseline_path)
    except GitSafetyError as exc:
        # Clone-reliability hardening (SCL-009, 2026-07-22): a clone_baseline()
        # failure previously propagated uncaught all the way to the CLI's bare
        # `error: ...` print and exit 3 -- no SuperviseResult, no evidence,
        # nothing for a portfolio pass or a human to inspect afterward. Caught
        # here, matching every other BLOCKED shortcut in this function, so a
        # slow/oversized repo (e.g. Aspose.Words-FOSS-for-.NET, ~15.5k files,
        # found live 2026-07-22 timing out against the previous hardcoded
        # 300s) degrades to an observable, evidenced outcome instead of an
        # opaque process abort.
        clone_failure_decisions = [
            DecisionSummary(turn=0, kind="baseline_clone_failed", detail=str(exc))
        ]
        clone_failure_evidence_dir = None
        if write_evidence_bundle:
            clone_failure_run_id = generate_run_id()
            clone_failure_evidence_dir = paths.evidence_dir(clone_failure_run_id)
            _write_supervise_evidence(
                clone_failure_evidence_dir,
                clone_failure_run_id,
                org_repo,
                "BLOCKED",
                TaskGraph(),
                clone_failure_decisions,
                control_plane_fingerprint=current_control_plane_fingerprint,
            )
            _assert_evidence_complete(clone_failure_evidence_dir)
        return SuperviseResult(
            status="BLOCKED",
            org_repo=org_repo,
            task_graph=TaskGraph(),
            decisions=clone_failure_decisions,
            blocked_reason=f"baseline_clone_failed:{exc}",
            evidence_dir=clone_failure_evidence_dir,
        )
    current_revision = _current_upstream_revision(baseline_path)
    # Wave 9.7 (`FRESH-010`): same 7-condition gate as the pre-clone probe
    # shortcut above, not the bare 3-condition `is_fresh()`.
    if no_change_gate_holds(
        prior_full_state,
        current_revision,
        current_control_plane_fingerprint,
        now=datetime.now(UTC),
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
        tier = run_specialist_tier(
            org_repo=org_repo,
            baseline_path=baseline_path,
            state_backend=state_backend,
            current_revision=current_revision,
            enable_specialist_skip=enable_specialist_skip,
            specialist_selection_client=specialist_selection_client,
            escalation_alert_threshold=ESCALATION_ALERT_THRESHOLD,
        )
        specialist_domains = tier.domains
        specialist_results = tier.results
        unrecorded_failures = tier.unrecorded_failures
        escalation_alerts = tier.escalation_alerts
        retry_alerts = tier.retry_alerts
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
                *retry_alerts,
            ]
            # Wave 9.7: the specialist tier actually ran this turn (every
            # domain reported NO_CHANGE) -- a real chance to observe every
            # non-git surface, so refresh, not carry forward. Computed once,
            # reused for both the durable-state write and the evidence
            # bundle below, rather than recomputed twice.
            refreshed_surface_freshness = refresh_surface_contracts(
                prior.surface_freshness if prior else {},
                _surface_observed_hashes(specialist_results),
                datetime.now(UTC),
            )
            if state_backend is not None and write_evidence_bundle:
                _record_supervisor_state(
                    state_backend,
                    org_repo,
                    SupervisorStateV1(
                        last_observed_upstream_revision=current_revision,
                        last_status="CONVERGED_NO_TRACKED_CHANGE",
                        last_run_timestamp=datetime.now(UTC).isoformat(),
                        control_plane_fingerprint=current_control_plane_fingerprint,
                        surface_freshness=refreshed_surface_freshness,
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
                    control_plane_fingerprint=current_control_plane_fingerprint,
                    upstream_revision=current_revision,
                    # Wave 9.7: every domain reported a real, non-skipped
                    # NO_CHANGE this turn (the condition that reached this
                    # branch) -- domain coverage is complete by construction
                    # here, not an inference across a helper boundary.
                    domain_coverage_complete=True,
                    surface_freshness=refreshed_surface_freshness,
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
            planner = run_planner_loop(
                org_repo=org_repo,
                specialist_results=specialist_results,
                initial_decisions=[*escalation_alerts, *retry_alerts],
                state_backend=state_backend,
                planner_client=planner_client,
                repair_planner_client=repair_planner_client,
                allowed_permission_classes=allowed_permission_classes,
                max_turns=max_turns,
                no_progress_turn_limit=NO_PROGRESS_TURN_LIMIT,
                dossier_token_budget=DOSSIER_TOKEN_BUDGET,
            )
            graph = planner.graph
            decisions = planner.decisions
            outcome = planner.outcome

            run_id = generate_run_id() if write_evidence_bundle else None
            # Wave 9.7: the specialist tier ran this turn -- refresh every
            # tracked non-git surface from what it actually saw. Computed
            # once, reused for both the durable-state write and the
            # evidence bundle below, rather than recomputed twice.
            refreshed_surface_freshness = refresh_surface_contracts(
                prior.surface_freshness if prior else {},
                _surface_observed_hashes(specialist_results),
                datetime.now(UTC),
            )
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
                        surface_freshness=refreshed_surface_freshness,
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
                    control_plane_fingerprint=current_control_plane_fingerprint,
                    upstream_revision=current_revision,
                    surface_freshness=refreshed_surface_freshness,
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
