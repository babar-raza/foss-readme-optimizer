"""Policy tests for agile mission admission, verification, and replanning."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from readme_agent.errors import ConfigError
from readme_agent.state.agile_execution_schema import (
    ApproachAttemptV1,
    ApproachControlStateV1,
    FirstPrinciplesReplanV1,
    InfrastructureAdmissionSpecV1,
    ParallelismControlStateV1,
    ParallelismObservationV1,
    SafeCommandAuthorityRequestV1,
    TaskCloseoutControlEvidenceV1,
)
from readme_agent.state.backend import SaveResult
from readme_agent.state.schema import MissionExecutionStateV1, RunStateV1
from readme_agent.supervisor import mission_command
from readme_agent.supervisor.approach_control import (
    apply_first_principles_replan,
    decide_approach_admission,
    decide_safe_command_authority,
    record_material_narrowing,
    start_approach_attempt,
    task_approach_fingerprint,
)
from readme_agent.supervisor.infrastructure_admission import (
    decide_infrastructure_admission,
)
from readme_agent.supervisor.mission_control import (
    claim_next_task,
    evaluate_mission,
    mission_state_key,
    persist_evaluation,
    record_first_principles_replan,
    record_parallelism_observation,
    record_task_material_narrowing,
)
from readme_agent.supervisor.mission_graph import load_mission_graph
from readme_agent.supervisor.mission_schema import RequirementCatalogRecordV1
from readme_agent.supervisor.multi_agent_admission import (
    MultiAgentAdmissionRequestV1,
    MultiAgentLaneLeaseV1,
    decide_multi_agent_admission,
    multi_agent_admission_sha256,
    request_from_execution_plan,
    validate_multi_agent_closeout_binding,
)
from readme_agent.supervisor.parallelism_admission import decide_parallelism
from readme_agent.supervisor.verification_policy import (
    build_verification_plan,
    validate_closeout_control_evidence,
    verification_plan_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_GRAPH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
ALL_ROUTE_ASSESSMENTS = [
    "reuse",
    "invalidation",
    "critical_path",
    "infrastructure_timing",
    "factuality",
    "safety",
    "smaller_alternatives",
]


class _MemoryStateBackend:
    def __init__(self) -> None:
        self.records: dict[str, RunStateV1] = {}

    def load(self, org_repo: str) -> RunStateV1 | None:
        record = self.records.get(org_repo)
        return deepcopy(record) if record is not None else None

    def save(self, org_repo: str, state: RunStateV1, expected_version: int | None) -> SaveResult:
        current = self.records.get(org_repo)
        current_version = current.state_version if current is not None else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self.records[org_repo] = state.model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult(outcome="saved", new_version=new_version)


def _graph_task():
    graph, _ = load_mission_graph(REAL_GRAPH)
    return graph.taskcards[0]


def _all_closed_statuses(graph) -> dict[str, str]:
    return {
        **{task.task_id: "CLOSED" for task in graph.taskcards},
        **{task.task_id: "CLOSED" for task in graph.deferred_task_index},
    }


def _observation(
    lane_count: int,
    *,
    speedup: float,
    overhead_ratio: float,
    duplicate: bool = False,
    observed_at: str = "2026-08-05T00:00:00+00:00",
) -> ParallelismObservationV1:
    parallel_seconds = 100.0
    return ParallelismObservationV1(
        lane_count=lane_count,
        serial_seconds=parallel_seconds * speedup,
        parallel_seconds=parallel_seconds,
        coordination_seconds=parallel_seconds * overhead_ratio,
        isolation_proven=True,
        disjoint_lease_ids=[f"lease-{index}" for index in range(lane_count)],
        duplicate_work_detected=duplicate,
        observed_at=observed_at,
    )


def test_infrastructure_admission_rejects_speculation_and_stacking_before_python():
    task = _graph_task().model_copy(
        update={
            "execution_kind": "infrastructure",
            "infrastructure_admission": InfrastructureAdmissionSpecV1(
                trigger="speculative",
                evidence_refs=["plans/idea.md"],
            ),
        }
    )

    speculative = decide_infrastructure_admission(
        task,
        infrastructure_tasks_since_visible_delivery=0,
        python_platform_complete=False,
    )
    assert speculative.admitted is False

    evidenced = task.model_copy(
        update={
            "infrastructure_admission": InfrastructureAdmissionSpecV1(
                trigger="current_repository_blocker",
                evidence_refs=["plans/requirements.md#L8-049"],
            )
        }
    )
    first = decide_infrastructure_admission(
        evidenced,
        infrastructure_tasks_since_visible_delivery=0,
        python_platform_complete=False,
    )
    stacked = decide_infrastructure_admission(
        evidenced,
        infrastructure_tasks_since_visible_delivery=1,
        python_platform_complete=False,
    )
    post_python = decide_infrastructure_admission(
        evidenced,
        infrastructure_tasks_since_visible_delivery=1,
        python_platform_complete=True,
    )

    assert first.admitted is True
    assert stacked.admitted is False
    assert post_python.admitted is True


def test_infrastructure_admission_never_infers_a_missing_specification():
    task = _graph_task().model_copy(
        update={"execution_kind": "auto", "infrastructure_admission": None}
    )
    assert task.core_contribution.kind == "first_boundary_removal"

    decision = decide_infrastructure_admission(
        task,
        infrastructure_tasks_since_visible_delivery=0,
        python_platform_complete=False,
    )

    assert decision.admitted is False
    assert decision.trigger == "speculative"
    assert decision.reason == "infrastructure task lacks an explicit admission specification"


def test_explicit_infrastructure_task_schema_requires_an_admission_specification():
    task = _graph_task()
    with pytest.raises(ValidationError, match="require infrastructure_admission"):
        task.__class__.model_validate(
            {
                **task.model_dump(mode="json"),
                "execution_kind": "infrastructure",
                "infrastructure_admission": None,
            }
        )


def test_ready_selector_enforces_the_infrastructure_delivery_budget():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses["L8-AGILE-AUTHORITY-RESET"] = "TODO"
    statuses["L8-VPY-03-ALL-PYTHON-VERIFIED-POC"] = "TODO"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
        infrastructure_tasks_since_visible_delivery=1,
    )

    evaluation = evaluate_mission(graph, state)

    assert evaluation.active_goal_id == "GOAL-V0A-FIRST-VERIFIED-README"
    assert evaluation.eligible_tasks == []


def test_verification_plan_and_closeout_receipt_fail_closed_on_missing_tier(tmp_path):
    task = _graph_task()
    plan = build_verification_plan(task)
    proof = tmp_path / "proof.txt"
    proof.write_text("proof", encoding="utf-8")
    receipt = TaskCloseoutControlEvidenceV1(
        task_id=task.task_id,
        verification_plan_sha256=verification_plan_sha256(plan),
        completed_tiers=plan.required_tiers[:-1],
        promotion_boundary=plan.promotion_boundary,
        canonical_evidence_promoted=plan.canonical_promotion_allowed,
        proof_refs=[str(proof)],
        independently_verified=True,
    )

    with pytest.raises(ValueError, match="missing verification tiers"):
        validate_closeout_control_evidence(task, receipt)

    complete = receipt.model_copy(update={"completed_tiers": plan.required_tiers})
    assert validate_closeout_control_evidence(task, complete) == complete

    premature_isolation = complete.model_copy(update={"transaction_isolation_proven": True})
    with pytest.raises(ValueError, match="only by a complete visible repository delivery"):
        validate_closeout_control_evidence(task, premature_isolation)

    visible_task = task.model_copy(update={"execution_kind": "visible_delivery"})
    visible_plan = build_verification_plan(visible_task)
    visible_isolation = premature_isolation.model_copy(
        update={
            "verification_plan_sha256": verification_plan_sha256(visible_plan),
            "completed_tiers": visible_plan.required_tiers,
            "promotion_boundary": visible_plan.promotion_boundary,
            "canonical_evidence_promoted": visible_plan.canonical_promotion_allowed,
        }
    )
    assert validate_closeout_control_evidence(visible_task, visible_isolation) == visible_isolation


def test_runtime_only_work_cannot_promote_canonical_evidence(tmp_path):
    task = _graph_task().model_copy(
        update={
            "execution_kind": "acceptance",
            "evidence_promotion_boundary": "runtime_only",
            "verification_change_classes": ["repository_runtime"],
        }
    )
    plan = build_verification_plan(task)
    proof = tmp_path / "proof.txt"
    proof.write_text("proof", encoding="utf-8")
    invalid = TaskCloseoutControlEvidenceV1(
        task_id=task.task_id,
        verification_plan_sha256=verification_plan_sha256(plan),
        completed_tiers=plan.required_tiers,
        promotion_boundary="runtime_only",
        canonical_evidence_promoted=True,
        proof_refs=[str(proof)],
        independently_verified=True,
    )

    with pytest.raises(ValueError, match="canonical evidence promotion"):
        validate_closeout_control_evidence(task, invalid)


def test_multi_agent_plan_is_bound_to_closeout_and_stale_hashes_fail(tmp_path):
    task = _graph_task()
    plan_dir = tmp_path / "runs" / "multi-agent" / task.task_id
    plan_dir.mkdir(parents=True)
    plan_path = plan_dir / "execution-plan.json"
    plan_path.write_text(
        f'{{"task_id":"{task.task_id}","roles":{{}}}}',
        encoding="utf-8",
    )
    decision = decide_multi_agent_admission(
        request_from_execution_plan(plan_path),
        decide_parallelism(ParallelismControlStateV1()),
        repository_root=tmp_path,
    )
    assert decision.admitted
    proof = tmp_path / "proof.txt"
    proof.write_text("proof", encoding="utf-8")
    verification_plan = build_verification_plan(task)
    complete = TaskCloseoutControlEvidenceV1(
        task_id=task.task_id,
        verification_plan_sha256=verification_plan_sha256(verification_plan),
        completed_tiers=verification_plan.required_tiers,
        promotion_boundary=verification_plan.promotion_boundary,
        canonical_evidence_promoted=verification_plan.canonical_promotion_allowed,
        proof_refs=[str(proof)],
        independently_verified=True,
        multi_agent_execution_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        multi_agent_admission_decision_sha256=multi_agent_admission_sha256(decision),
    )

    validate_multi_agent_closeout_binding(
        task.task_id,
        complete,
        decide_parallelism(ParallelismControlStateV1()),
        repository_root=tmp_path,
    )
    with pytest.raises(ValueError, match="stale or missing multi-agent execution plan hash"):
        validate_multi_agent_closeout_binding(
            task.task_id,
            complete.model_copy(update={"multi_agent_execution_plan_sha256": "0" * 64}),
            decide_parallelism(ParallelismControlStateV1()),
            repository_root=tmp_path,
        )


def test_parallelism_starts_serial_earns_lane_three_and_scales_down():
    assert decide_parallelism(ParallelismControlStateV1()).max_repository_lanes == 1

    isolated = ParallelismControlStateV1(
        transaction_isolation_proven=True,
        calibration_active=False,
    )
    assert decide_parallelism(isolated).max_repository_lanes == 2

    good_two = isolated.model_copy(
        update={"observations": [_observation(2, speedup=1.6, overhead_ratio=0.2)]}
    )
    assert decide_parallelism(good_two).max_repository_lanes == 3

    bad_two = isolated.model_copy(
        update={"observations": [_observation(2, speedup=1.2, overhead_ratio=0.3)]}
    )
    assert decide_parallelism(bad_two).max_repository_lanes == 1

    bad_three = isolated.model_copy(
        update={"observations": [_observation(3, speedup=1.4, overhead_ratio=0.2)]}
    )
    assert decide_parallelism(bad_three).max_repository_lanes == 2


def test_goal_capacity_consumes_measured_parallelism_policy():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    python_tasks = [
        task for task in graph.taskcards if task.stage_goal_id == "GOAL-V0-VERIFIED-PYTHON-POC"
    ]
    assert python_tasks
    for task in python_tasks:
        statuses[task.task_id] = "TODO"
    base = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
        parallelism_control=ParallelismControlStateV1(
            transaction_isolation_proven=True,
            calibration_active=False,
        ),
    )

    trial = evaluate_mission(graph, base)
    assert trial.capacity_allocation["max_concurrent_verified_lanes"] == 2

    earned = base.model_copy(
        update={
            "parallelism_control": base.parallelism_control.model_copy(
                update={"observations": [_observation(2, speedup=1.6, overhead_ratio=0.2)]}
            )
        }
    )
    assert evaluate_mission(graph, earned).capacity_allocation["max_concurrent_verified_lanes"] == 3


def test_parallel_observation_requires_isolation_and_is_durable():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    initialized = persist_evaluation(backend, graph, graph_hash)
    observation = _observation(2, speedup=1.6, overhead_ratio=0.2)

    with pytest.raises(ConfigError, match="prior transaction-isolation proof"):
        record_parallelism_observation(
            backend,
            graph,
            graph_hash,
            observation=observation,
        )

    assert initialized.mission_execution is not None
    isolated = initialized.mission_execution.model_copy(
        update={
            "parallelism_control": ParallelismControlStateV1(
                transaction_isolation_proven=True,
                calibration_active=False,
            )
        }
    )
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = initialized.model_copy(
        update={"mission_execution": isolated}
    )
    recorded = record_parallelism_observation(
        backend,
        graph,
        graph_hash,
        observation=observation,
    )

    assert recorded.mission_execution is not None
    assert recorded.mission_execution.parallelism_control.observations == [observation]


def test_two_equivalent_failures_and_fifteen_minutes_force_replan():
    task = _graph_task()
    fingerprint = task_approach_fingerprint(task)
    failed = ApproachControlStateV1(
        attempts=[
            ApproachAttemptV1(
                task_id=task.task_id,
                fingerprint=fingerprint,
                started_at=f"2026-08-05T00:0{index}:00+00:00",
                outcome="ineffective",
                evidence_refs=[f"attempt-{index}"],
            )
            for index in range(2)
        ]
    )
    assert decide_approach_admission(failed, task).admitted is False

    started = ApproachControlStateV1(
        attempts=[
            ApproachAttemptV1(
                task_id=task.task_id,
                fingerprint=fingerprint,
                started_at="2026-08-05T00:00:00+00:00",
            )
        ]
    )
    decision = decide_approach_admission(
        started,
        task,
        now=datetime(2026, 8, 5, 0, 15, tzinfo=UTC),
    )
    assert decision.requires_first_principles_replan is True


def test_visible_delivery_fingerprint_binds_the_small_execution_focus():
    graph, _ = load_mission_graph(REAL_GRAPH)
    task = next(item for item in graph.taskcards if item.execution_focus is not None)
    assert task.execution_focus is not None
    prior = task_approach_fingerprint(task)
    changed = task.model_copy(
        update={
            "execution_focus": task.execution_focus.model_copy(
                update={"immediate_outcome": "Show a materially different accepted README outcome."}
            )
        }
    )
    assert task_approach_fingerprint(changed) != prior


def test_material_narrowing_refreshes_the_anti_stall_watermark():
    task = _graph_task()
    state = start_approach_attempt(
        ApproachControlStateV1(),
        task,
        now=datetime(2026, 8, 5, 0, 0, tzinfo=UTC),
    )
    narrowed = record_material_narrowing(
        state,
        task.task_id,
        evidence_refs=["focused-test"],
        narrowed_at="2026-08-05T00:10:00+00:00",
    )

    decision = decide_approach_admission(
        narrowed,
        task,
        now=datetime(2026, 8, 5, 0, 20, tzinfo=UTC),
    )
    assert decision.admitted is True


def test_first_principles_replan_requires_classification_full_assessment_and_causal_change():
    task = _graph_task()
    prior = task_approach_fingerprint(task)
    with pytest.raises(ValidationError, match="change the approach fingerprint"):
        FirstPrinciplesReplanV1(
            task_id=task.task_id,
            prior_fingerprint=prior,
            new_fingerprint=prior,
            input_classification="tactic",
            route_change_assessments=ALL_ROUTE_ASSESSMENTS,
            rationale="The equivalent implementation path failed twice.",
            mechanism_changed=True,
            evidence_refs=["review.json"],
            created_at="2026-08-05T00:20:00+00:00",
        )

    with pytest.raises(ValidationError, match="must assess reuse"):
        FirstPrinciplesReplanV1(
            task_id=task.task_id,
            prior_fingerprint=prior,
            new_fingerprint="1" * 64,
            input_classification="tactic",
            route_change_assessments=["reuse"] * 7,
            rationale="The equivalent implementation path failed twice.",
            mechanism_changed=True,
            evidence_refs=["review.json"],
            created_at="2026-08-05T00:20:00+00:00",
        )


def test_replan_and_progress_updates_use_the_existing_durable_mission_state(tmp_path):
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="repair-agent")
    assert claimed.mission_execution is not None
    task = next(
        task for task in graph.taskcards if task.task_id == claimed.mission_execution.active_task_id
    )

    narrowed = record_task_material_narrowing(
        backend,
        graph,
        graph_hash,
        task_id=task.task_id,
        evidence_refs=["focused-test"],
    )
    assert narrowed.mission_execution is not None
    attempt = narrowed.mission_execution.approach_control.attempts[-1]
    assert attempt.last_material_narrowing_at is not None

    evidence = tmp_path / "first-principles-review.json"
    evidence.write_text("{}", encoding="utf-8")
    replan = FirstPrinciplesReplanV1(
        task_id=task.task_id,
        prior_fingerprint=attempt.fingerprint,
        new_fingerprint="2" * 64,
        input_classification="tactic",
        route_change_assessments=ALL_ROUTE_ASSESSMENTS,
        rationale="Move the causal owner from task prose to a typed admission boundary.",
        causal_owner_changed=True,
        evidence_refs=[str(evidence)],
        created_at=datetime.now(UTC).isoformat(),
    )
    replanned = record_first_principles_replan(
        backend,
        graph,
        graph_hash,
        replan=replan,
    )

    assert replanned.mission_execution is not None
    control = replanned.mission_execution.approach_control
    assert control.attempts[-2].outcome == "ineffective"
    assert control.attempts[-1].fingerprint == "2" * 64
    assert control.attempts[-1].outcome == "in_progress"
    assert control.proposed_fingerprints[task.task_id] == "2" * 64
    assert decide_approach_admission(control, task).admitted is True


def test_apply_replan_rejects_a_stale_prior_fingerprint():
    task = _graph_task()
    state = start_approach_attempt(ApproachControlStateV1(), task)
    replan = FirstPrinciplesReplanV1(
        task_id=task.task_id,
        prior_fingerprint="3" * 64,
        new_fingerprint="4" * 64,
        input_classification="hypothesis",
        route_change_assessments=ALL_ROUTE_ASSESSMENTS,
        rationale="The prior causal hypothesis does not match durable state.",
        pipeline_boundary_changed=True,
        evidence_refs=["review.json"],
        created_at=datetime.now(UTC).isoformat(),
    )

    with pytest.raises(ValueError, match="does not match the durable current approach"):
        apply_first_principles_replan(state, replan)


def test_public_mission_command_records_replan_and_resumes_claim(monkeypatch, tmp_path):
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="cli-repair-agent")
    assert claimed.mission_execution is not None
    active = claimed.mission_execution
    attempt = active.approach_control.attempts[-1]
    evidence = tmp_path / "first-principles-review.json"
    evidence.write_text("{}", encoding="utf-8")
    replan = FirstPrinciplesReplanV1(
        task_id=active.active_task_id or "",
        prior_fingerprint=attempt.fingerprint,
        new_fingerprint="a" * 64,
        input_classification="tactic",
        route_change_assessments=ALL_ROUTE_ASSESSMENTS,
        rationale="Move the causal owner to the typed public mission recovery boundary.",
        pipeline_boundary_changed=True,
        evidence_refs=[str(evidence)],
        created_at=datetime.now(UTC).isoformat(),
    )
    control_input = tmp_path / "replan.json"
    control_input.write_text(replan.model_dump_json(indent=2), encoding="utf-8")
    monkeypatch.setattr(mission_command, "default_state_backend", lambda: backend)
    base_args = {
        "mission_task_graph": str(REAL_GRAPH),
        "mission_task_id": None,
        "mission_to_status": None,
        "mission_reason": None,
        "mission_evidence": [],
        "mission_observer": "cli-repair-agent",
        "mission_control_input": str(control_input),
    }

    assert (
        mission_command.run_mission_command(
            SimpleNamespace(**base_args, mission_action="record-replan")
        )
        == 0
    )
    assert (
        mission_command.run_mission_command(SimpleNamespace(**base_args, mission_action="claim"))
        == 0
    )
    saved = backend.load(mission_state_key(graph.mission_authority.mission_id))
    assert saved is not None and saved.mission_execution is not None
    assert (
        saved.mission_execution.approach_control.proposed_fingerprints[replan.task_id]
        == replan.new_fingerprint
    )


@pytest.mark.parametrize(
    ("authority_request", "expected"),
    [
        (
            SafeCommandAuthorityRequestV1(plan_bound=True, local_only=True),
            "AUTO_PROCEED",
        ),
        (
            SafeCommandAuthorityRequestV1(
                plan_bound=True,
                local_only=False,
                external_effect=True,
            ),
            "HUMAN_AUTHORITY_REQUIRED",
        ),
        (
            SafeCommandAuthorityRequestV1(plan_bound=False, local_only=True),
            "REJECT_NOT_PLAN_BOUND",
        ),
    ],
)
def test_safe_command_authority_is_typed_and_fail_closed(authority_request, expected):
    assert decide_safe_command_authority(authority_request).disposition == expected


def test_requirement_catalog_preserves_legacy_status_during_migration():
    record = RequirementCatalogRecordV1(
        schema_version=1,
        requirement_id="L8-049",
        section="20. Level-8 consolidation gates",
        requirement="Infrastructure is admitted just in time.",
        priority="P0",
        status="PARTIAL",
        legacy_status="IMPLEMENTED",
        acceptance_evidence="Admission and negative controls.",
        legacy_acceptance_evidence="Original admission evidence.",
        traceability="Decision 92",
        legacy_line=1,
        legacy_row_sha256="0" * 64,
    )

    assert record.status == "PARTIAL"
    assert record.legacy_status == "IMPLEMENTED"
    assert record.legacy_acceptance_evidence == "Original admission evidence."


def _lane(
    lane_id: str,
    role: str,
    allowed_paths: list[str],
    *,
    status: str = "active",
    authored_paths: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    evidence_destination: str | None = None,
) -> MultiAgentLaneLeaseV1:
    return MultiAgentLaneLeaseV1(
        lane_id=lane_id,
        role=role,
        status=status,
        allowed_paths=allowed_paths,
        authored_paths=authored_paths or [],
        evidence_refs=evidence_refs or [],
        evidence_destination=evidence_destination,
    )


def _parallel_capacity(lanes: int):
    return decide_parallelism(
        ParallelismControlStateV1(
            transaction_isolation_proven=lanes >= 2,
            calibration_active=False,
            observations=([_observation(2, speedup=1.6, overhead_ratio=0.2)] if lanes == 3 else []),
        )
    )


def test_multi_agent_admission_allows_serial_execution_without_ceremonial_roles(tmp_path):
    request = MultiAgentAdmissionRequestV1(task_id="SERIAL", lanes=[])

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(1),
        repository_root=tmp_path,
    )

    assert decision.admitted is True
    assert decision.active_lane_count == 0


@pytest.mark.parametrize(
    "worker_paths",
    [
        ["runs/lane-a", "runs/lane-a"],
        ["src/readme_agent/ecosystems", "src/readme_agent/ecosystems/python.py"],
    ],
)
def test_multi_agent_admission_rejects_duplicate_and_parent_child_paths(
    tmp_path,
    worker_paths,
):
    request = MultiAgentAdmissionRequestV1(
        task_id="OVERLAP",
        lanes=[
            _lane("coordinator", "coordinator", ["runs/coordinator"]),
            _lane("worker", "repository_worker", worker_paths),
        ],
    )

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(2),
        repository_root=tmp_path,
    )

    assert decision.admitted is False
    assert any("duplicate or overlapping paths" in item for item in decision.violations)


def test_multi_agent_admission_rejects_cross_lane_overlap(tmp_path):
    request = MultiAgentAdmissionRequestV1(
        task_id="CROSS-OVERLAP",
        lanes=[
            _lane("coordinator", "coordinator", ["runs/coordinator"]),
            _lane(
                "worker-a",
                "repository_worker",
                ["runs/readme-poc/aspose-note-foss"],
            ),
            _lane(
                "worker-b",
                "repository_worker",
                ["runs/readme-poc/aspose-note-foss/revision"],
            ),
        ],
    )

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(2),
        repository_root=tmp_path,
    )

    assert decision.admitted is False
    assert any(
        "active lanes" in item and "overlapping paths" in item for item in decision.violations
    )


@pytest.mark.parametrize(
    "shared_path",
    [
        "AGENTS.md",
        "plans/master.md",
        "scripts/governance/validate_plan_structure.py",
        "src/readme_agent/state/schema.py",
        "src/readme_agent/supervisor/mission_control.py",
        ".git/index",
    ],
)
def test_multi_agent_admission_rejects_worker_leases_on_shared_paths(tmp_path, shared_path):
    request = MultiAgentAdmissionRequestV1(
        task_id="SHARED",
        lanes=[
            _lane("coordinator", "coordinator", ["runs/coordinator"]),
            _lane("worker", "repair_worker", [shared_path]),
        ],
    )

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(1),
        repository_root=tmp_path,
    )

    assert decision.admitted is False
    assert any("coordinator-owned shared path" in item for item in decision.violations)


def test_multi_agent_admission_rejects_verifier_implementation_authorship(tmp_path):
    request = MultiAgentAdmissionRequestV1(
        task_id="VERIFIER",
        lanes=[
            _lane(
                "coordinator",
                "coordinator",
                ["src/readme_agent/supervisor/runtime.py"],
            ),
            _lane(
                "verifier",
                "independent_verifier",
                ["runs/verification"],
                authored_paths=["src/readme_agent/supervisor/runtime.py"],
            ),
        ],
    )

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(1),
        repository_root=tmp_path,
    )

    assert decision.admitted is False
    assert any("authored implementation path" in item for item in decision.violations)


def test_multi_agent_admission_requires_inspectable_completed_lane_evidence(tmp_path):
    missing = MultiAgentAdmissionRequestV1(
        task_id="EVIDENCE",
        lanes=[
            _lane(
                "worker",
                "repository_worker",
                ["runs/readme-poc/repository-a"],
                status="completed",
            )
        ],
    )
    missing_decision = decide_multi_agent_admission(
        missing,
        _parallel_capacity(1),
        repository_root=tmp_path,
    )
    assert missing_decision.admitted is False
    assert any("no inspectable evidence" in item for item in missing_decision.violations)

    evidence = tmp_path / "runs" / "evidence" / "receipt.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}", encoding="utf-8")
    complete = missing.model_copy(
        update={
            "lanes": [
                missing.lanes[0].model_copy(
                    update={"evidence_refs": ["runs/evidence/receipt.json"]}
                )
            ]
        }
    )
    complete_decision = decide_multi_agent_admission(
        complete,
        _parallel_capacity(1),
        repository_root=tmp_path,
    )
    assert complete_decision.admitted is True


def test_multi_agent_admission_rejects_capacity_above_measured_decision(tmp_path):
    request = MultiAgentAdmissionRequestV1(
        task_id="CAPACITY",
        lanes=[
            _lane("coordinator", "coordinator", ["runs/coordinator"]),
            _lane("worker-a", "repository_worker", ["runs/repository-a"]),
            _lane("worker-b", "repository_worker", ["runs/repository-b"]),
        ],
    )

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(1),
        repository_root=tmp_path,
    )

    assert decision.admitted is False
    assert any("exceed measured capacity 1" in item for item in decision.violations)


def test_multi_agent_admission_serializes_shared_repairs(tmp_path):
    request = MultiAgentAdmissionRequestV1(
        task_id="SERIAL-REPAIR",
        lanes=[
            _lane("coordinator", "coordinator", ["runs/coordinator"]),
            _lane("repair-a", "repair_worker", ["src/readme_agent/cache/a.py"]),
            _lane("repair-b", "repair_worker", ["src/readme_agent/cache/b.py"]),
        ],
    )

    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(2),
        repository_root=tmp_path,
    )

    assert decision.admitted is False
    assert any("shared-code repair must run" in item for item in decision.violations)


def test_existing_execution_plan_preserves_bootstrap_violation_and_admits_serial_recovery():
    plan_path = (
        REPO_ROOT
        / "plans"
        / "investigations"
        / "evidence"
        / "agile-authority-reset-v1"
        / "multi-agent-execution-plan.json"
    )

    request = request_from_execution_plan(plan_path)

    assert request.task_id == "L8-AGILE-AUTHORITY-RESET"
    plan_text = plan_path.read_text(encoding="utf-8")
    assert '"status": "superseded_bootstrap_violation"' in plan_text
    assert "This violation is preserved rather than waived or hidden" in plan_text
    assert "component-versioning-and-acceptance-axes" not in {
        lane.lane_id for lane in request.lanes
    }
    assert "mission-admission-and-replanning-controls" not in {
        lane.lane_id for lane in request.lanes
    }
    decision = decide_multi_agent_admission(
        request,
        _parallel_capacity(1),
        repository_root=REPO_ROOT,
    )
    assert decision.admitted is True
    assert decision.violations == []
