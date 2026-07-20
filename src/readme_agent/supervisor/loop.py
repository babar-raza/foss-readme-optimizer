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
from readme_agent.capabilities.effect_ledger import dispatch_gated_effect
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import StateBackendError
from readme_agent.evidence.writer import generate_run_id
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.llm.planner_client import LivePlannerClient, PlannerClient
from readme_agent.registry.loader import find_entry, require_listed
from readme_agent.specialists import registry as specialists_registry
from readme_agent.state.backend import StateBackend
from readme_agent.state.schema import DomainStateV1, RunStateV1, SupervisorStateV1
from readme_agent.supervisor import repair
from readme_agent.supervisor.convergence import check_repair_exhausted, final_status, is_fresh
from readme_agent.supervisor.task import Task, TaskGraph

DEFAULT_MAX_TURNS = 8
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}

SYSTEM_PROMPT = (
    "You are an autonomous repository-presentation planner. You have a menu of capabilities "
    "(tools) describing what each one observes or changes. Given the current observation, call "
    "exactly one capability per turn that would most usefully extend your understanding of the "
    "repository, or address a gap you've observed. Once you have enough information and no "
    "further capability would help, stop calling tools and explain why in plain text."
)


@dataclass
class DecisionSummary:
    """`AGT-003`: every autonomous decision recorded as a concise summary in
    evidence, not only as hidden model reasoning."""

    turn: int
    kind: str  # "capability_selected" | "repair" | "stop"
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
    backend: StateBackend, org_repo: str, supervisor_state: SupervisorStateV1
) -> None:
    """Best-effort CAS write-back, mirrors `orchestrator._record_accepted_state()`
    exactly -- never able to fail the run by itself."""
    try:
        current = backend.load(org_repo)
        expected_version = current.state_version if current else None
        new_state = (current or RunStateV1(org_repo=org_repo)).model_copy(
            update={"supervisor_state": supervisor_state}
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
) -> Task:
    """Dispatches `task`, marks it terminal, and -- on a repairable failure
    -- creates and immediately dispatches exactly one repair task
    (`depth` bounds this to a single auto-repair attempt per original
    failure; this is a reasoned, per-task bound, not the arbitrary global
    iteration cap `AGT-004` forbids).

    Returns the `Task` that actually carries the final word: `task` itself
    if it passed or was blocked outright, or the repair task if one was
    attempted -- callers must use the return value, not the `task` they
    passed in, since `TaskGraph.mark()` returns a *new* object rather than
    mutating in place (every other pydantic model in this codebase is
    treated as immutable the same way)."""
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

        dispatch = dispatch_tool_call(tool_call, _READ_ONLY_PERMISSIONS)

    assert dispatch is not None
    if dispatch.outcome == "executed":
        return graph.mark(task.task_id, "PASSED", result=dispatch.result)

    classification = repair.classify_failure(dispatch)
    if dispatch.outcome == "rejected_unknown_capability":
        return graph.mark(task.task_id, "BLOCKED", blocked_reason=classification, gap=dispatch.gap)

    if depth == 0:
        repair_task = repair.create_repair_task(graph, task, classification, manifest)
        if repair_task is not None:
            graph.mark(task.task_id, "FAILED", blocked_reason=dispatch.error)
            decisions.append(
                DecisionSummary(
                    turn=turn,
                    kind="repair",
                    detail=f"{task.capability_id!r} failed ({classification}); retrying once",
                )
            )
            return _dispatch_and_record(
                graph,
                repair_task,
                backend=backend,
                org_repo=org_repo,
                decisions=decisions,
                turn=turn,
                depth=depth + 1,
            )

    return graph.mark(task.task_id, "BLOCKED", blocked_reason=dispatch.error or classification)


def supervise_repo(
    org_repo: str,
    *,
    planner_client: PlannerClient | None = None,
    state_backend: StateBackend | None = None,
    write_evidence_bundle: bool = True,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> SuperviseResult:
    # require_listed(), not require_permitted() (decision #40): most of a
    # supervised run is read-only planning/observation, so mode is not
    # itself a reason to refuse the whole run -- _dispatch_and_record()
    # is where a write-capable capability is actually mode-gated, per turn.
    entry = require_listed(org_repo)
    baseline_path = paths.baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, baseline_path)
    current_revision = _current_upstream_revision(baseline_path)

    prior = _load_supervisor_state(state_backend, org_repo)
    if is_fresh(prior.last_observed_upstream_revision if prior else None, current_revision):
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

    # Wave 6 (decision #39): a second, finer-grained convergence tier, run
    # BEFORE the supervisor's own lock is acquired below -- each specialist's
    # `record` step (`save_domain()`) acquires and releases this exact
    # per-org_repo lock internally, so holding it here first would deadlock.
    # Registry-driven, not hardcoded: Wave 7 adding a specialist changes only
    # `specialists/registry.py`, never this loop.
    specialist_domains = specialists_registry.all_domains()
    specialist_results: dict[str, DomainStateV1] = {}
    for domain in specialist_domains:
        result = specialists_registry.run_domain(domain, org_repo, state_backend)
        if result is not None:
            specialist_results[domain] = result

    if specialist_domains and all(
        r.accepted_status == "NO_CHANGE" for r in specialist_results.values()
    ):
        graph = TaskGraph()
        if state_backend is not None and write_evidence_bundle:
            _record_supervisor_state(
                state_backend,
                org_repo,
                SupervisorStateV1(
                    last_observed_upstream_revision=current_revision,
                    last_status="CONVERGED_NO_TRACKED_CHANGE",
                    last_run_timestamp=datetime.now(UTC).isoformat(),
                ),
            )
        return SuperviseResult(
            status="CONVERGED_NO_TRACKED_CHANGE",
            org_repo=org_repo,
            task_graph=graph,
            decisions=[
                DecisionSummary(
                    turn=0,
                    kind="stop",
                    detail=(
                        f"upstream commit changed ({current_revision}), but every registered "
                        f"specialist domain reports NO_CHANGE ({sorted(specialist_results)}); "
                        "zero planning calls"
                    ),
                )
            ],
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
        decisions: list[DecisionSummary] = []
        applied_any_effect = False

        bootstrap = graph.add_task(
            Task(capability_id="inspect_repository", arguments={"org_repo": org_repo})
        )
        bootstrap = _dispatch_and_record(
            graph, bootstrap, backend=state_backend, org_repo=org_repo, decisions=decisions, turn=0
        )
        decisions.append(
            DecisionSummary(
                turn=0, kind="capability_selected", detail="inspect_repository (bootstrap)"
            )
        )

        client = planner_client or LivePlannerClient(
            *_default_planner_args(),
        )
        specialist_observations = {
            domain: result.accepted_status for domain, result in specialist_results.items()
        }
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Repository: {org_repo}. Initial observation: "
                    f"{json.dumps(bootstrap.result)}. Specialist observations: "
                    f"{json.dumps(specialist_observations)}. Plan the next step, or stop if "
                    "nothing further would help."
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

            plan = client.plan(messages, registry.all_tool_schemas())
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
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            arguments.setdefault("org_repo", org_repo)

            new_task = graph.add_task(Task(capability_id=capability_id, arguments=arguments))
            decisions.append(
                DecisionSummary(turn=turn, kind="capability_selected", detail=capability_id or "")
            )
            if new_task.state == "SUPERSEDED":
                messages.append(
                    {
                        "role": "user",
                        "content": f"{capability_id} with these arguments was already answered "
                        f"this run: {json.dumps(new_task.result)}. Choose something else, or stop.",
                    }
                )
                continue

            resolved = _dispatch_and_record(
                graph,
                new_task,
                backend=state_backend,
                org_repo=org_repo,
                decisions=decisions,
                turn=turn,
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
                    repair_history=[d.__dict__ for d in decisions if d.kind == "repair"],
                ),
            )

        evidence_path = None
        if write_evidence_bundle:
            assert run_id is not None
            evidence_path = paths.evidence_dir(run_id)
            _write_supervise_evidence(
                evidence_path, run_id, org_repo, outcome.status, graph, decisions
            )

        return SuperviseResult(
            status=outcome.status,
            org_repo=org_repo,
            task_graph=graph,
            decisions=decisions,
            blocked_reason=outcome.blocked_reason,
            evidence_dir=evidence_path,
        )
    finally:
        if lock is not None and state_backend is not None:
            state_backend.release_lock(lock)


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
) -> None:
    """Small, self-contained atomic-write helper -- duplicates
    `evidence/writer.py`'s `.tmp` + `os.replace` pattern rather than reusing
    its private `_atomic_write_json` (that function's redaction/jsonable
    conversion is tailored to `generate_repo()`'s specific payload shape).
    Flagged here rather than silently repeated uncredited."""
    evidence_dir.mkdir(parents=True, exist_ok=True)

    def _write(name: str, data: Any) -> None:
        tmp = evidence_dir / f"{name}.tmp"
        tmp.write_text(
            json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(tmp, evidence_dir / name)

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
        },
    )
