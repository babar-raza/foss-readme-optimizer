"""Offline tests for the supervisor's central mission-taskcard consumer."""

import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from readme_agent.errors import ConfigError
from readme_agent.facts.acceptance_contract import current_fact_acceptance_contract
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.registry.loader import load_products
from readme_agent.state.agile_execution_schema import (
    ApproachAttemptV1,
    ApproachControlStateV1,
    ParallelismControlStateV1,
    TaskCloseoutControlEvidenceV1,
)
from readme_agent.state.backend import SaveResult
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.mission_goal_schema import MissionContributionEvidenceV1
from readme_agent.state.schema import MissionExecutionStateV1, MissionTransitionV1, RunStateV1
from readme_agent.supervisor.approach_control import task_approach_fingerprint
from readme_agent.supervisor.mission_control import (
    claim_next_task,
    evaluate_mission,
    has_graph_drift,
    mission_state_key,
    persist_evaluation,
    record_task_material_narrowing,
    transition_task,
)
from readme_agent.supervisor.mission_goal_guard import (
    derive_lifecycle_scoreboard,
    lifecycle_scoreboard_sha256,
)
from readme_agent.supervisor.mission_graph import load_mission_graph
from readme_agent.supervisor.mission_lifecycle_freshness import (
    evaluate_lifecycle_fact_freshness,
)
from readme_agent.supervisor.multi_agent_admission import (
    decide_multi_agent_admission,
    multi_agent_admission_sha256,
    request_from_execution_plan,
)
from readme_agent.supervisor.parallelism_admission import decide_parallelism
from readme_agent.supervisor.verification_policy import (
    build_verification_plan,
    verification_plan_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_GRAPH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)


def _load_tool_module(name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _write_contribution_evidence(
    tmp_path: Path,
    backend: _MemoryStateBackend,
    task,
) -> list[Path]:
    proof_path = tmp_path / f"{task.task_id}-proof.txt"
    proof_path.write_text("independent task proof", encoding="utf-8")
    scoreboard = derive_lifecycle_scoreboard(backend)
    scoreboard_hash = lifecycle_scoreboard_sha256(scoreboard)
    evidence = MissionContributionEvidenceV1(
        task_id=task.task_id,
        stage_goal_id=task.stage_goal_id,
        campaign_id=task.campaign_id,
        goal_ids=task.goal_ids,
        core_contribution=task.core_contribution,
        acceptance_checks_passed=task.acceptance_checks,
        proof_refs=[str(proof_path)],
        scoreboard_before_sha256=scoreboard_hash,
        scoreboard_after_sha256=scoreboard_hash,
        first_failing_boundary_before=scoreboard.first_failing_boundary,
        first_failing_boundary_after=scoreboard.first_failing_boundary,
        contribution_boundary_before=(
            "unresolved_task_boundary"
            if task.core_contribution.kind == "first_boundary_removal"
            else None
        ),
        contribution_boundary_after=(
            "resolved_task_boundary"
            if task.core_contribution.kind == "first_boundary_removal"
            else None
        ),
        independently_verified=True,
    )
    evidence_path = tmp_path / f"{task.task_id}-contribution.json"
    evidence_path.write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    verification_plan = build_verification_plan(task)
    execution_plan_path = REPO_ROOT / "runs" / "multi-agent" / task.task_id / "execution-plan.json"
    multi_agent_binding = {}
    if execution_plan_path.is_file():
        request = request_from_execution_plan(execution_plan_path)
        decision = decide_multi_agent_admission(
            request,
            decide_parallelism(ParallelismControlStateV1()),
            repository_root=REPO_ROOT,
        )
        assert decision.admitted
        multi_agent_binding = {
            "multi_agent_execution_plan_sha256": hashlib.sha256(
                execution_plan_path.read_bytes()
            ).hexdigest(),
            "multi_agent_admission_decision_sha256": multi_agent_admission_sha256(decision),
        }
    control = TaskCloseoutControlEvidenceV1(
        task_id=task.task_id,
        verification_plan_sha256=verification_plan_sha256(verification_plan),
        completed_tiers=verification_plan.required_tiers,
        promotion_boundary=verification_plan.promotion_boundary,
        canonical_evidence_promoted=verification_plan.canonical_promotion_allowed,
        proof_refs=[str(proof_path)],
        independently_verified=True,
        **multi_agent_binding,
    )
    control_path = tmp_path / f"{task.task_id}-closeout-control.json"
    control_path.write_text(control.model_dump_json(indent=2), encoding="utf-8")
    return [evidence_path, control_path]


def _all_closed_statuses(graph) -> dict[str, str]:
    """Build a complete synthetic terminal state across active and deferred records."""

    return {
        **{task.task_id: "CLOSED" for task in graph.taskcards},
        **{task.task_id: "CLOSED" for task in graph.deferred_task_index},
    }


def test_real_level8_graph_is_schema_valid_and_acyclic():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)

    assert graph.mission_authority.mission_id == "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
    assert graph.autonomous_execution_contract.mechanism_locked is True
    assert 1 <= len(graph.taskcards) <= 15
    assert len(graph.deferred_task_index) == graph.deferred_task_catalog.record_count
    assert len(graph_hash) == 64
    tasks = {task.task_id: task for task in graph.taskcards}
    assert set(tasks) == {
        "L8-AGILE-AUTHORITY-RESET",
        "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
        "L8-VPY-01-NOTE-VERIFIED-CANARY",
        "L8-VPY-00-PRESENTATION-CONTRACT-RESET",
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES",
        "L8-VPY-03C-PAGE-CURRENT-REFRESH",
        "L8-VPY-03D-NOTE-CURRENT-REFRESH",
        "L8-VPY-03E-3D-CURRENT-REFRESH",
        "L8-VPY-03-ALL-PYTHON-VERIFIED-POC",
        "L8-VNET-01-ACCELERATED-LOCAL-NO-OP",
        "L8-VPY-04-PRODUCTION-TRANSPORT",
        "L8-VPY-05-PRODUCTION-ADMISSION",
        "L8-VNET-02-PRODUCTION-TRANSPORT",
        "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES",
        "L8-HORIZON-01-ACTIVATE-GATE-A",
    }
    assert tasks["L8-AGILE-AUTHORITY-RESET"].dependencies == []
    assert tasks["L8-VPY-01-NOTE-VERIFIED-CANARY"].dependencies == ["L8-AGILE-AUTHORITY-RESET"]
    assert tasks["L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E"].dependencies == [
        "L8-VPY-01-NOTE-VERIFIED-CANARY"
    ]
    assert tasks["L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"].dependencies == [
        "L8-VPY-00-PRESENTATION-CONTRACT-RESET"
    ]
    assert tasks["L8-VPY-00-PRESENTATION-CONTRACT-RESET"].dependencies == [
        "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E"
    ]
    assert tasks["L8-VNET-01-ACCELERATED-LOCAL-NO-OP"].dependencies == [
        "L8-VPY-05-PRODUCTION-ADMISSION"
    ]
    assert tasks["L8-VPY-03C-PAGE-CURRENT-REFRESH"].dependencies == [
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
    ]
    assert tasks["L8-VPY-03D-NOTE-CURRENT-REFRESH"].dependencies == [
        "L8-VPY-03C-PAGE-CURRENT-REFRESH"
    ]
    assert tasks["L8-VPY-03E-3D-CURRENT-REFRESH"].dependencies == [
        "L8-VPY-03D-NOTE-CURRENT-REFRESH"
    ]
    assert tasks["L8-VPY-03-ALL-PYTHON-VERIFIED-POC"].dependencies == [
        "L8-VPY-03E-3D-CURRENT-REFRESH",
    ]
    assert tasks["L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"].execution_focus is not None
    assert (
        tasks["L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"].execution_focus.goal_id
        == "DELIVERY-PY-PDF-CURRENT"
    )
    assert tasks["L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"].dependencies == [
        "L8-VNET-02-PRODUCTION-TRANSPORT"
    ]
    assert tasks["L8-HORIZON-01-ACTIVATE-GATE-A"].dependencies == [
        "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"
    ]
    goals = {goal.goal_id: goal for goal in graph.mission_authority.stage_goal_catalog}
    campaigns = {campaign.campaign_id: campaign for campaign in graph.campaign_catalog}
    assert list(campaigns) == [
        "CAMP-PLAN-FREEZE",
        "CAMP-SHARED-ACCELERATION",
        "CAMP-FIRST-PYTHON-SLICE",
        "CAMP-PYTHON-PORTFOLIO",
        "CAMP-THREE-SLICES",
        "CAMP-GATE-A-PORTFOLIO",
        "CAMP-GATE-B-AND-LATER",
    ]
    assert all(task.campaign_id is not None for task in graph.taskcards)
    assert goals["GOAL-V0-VERIFIED-PYTHON-POC"].execution_required is True
    assert goals["GOAL-TP-TRUSTED-COHORT-POC"].execution_required is False
    assert goals["GOAL-L7-HETEROGENEOUS-30D"].execution_required is False
    assert goals["GOAL-L8-SELF-MAINTAINING-90D"].execution_required is False
    historical = [
        task for task in graph.deferred_task_index if task.activation_group == "historical-control"
    ]
    assert historical
    assert all(task.status == "DEFERRED_WITH_REASON" for task in historical)

    requirement_catalog = REPO_ROOT / graph.requirement_catalog.path
    coverage_path = REPO_ROOT / graph.requirement_coverage.path
    deferred_catalog = REPO_ROOT / graph.deferred_task_catalog.path
    assert hashlib.sha256(requirement_catalog.read_bytes()).hexdigest() == (
        graph.requirement_catalog.sha256
    )
    assert (
        hashlib.sha256(coverage_path.read_bytes()).hexdigest() == graph.requirement_coverage.sha256
    )
    assert hashlib.sha256(deferred_catalog.read_bytes()).hexdigest() == (
        graph.deferred_task_catalog.sha256
    )
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert len(coverage["mappings"]) == graph.requirement_coverage.record_count
    assert coverage["unmapped_requirement_ids"] == []
    assert {mapping["requirement_id"] for mapping in coverage["mappings"]} >= {
        "L8-001",
        "L8-011",
        "L8-047",
    }


def test_stage_goals_derive_advance_and_reactivate_without_manual_selection():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses["L8-AGILE-AUTHORITY-RESET"] = "TODO"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
        active_goal_id="GOAL-V2-VERIFIED-GATE-A",
    )

    qualification = evaluate_mission(graph, state)
    assert qualification.active_goal_id == "GOAL-V0A-FIRST-VERIFIED-README"
    assert qualification.concurrent_goal_ids == []
    assert [task.task_id for task in qualification.eligible_tasks] == ["L8-AGILE-AUTHORITY-RESET"]
    assert qualification.next_task is not None
    assert qualification.next_task.campaign_id == "CAMP-SHARED-ACCELERATION"

    first_readme = evaluate_mission(
        graph,
        state.model_copy(
            update={
                "task_statuses": {
                    **statuses,
                    "L8-AGILE-AUTHORITY-RESET": "CLOSED",
                    "L8-VPY-01-NOTE-VERIFIED-CANARY": "TODO",
                }
            }
        ),
    )
    assert first_readme.active_goal_id == "GOAL-V0A-FIRST-VERIFIED-README"
    assert first_readme.next_task is not None
    assert first_readme.next_task.task_id == "L8-VPY-01-NOTE-VERIFIED-CANARY"
    assert first_readme.next_task.immediate_goal_id == "DELIVERY-PY-CONTRACT-CURRENT"

    python_cohort = evaluate_mission(
        graph,
        state.model_copy(
            update={
                "task_statuses": {
                    **statuses,
                    "L8-AGILE-AUTHORITY-RESET": "CLOSED",
                    "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E": "TODO",
                    "L8-VPY-00-PRESENTATION-CONTRACT-RESET": "TODO",
                    "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES": "TODO",
                }
            }
        ),
    )
    assert python_cohort.active_goal_id == "GOAL-V0-VERIFIED-PYTHON-POC"
    assert [task.task_id for task in python_cohort.eligible_tasks] == [
        "L8-VPY-03B-FIRST-CURRENT-PYTHON-E2E",
    ]

    post_python = evaluate_mission(
        graph,
        state.model_copy(
            update={
                "task_statuses": {
                    **statuses,
                    "L8-AGILE-AUTHORITY-RESET": "CLOSED",
                    "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES": "TODO",
                }
            }
        ),
    )
    assert post_python.active_goal_id == "GOAL-V0B-POST-PYTHON-SLICES"
    assert post_python.next_task is not None
    assert post_python.next_task.task_id == "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES"

    reopened = evaluate_mission(
        graph,
        state.model_copy(
            update={
                "task_statuses": {
                    **statuses,
                    "L8-AGILE-AUTHORITY-RESET": "REGRESSED",
                }
            }
        ),
    )
    assert reopened.active_goal_id == "GOAL-V0A-FIRST-VERIFIED-README"
    assert reopened.next_task is not None
    assert reopened.next_task.task_id == "L8-AGILE-AUTHORITY-RESET"


def test_dotnet_remains_ineligible_until_python_production_admission():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses.update(
        {
            "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES": "TODO",
            "L8-VNET-01-ACCELERATED-LOCAL-NO-OP": "TODO",
        }
    )
    base_state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    serial = evaluate_mission(graph, base_state)

    assert serial.active_goal_id == "GOAL-V0-VERIFIED-PYTHON-POC"
    assert serial.concurrent_goal_ids == []
    assert [task.task_id for task in serial.eligible_tasks] == [
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
    ]

    isolated = evaluate_mission(
        graph,
        base_state.model_copy(
            update={
                "parallelism_control": ParallelismControlStateV1(
                    transaction_isolation_proven=True,
                    calibration_active=False,
                )
            }
        ),
    )

    assert isolated.concurrent_goal_ids == []
    assert [task.task_id for task in isolated.eligible_tasks] == [
        "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES",
    ]


def test_concurrent_lane_cannot_replace_an_admission_blocked_primary_claim():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    primary_id = "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
    concurrent_id = "L8-VNET-01-ACCELERATED-LOCAL-NO-OP"
    statuses.update({primary_id: "REGRESSED", concurrent_id: "TODO"})
    primary = next(task for task in graph.taskcards if task.task_id == primary_id)
    fingerprint = task_approach_fingerprint(primary)
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
        approach_control=ApproachControlStateV1(
            attempts=[
                ApproachAttemptV1(
                    task_id=primary_id,
                    fingerprint=fingerprint,
                    started_at=f"2026-08-10T00:0{index}:00+00:00",
                    outcome="ineffective",
                )
                for index in range(2)
            ]
        ),
        parallelism_control=ParallelismControlStateV1(
            transaction_isolation_proven=True,
            calibration_active=False,
        ),
    )
    backend = _MemoryStateBackend()
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = RunStateV1(
        org_repo=mission_state_key(graph.mission_authority.mission_id),
        state_version=1,
        mission_execution=state,
    )

    evaluation = evaluate_mission(graph, state)
    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="coordinator")

    assert evaluation.active_goal_id == "GOAL-V0-VERIFIED-PYTHON-POC"
    assert [task.task_id for task in evaluation.eligible_tasks] == []
    assert evaluation.next_task is None
    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id is None
    assert claimed.mission_execution.task_statuses[concurrent_id] == "TODO"


def test_platform_production_admission_keeps_python_ahead_of_dotnet_and_java():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses.update(
        {
            "L8-VPY-04-PRODUCTION-TRANSPORT": "TODO",
            "L8-VNET-02-PRODUCTION-TRANSPORT": "TODO",
            "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES": "TODO",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    python_transport = evaluate_mission(graph, state)

    assert python_transport.next_task is not None
    assert python_transport.next_task.task_id == "L8-VPY-04-PRODUCTION-TRANSPORT"

    dotnet_transport = evaluate_mission(
        graph,
        state.model_copy(
            update={
                "task_statuses": {
                    **statuses,
                    "L8-VPY-04-PRODUCTION-TRANSPORT": "CLOSED",
                }
            }
        ),
    )

    assert dotnet_transport.next_task is not None
    assert dotnet_transport.next_task.task_id == "L8-VNET-02-PRODUCTION-TRANSPORT"


def test_delivery_and_background_certification_have_distinct_closure_states():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    observation = next(
        task
        for task in graph.deferred_task_index
        if task.stage_goal_id == "GOAL-L7-HETEROGENEOUS-30D"
    )
    statuses[observation.task_id] = "OBSERVATION_RUNNING"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    observing = evaluate_mission(graph, state)

    assert observing.active_goal_id is None
    assert observing.delivery_complete is True
    assert observing.certification_complete is False
    assert observing.mission_complete is False

    certified = evaluate_mission(
        graph,
        state.model_copy(update={"task_statuses": {**statuses, observation.task_id: "CLOSED"}}),
    )

    assert certified.delivery_complete is True
    assert certified.certification_complete is True
    assert certified.mission_complete is True


def test_historical_deferred_dispositions_do_not_prevent_delivery_completion():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    historical = [
        task for task in graph.deferred_task_index if task.activation_group == "historical-control"
    ]
    assert historical
    for task in historical:
        statuses[task.task_id] = "DEFERRED_WITH_REASON"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert evaluation.delivery_complete is True
    assert all(task.task_id not in evaluation.unresolved_task_ids for task in historical)


def test_preserved_trusted_goals_cannot_regain_execution_authority():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses["TRP-04P-COHORT-FREEZE"] = "TODO"
    statuses["TRP-04-CANARY-QUALIFICATION"] = "TODO"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)
    assert evaluation.active_goal_id is None
    assert evaluation.next_task is None
    assert "TRP-04P-COHORT-FREEZE" not in evaluation.unresolved_task_ids
    assert "TRP-04-CANARY-QUALIFICATION" not in evaluation.unresolved_task_ids


def test_first_verified_readme_goal_precedes_the_python_platform_goal():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses.update(
        {
            "L8-AGILE-AUTHORITY-RESET": "TODO",
            "L8-VPY-01-NOTE-VERIFIED-CANARY": "TODO",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)
    assert evaluation.active_goal_id == "GOAL-V0A-FIRST-VERIFIED-README"
    assert evaluation.next_task is not None
    assert evaluation.next_task.task_id == "L8-AGILE-AUTHORITY-RESET"


def test_terminal_exception_stage_does_not_starve_later_ready_work():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses.update(
        {
            "L8-HORIZON-01-ACTIVATE-GATE-A": "TODO",
            "L8-GATE-D-GITHUB-APP-INTEGRATION": "BLOCKED_EXTERNAL",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert evaluation.active_goal_id == "GOAL-V0B-POST-PYTHON-SLICES"
    assert evaluation.next_task is not None
    assert evaluation.next_task.task_id == "L8-HORIZON-01-ACTIVATE-GATE-A"
    assert "L8-GATE-D-GITHUB-APP-INTEGRATION" in evaluation.blocked_external_task_ids
    assert evaluation.mission_complete is False


def test_requirement_coverage_source_hash_is_line_ending_independent(tmp_path: Path):
    coverage_tool = _load_tool_module(
        "build_level8_requirement_taskcard_coverage_line_endings",
        "scripts/governance/build_level8_requirement_taskcard_coverage.py",
    )
    lf_path = tmp_path / "requirements-lf.md"
    crlf_path = tmp_path / "requirements-crlf.md"
    lf_path.write_bytes(b"# Requirements\n\n| ID | Status |\n")
    crlf_path.write_bytes(b"# Requirements\r\n\r\n| ID | Status |\r\n")

    assert coverage_tool.canonical_text_sha256(lf_path) == coverage_tool.canonical_text_sha256(
        crlf_path
    )


def test_requirement_coverage_preserves_python_contract_and_production_stage_order():
    coverage_tool = _load_tool_module(
        "build_level8_requirement_taskcard_coverage_stage_order",
        "scripts/governance/build_level8_requirement_taskcard_coverage.py",
    )

    assert coverage_tool.task_stage_goal("L8-VPY-00-PRESENTATION-CONTRACT-RESET") == (
        "GOAL-V0-VERIFIED-PYTHON-POC",
        "primary_only",
    )
    assert coverage_tool.task_stage_goal("L8-VPY-04-PRODUCTION-TRANSPORT") == (
        "GOAL-V0B-POST-PYTHON-SLICES",
        "primary_only",
    )
    assert coverage_tool.task_stage_goal("L8-VPY-05-PRODUCTION-ADMISSION") == (
        "GOAL-V0B-POST-PYTHON-SLICES",
        "primary_only",
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda task: task.pop("goal_ids"), "invalid mission task graph"),
        (
            lambda task: task.update(goal_ids=["GOAL-NARRATIVE-ONLY"]),
            "invalid mission task graph",
        ),
        (
            lambda task: task["core_contribution"].update(
                summary="complete the task and support the mission"
            ),
            "vague core contribution",
        ),
    ],
)
def test_graph_rejects_missing_unknown_or_vague_goal_bindings(tmp_path, mutation, message):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    mutation(raw["taskcards"][0])
    invalid = tmp_path / "invalid-goal-binding.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_mission_graph(invalid)


def test_dynamic_scoreboard_counts_durable_lifecycle_progress(tmp_path):
    products = list(load_products())[:6]
    products_path = tmp_path / "products.json"
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    selected_org_repos = {entry.org_repo for entry in products}
    products_path.write_text(
        json.dumps(
            [
                item
                for item in source_products
                if f"{item['repo_url'].split('/')[3]}/{item['repo_name']}" in selected_org_repos
            ]
        ),
        encoding="utf-8",
    )
    backend = _MemoryStateBackend()
    statuses = (
        "FACTS_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_ACCEPTED",
    )
    for entry, status in zip(products, statuses, strict=True):
        backend.records[entry.org_repo] = RunStateV1(
            org_repo=entry.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(status=status),
        )

    scoreboard = derive_lifecycle_scoreboard(
        backend,
        products_path=products_path,
        verify_acceptance_freshness=False,
    )

    assert scoreboard.denominator == 6
    assert (
        scoreboard.facts_ready,
        scoreboard.candidate_generated,
        scoreboard.deterministic_validated,
        scoreboard.agent_approved,
        scoreboard.no_op_proven,
        scoreboard.human_accepted,
    ) == (6, 5, 4, 3, 2, 1)
    assert scoreboard.first_failing_boundary == "CANDIDATE_GENERATED"


def test_dynamic_scoreboard_builds_fact_contract_per_registry_entry(tmp_path, monkeypatch):
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    selected = [
        item
        for item in source_products
        if item["ecosystem"] == "python" and item["family"] in {"3d", "barcode"}
    ]
    products_path = tmp_path / "products.json"
    products_path.write_text(json.dumps(selected), encoding="utf-8")
    observed: list[tuple[str | None, str | None]] = []

    def contract(ecosystem=None, family=None):
        observed.append((ecosystem, family))
        return current_fact_acceptance_contract(ecosystem, family)

    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.current_fact_acceptance_contract",
        contract,
    )

    backend = _MemoryStateBackend()
    for item in selected:
        org_repo = f"{item['repo_url'].split('/')[3]}/{item['repo_name']}"
        backend.records[org_repo] = RunStateV1(
            org_repo=org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(status="FACTS_READY"),
        )

    scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert scoreboard.denominator == 2
    assert observed == [("python", "3d"), ("python", "barcode")]


def test_dynamic_scoreboard_does_not_build_fact_contract_for_unconfigured_discovery(
    tmp_path,
    monkeypatch,
):
    products_path = tmp_path / "products.json"
    products_path.write_text(
        json.dumps(
            [
                {
                    "family": "psd",
                    "platform": "python",
                    "repo_name": "Aspose.PSD-FOSS-for-Python",
                    "repo_url": "https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Python",
                    "clone_url": "https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Python.git",
                    "active": True,
                    "discovered_via": "github",
                    "mode": "disabled",
                    "ecosystem": None,
                    "policy_profile": None,
                }
            ]
        ),
        encoding="utf-8",
    )

    def unexpected_contract(*_args, **_kwargs):
        raise AssertionError("DISCOVERED intake must not require a fact contract")

    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.current_fact_acceptance_contract",
        unexpected_contract,
    )

    scoreboard = derive_lifecycle_scoreboard(_MemoryStateBackend(), products_path=products_path)

    assert scoreboard.denominator == 1
    assert scoreboard.lifecycle_status_counts == {"DISCOVERED": 1}
    assert scoreboard.missing_lifecycle_repositories == [
        "aspose-psd-foss/Aspose.PSD-FOSS-for-Python"
    ]


def test_dynamic_scoreboard_reports_raw_but_excludes_stale_acceptance(
    tmp_path,
    monkeypatch,
):
    entry = load_products()[0]
    products_path = tmp_path / "products.json"
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    products_path.write_text(
        json.dumps(
            [
                item
                for item in source_products
                if f"{item['repo_url'].split('/')[3]}/{item['repo_name']}" == entry.org_repo
            ]
        ),
        encoding="utf-8",
    )
    backend = _MemoryStateBackend()
    backend.records[entry.org_repo] = RunStateV1(
        org_repo=entry.org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="NO_OP_PROVEN",
            source_revision="a" * 40,
        ),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.evaluate_lifecycle_fact_freshness",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {"reusable": True, "mismatch_reasons": []},
        )(),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.local_poc_cache.evaluate_completed_local_poc_cache",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {
                "reusable": False,
                "mismatch_reasons": ["current_template_hash_mismatch"],
            },
        )(),
    )

    scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert scoreboard.raw_agent_approved == 1
    assert scoreboard.raw_no_op_proven == 1
    assert scoreboard.agent_approved == 0
    assert scoreboard.no_op_proven == 0
    assert scoreboard.stale_acceptance_repositories == {
        entry.org_repo: ["current_template_hash_mismatch"]
    }
    assert scoreboard.first_failing_boundary == "AGENT_APPROVED"


def test_dynamic_scoreboard_reports_raw_but_excludes_stale_fact_contract(
    tmp_path,
    monkeypatch,
):
    entry = load_products()[0]
    products_path = tmp_path / "products.json"
    source_products = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    products_path.write_text(
        json.dumps(
            [
                item
                for item in source_products
                if f"{item['repo_url'].split('/')[3]}/{item['repo_name']}" == entry.org_repo
            ]
        ),
        encoding="utf-8",
    )
    backend = _MemoryStateBackend()
    backend.records[entry.org_repo] = RunStateV1(
        org_repo=entry.org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="DETERMINISTIC_VALIDATED",
            source_revision="a" * 40,
        ),
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.mission_goal_guard.evaluate_lifecycle_fact_freshness",
        lambda *args, **kwargs: type(
            "Decision",
            (),
            {
                "reusable": False,
                "mismatch_reasons": ["fact_acceptance_contract_hash_changed"],
            },
        )(),
    )

    scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert (
        scoreboard.raw_facts_ready,
        scoreboard.raw_candidate_generated,
        scoreboard.raw_deterministic_validated,
    ) == (1, 1, 1)
    assert (
        scoreboard.facts_ready,
        scoreboard.candidate_generated,
        scoreboard.deterministic_validated,
    ) == (0, 0, 0)
    assert scoreboard.stale_fact_contract_repositories == {
        entry.org_repo: ["fact_acceptance_contract_hash_changed"]
    }
    assert scoreboard.first_failing_boundary == "FACTS_READY"


def test_fact_freshness_reuses_public_truth_contract_without_state_mutation(tmp_path):
    org_repo = "org/repo"
    source_revision = "a" * 40
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision=source_revision,
    )
    renderable_values = {
        "product.audience": ["Developers using Python"],
        "product.problems_solved": ["Process note files"],
        "product.capabilities": ["Create and inspect notes"],
        "product.formats": ["ONE"],
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "mission-freshness-fixture"),
            field=field,
            value=renderable_values.get(field, {"field": field}),
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    facts = ProductFactsV2(
        org_repo=org_repo,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )
    contract = current_fact_acceptance_contract()
    verification_hash = "b" * 64
    lifecycle = ReadmePocLifecycleStateV2(
        status="FACTS_READY",
        source_revision=source_revision,
        facts_hash=facts.canonical_hash(),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    state = RunStateV1(org_repo=org_repo, readme_poc_lifecycle=lifecycle)
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "facts").mkdir(parents=True)
    (bundle_dir / "facts" / "product-facts.json").write_text(
        facts.model_dump_json(), encoding="utf-8"
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "org_repo": org_repo,
                "source_revision": source_revision,
                "facts_hash": facts.canonical_hash(),
                "content_assurance": "repository_verified",
                "resolution_source": "repository_and_policy",
                "fact_acceptance_contract_hash": contract.canonical_hash(),
                "fact_acceptance_component_hashes": contract.component_hashes,
                "local_verification_contract_hash": verification_hash,
            }
        ),
        encoding="utf-8",
    )
    state_before = state.model_dump(mode="json")

    decision = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )

    assert decision.reusable is True
    assert decision.mismatch_reasons == []
    assert state.model_dump(mode="json") == state_before

    lifecycle.fact_acceptance_contract_hash = "0" * 64
    classification_only_change = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert classification_only_change.reusable is True

    lifecycle.fact_acceptance_component_hashes = {
        **contract.component_hashes,
        "fact_schema": "0" * 64,
    }
    recollection_change = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert recollection_change.reusable is False
    assert recollection_change.mismatch_reasons == [
        "fact_acceptance_recollection_component_changed"
    ]

    lifecycle.fact_acceptance_contract_hash = contract.canonical_hash()
    lifecycle.fact_acceptance_component_hashes = contract.component_hashes
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("content_assurance")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    missing_assurance = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert missing_assurance.reusable is False
    assert missing_assurance.mismatch_reasons == ["manifest_content_assurance_mismatch"]

    manifest["content_assurance"] = "repository_verified"
    manifest["resolution_source"] = "deterministic_salvage"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (bundle_dir / "facts" / "proposed-product-truth.json").write_text("{}", encoding="utf-8")
    lifecycle.prompt_hash = None
    deterministic_salvage = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert deterministic_salvage.reusable is True

    draft_prompt_hash = "0" * 64
    manifest["resolution_source"] = "agent_draft"
    manifest["prompt_hash"] = draft_prompt_hash
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    lifecycle.prompt_hash = draft_prompt_hash
    stale_prompt = evaluate_lifecycle_fact_freshness(
        state,
        bundle_dir,
        current_contract=contract,
        current_local_verification_hash=verification_hash,
    )
    assert stale_prompt.reusable is False
    assert stale_prompt.mismatch_reasons == [
        "agent_draft_resolution_not_cacheable",
        "draft_product_truth_prompt_hash_changed",
    ]


def test_lifecycle_scoreboard_registry_hash_is_line_ending_independent(tmp_path: Path):
    source = (REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8")
    canonical = source.replace("\r\n", "\n").replace("\r", "\n")
    products_path = tmp_path / "products.json"
    backend = _MemoryStateBackend()

    products_path.write_bytes(canonical.encode("utf-8"))
    lf_scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)
    products_path.write_bytes(canonical.replace("\n", "\r\n").encode("utf-8"))
    crlf_scoreboard = derive_lifecycle_scoreboard(backend, products_path=products_path)

    assert lf_scoreboard.registry_sha256 == crlf_scoreboard.registry_sha256
    assert lifecycle_scoreboard_sha256(lf_scoreboard) == lifecycle_scoreboard_sha256(
        crlf_scoreboard
    )


def test_requirement_coverage_classifier_handles_every_extractor_status():
    extractor = _load_tool_module(
        "extract_requirements_for_status_contract",
        "plans/investigations/tools/extract_requirements.py",
    )
    classifier = _load_tool_module(
        "coverage_classify_for_status_contract",
        "plans/investigations/tools/coverage_classify.py",
    )

    assert set(classifier.STATUS_DEFAULT) == extractor.VALID_STATUSES


def test_evaluate_initializes_then_claims_the_reset_task():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()

    first = persist_evaluation(backend, graph, graph_hash)
    second = persist_evaluation(backend, graph, graph_hash)

    assert first.state_version == 1
    assert second.state_version == 2
    state = second.mission_execution
    assert state is not None
    assert state.active_task_id is None
    assert state.task_statuses["L8-AGILE-AUTHORITY-RESET"] == "TODO"
    evaluation = evaluate_mission(graph, state)
    assert evaluation.mission_complete is False
    assert state.lifecycle_scoreboard is not None
    assert state.lifecycle_scoreboard.denominator == len(load_products())
    assert state.next_task is not None
    assert state.next_task.task_id == "L8-AGILE-AUTHORITY-RESET"
    assert evaluation.core_goal_active is True

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == "L8-AGILE-AUTHORITY-RESET"
    assert claimed.mission_execution.task_statuses["L8-AGILE-AUTHORITY-RESET"] == "IN_PROGRESS"


def test_evaluate_reopens_a_stale_closed_repository_before_its_dependent(monkeypatch):
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    statuses = _all_closed_statuses(graph)
    statuses.update(
        {
            "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES": "CLOSED",
            "L8-VPY-03C-PAGE-CURRENT-REFRESH": "TODO",
            "L8-VPY-03D-NOTE-CURRENT-REFRESH": "TODO",
            "L8-VPY-03E-3D-CURRENT-REFRESH": "TODO",
            "L8-VPY-03-ALL-PYTHON-VERIFIED-POC": "TODO",
            "L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES": "TODO",
            "L8-HORIZON-01-ACTIVATE-GATE-A": "TODO",
        }
    )
    mission_key = mission_state_key(graph.mission_authority.mission_id)
    backend.records[mission_key] = RunStateV1(
        org_repo=mission_key,
        state_version=8,
        mission_execution=MissionExecutionStateV1(
            mission_id=graph.mission_authority.mission_id,
            graph_sha256=graph_hash,
            task_statuses=statuses,
        ),
    )
    scoreboard = derive_lifecycle_scoreboard(backend).model_copy(
        update={
            "stale_fact_contract_repositories": {
                "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python": [
                    "fact_acceptance_recollection_component_changed"
                ]
            }
        }
    )
    monkeypatch.setattr(
        "readme_agent.supervisor.mission_control.derive_lifecycle_scoreboard",
        lambda _backend: scoreboard,
    )

    record = persist_evaluation(backend, graph, graph_hash)

    assert record.mission_execution is not None
    state = record.mission_execution
    assert state.task_statuses["L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"] == "REGRESSED"
    assert state.task_statuses["L8-VPY-03C-PAGE-CURRENT-REFRESH"] == "TODO"
    assert state.next_task is not None
    assert state.next_task.task_id == "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
    assert state.transition_history[-1].observed_by == "mission-lifecycle-freshness"

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="freshness-worker")

    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == ("L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES")


def test_evaluate_migrates_historical_work_to_a_durable_non_executable_disposition():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    historical = next(
        task for task in graph.deferred_task_index if task.activation_group == "historical-control"
    )
    statuses = {
        **{task.task_id: task.status for task in graph.taskcards},
        **{task.task_id: task.status for task in graph.deferred_task_index},
        historical.task_id: "IN_PROGRESS",
    }
    prior_transition = MissionTransitionV1(
        task_id=historical.task_id,
        from_status="TODO",
        to_status="READY",
        observed_by="pre-migration-worker",
        reason="preserved pre-migration history",
    )
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = RunStateV1(
        org_repo=mission_state_key(graph.mission_authority.mission_id),
        state_version=7,
        mission_execution=MissionExecutionStateV1(
            mission_id=graph.mission_authority.mission_id,
            graph_sha256="0" * 64,
            task_statuses=statuses,
            active_task_id=historical.task_id,
            claim_id="historical-claim",
            claimed_by="pre-migration-worker",
            claimed_at="2026-08-01T00:00:00+00:00",
            claim_expires_at="2026-08-01T00:30:00+00:00",
            transition_history=[prior_transition],
        ),
    )

    migrated = persist_evaluation(backend, graph, graph_hash)

    assert migrated.mission_execution is not None
    state = migrated.mission_execution
    assert state.task_statuses[historical.task_id] == "DEFERRED_WITH_REASON"
    assert state.active_task_id is None
    assert state.claim_id is None
    assert state.transition_history[0] == prior_transition
    assert state.transition_history[-1].task_id == historical.task_id
    assert state.transition_history[-1].from_status == "IN_PROGRESS"
    assert state.transition_history[-1].to_status == "DEFERRED_WITH_REASON"
    assert state.transition_history[-1].observed_by == "mission-graph-migration"


def test_read_only_evaluation_accepts_a_new_graph_task_before_state_reconciliation():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {
        **{task.task_id: task.status for task in graph.taskcards},
        **{task.task_id: task.status for task in graph.deferred_task_index},
    }
    statuses.pop("L8-AGILE-AUTHORITY-RESET")
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert "L8-AGILE-AUTHORITY-RESET" in evaluation.unresolved_task_ids
    assert evaluation.next_task is not None
    assert evaluation.next_task.task_id == "L8-AGILE-AUTHORITY-RESET"
    assert evaluation.mission_complete is False


def test_claim_is_idempotent_while_a_task_is_already_active():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)

    first = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    second = claim_next_task(backend, graph, graph_hash, claimed_by="other-worker")

    assert first.mission_execution is not None
    assert second.mission_execution is not None
    assert first.mission_execution.active_task_id == second.mission_execution.active_task_id
    assert first.mission_execution.claim_id is not None
    assert second.mission_execution.claim_id == first.mission_execution.claim_id
    assert second.mission_execution.claimed_by == first.mission_execution.claimed_by
    assert second.state_version == first.state_version


def test_claim_rejects_substitution_when_expected_task_is_not_eligible():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)

    with pytest.raises(ConfigError, match="is not eligible"):
        claim_next_task(
            backend,
            graph,
            graph_hash,
            claimed_by="test-worker",
            expected_task_id="L8-VNET-01-ACCELERATED-LOCAL-NO-OP",
        )

    record = backend.load(mission_state_key(graph.mission_authority.mission_id))
    assert record is not None
    assert record.mission_execution is not None
    assert record.mission_execution.active_task_id is None


def test_claim_rejects_expected_task_that_differs_from_live_claim():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="primary-worker")
    assert claimed.mission_execution is not None

    with pytest.raises(ConfigError, match="owns the active claim"):
        claim_next_task(
            backend,
            graph,
            graph_hash,
            claimed_by="secondary-worker",
            expected_task_id="L8-VNET-01-ACCELERATED-LOCAL-NO-OP",
        )


def test_closeout_ladder_then_claims_exactly_one_dependency_ready_task(tmp_path):
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    assert claimed.mission_execution is not None
    task_id = "L8-AGILE-AUTHORITY-RESET"
    assert claimed.mission_execution.active_task_id == task_id
    task = next(task for task in graph.taskcards if task.task_id == task_id)
    contribution_evidence = _write_contribution_evidence(tmp_path, backend, task)

    for status in ("IMPLEMENTED", "VERIFIED", "SCORED", "CLOSED"):
        record = transition_task(
            backend,
            graph,
            graph_hash,
            task_id=task_id,
            to_status=status,
            observed_by="test-verifier",
            reason=f"test transition to {status}",
            evidence_refs=(
                [str(path) for path in contribution_evidence]
                if status == "CLOSED"
                else [f"evidence/{status.lower()}.json"]
            ),
        )

    state = record.mission_execution
    assert state is not None
    assert state.infrastructure_tasks_since_visible_delivery == 1
    assert state.approach_control.attempts[-1].outcome == "effective"
    evaluation = evaluate_mission(graph, state)
    assert [task.task_id for task in evaluation.eligible_tasks] == [
        "L8-VPY-01-NOTE-VERIFIED-CANARY"
    ]

    next_claim = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    assert next_claim.mission_execution is not None
    assert next_claim.mission_execution.active_task_id == "L8-VPY-01-NOTE-VERIFIED-CANARY"


def test_rerouted_parent_does_not_unlock_dependent_tasks():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = _all_closed_statuses(graph)
    statuses.update(
        {
            "L8-AGILE-AUTHORITY-RESET": "REROUTED",
            "L8-VPY-01-NOTE-VERIFIED-CANARY": "TODO",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    eligible = [task.task_id for task in evaluate_mission(graph, state).eligible_tasks]

    assert eligible == []
    assert "L8-VPY-01-NOTE-VERIFIED-CANARY" not in eligible


def test_graph_drift_is_visible_to_read_only_status():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256="0" * 64,
        task_statuses={
            **{task.task_id: task.status for task in graph.taskcards},
            **{task.task_id: task.status for task in graph.deferred_task_index},
        },
    )

    assert has_graph_drift(state, graph_hash) is True


def test_expired_claim_is_recovered_before_the_next_claim():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    record = claim_next_task(backend, graph, graph_hash, claimed_by="lost-worker")
    assert record.mission_execution is not None
    expired = record.mission_execution.model_copy(
        update={
            "claim_id": "expired-claim",
            "claimed_by": "lost-worker",
            "claimed_at": "2020-01-01T00:00:00+00:00",
            "claim_expires_at": "2020-01-01T00:30:00+00:00",
        }
    )
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = record.model_copy(
        update={"mission_execution": expired}
    )

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="recovery-worker")

    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == "L8-AGILE-AUTHORITY-RESET"
    assert claimed.mission_execution.claimed_by == "recovery-worker"
    assert any(
        transition.to_status == "REGRESSED"
        for transition in claimed.mission_execution.transition_history
    )


def test_expired_claim_recovery_preserves_prior_material_narrowing():
    """A lease timeout must not erase narrowing recorded before it expired.

    Regression: _recover_expired_claim() unconditionally closed the active approach
    attempt as ineffective with evidence_refs=["claim lease expired"], discarding any
    last_material_narrowing_at/evidence_refs a prior record-narrowing call had already
    stamped on that same in-progress attempt. A long-running but genuinely progressing
    task (multiple real transactions plus an independent-verification pass, each easily
    exceeding the 30-minute claim lease) would then accumulate "ineffective" attempts
    purely from lease timeouts and eventually trip the two-equivalent-failures gate even
    though real narrowing had occurred throughout.
    """

    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    record = claim_next_task(backend, graph, graph_hash, claimed_by="lost-worker")
    assert record.mission_execution is not None
    task_id = record.mission_execution.active_task_id
    assert task_id is not None

    narrowed = record_task_material_narrowing(
        backend,
        graph,
        graph_hash,
        task_id=task_id,
        evidence_refs=["genuine forward progress before the lease lapsed"],
    )
    assert narrowed.mission_execution is not None
    live_attempt = next(
        attempt
        for attempt in narrowed.mission_execution.approach_control.attempts
        if attempt.task_id == task_id and attempt.outcome == "in_progress"
    )
    assert live_attempt.last_material_narrowing_at is not None

    expired = narrowed.mission_execution.model_copy(
        update={
            "claim_id": "expired-claim",
            "claimed_by": "lost-worker",
            "claimed_at": "2020-01-01T00:00:00+00:00",
            "claim_expires_at": "2020-01-01T00:30:00+00:00",
        }
    )
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = record.model_copy(
        update={"mission_execution": expired}
    )

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="recovery-worker")

    assert claimed.mission_execution is not None
    closed_attempt = next(
        attempt
        for attempt in claimed.mission_execution.approach_control.attempts
        if attempt.task_id == task_id and attempt.started_at == live_attempt.started_at
    )
    assert closed_attempt.outcome == "effective"
    assert closed_attempt.last_material_narrowing_at == live_attempt.last_material_narrowing_at
    assert "genuine forward progress before the lease lapsed" in closed_attempt.evidence_refs
    assert "claim lease expired" in closed_attempt.evidence_refs


def test_expired_claim_recovery_persists_even_when_expected_task_stays_unclaimable():
    """An expired claim must release even when the requested task cannot be reclaimed.

    Regression: claim_next_task() used to compute the expired-claim recovery and the
    "expected task is not claimable" rejection inside the same all-or-nothing mutator, so
    raising the rejection discarded the recovery too -- every retry recomputed and lost the
    same recovery, leaving the task permanently stuck under its expired claim.
    """

    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    record = claim_next_task(backend, graph, graph_hash, claimed_by="lost-worker")
    assert record.mission_execution is not None
    task_id = record.mission_execution.active_task_id
    assert task_id is not None
    task = next(t for t in graph.taskcards if t.task_id == task_id)
    fingerprint = task_approach_fingerprint(task)

    expired = record.mission_execution.model_copy(
        update={
            "claim_id": "expired-claim",
            "claimed_by": "lost-worker",
            "claimed_at": "2020-01-01T00:00:00+00:00",
            "claim_expires_at": "2020-01-01T00:30:00+00:00",
            "approach_control": ApproachControlStateV1(
                attempts=[
                    ApproachAttemptV1(
                        task_id=task_id,
                        fingerprint=fingerprint,
                        started_at="2020-01-01T00:00:00+00:00",
                        outcome="ineffective",
                    ),
                    ApproachAttemptV1(
                        task_id=task_id,
                        fingerprint=fingerprint,
                        started_at="2020-01-01T00:10:00+00:00",
                        outcome="ineffective",
                    ),
                ]
            ),
        }
    )
    backend.records[mission_state_key(graph.mission_authority.mission_id)] = record.model_copy(
        update={"mission_execution": expired}
    )

    with pytest.raises(ConfigError, match="is not dependency-ready"):
        claim_next_task(
            backend,
            graph,
            graph_hash,
            claimed_by="recovery-worker",
            expected_task_id=task_id,
        )

    persisted = backend.load(mission_state_key(graph.mission_authority.mission_id))
    assert persisted is not None
    assert persisted.mission_execution is not None
    assert persisted.mission_execution.active_task_id is None
    assert persisted.mission_execution.claimed_by is None
    assert any(
        transition.to_status == "REGRESSED"
        for transition in persisted.mission_execution.transition_history
    )


def test_direct_close_and_closure_without_evidence_fail_closed():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="test")
    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == "L8-AGILE-AUTHORITY-RESET"

    with pytest.raises(ConfigError, match="invalid mission transition"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-AGILE-AUTHORITY-RESET",
            to_status="CLOSED",
            observed_by="test",
            reason="skip every verification stage",
            evidence_refs=["not-enough.json"],
        )

    with pytest.raises(ConfigError, match="requires at least one evidence"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-AGILE-AUTHORITY-RESET",
            to_status="IMPLEMENTED",
            observed_by="test",
            reason="no evidence",
            evidence_refs=[],
        )

    for status in ("IMPLEMENTED", "VERIFIED", "SCORED"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-AGILE-AUTHORITY-RESET",
            to_status=status,
            observed_by="test",
            reason=f"reach {status} for closure guard",
            evidence_refs=[f"evidence/{status.lower()}.json"],
        )
    with pytest.raises(ConfigError, match="valid contribution evidence"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-AGILE-AUTHORITY-RESET",
            to_status="CLOSED",
            observed_by="test",
            reason="ordinary report cannot close the task",
            evidence_refs=["evidence/report.json"],
        )


def test_observation_running_is_reserved_for_background_certification():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)

    with pytest.raises(ConfigError, match="reserved for Level-7/Level-8 background"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-AGILE-AUTHORITY-RESET",
            to_status="OBSERVATION_RUNNING",
            observed_by="test",
            reason="delivery work cannot become an elapsed-time observation",
            evidence_refs=[],
        )

    background_task = graph.taskcards[0].model_copy(
        update={
            "stage_goal_id": "GOAL-L7-HETEROGENEOUS-30D",
            "status": "TODO",
        }
    )
    background_graph = graph.model_copy(
        update={"taskcards": [background_task, *graph.taskcards[1:]]}
    )
    background_backend = _MemoryStateBackend()
    persist_evaluation(background_backend, background_graph, graph_hash)

    observed = transition_task(
        background_backend,
        background_graph,
        graph_hash,
        task_id=background_task.task_id,
        to_status="OBSERVATION_RUNNING",
        observed_by="test",
        reason="production is deployed; certification window is now accumulating",
        evidence_refs=[],
    )

    assert observed.mission_execution is not None
    assert observed.mission_execution.task_statuses[background_task.task_id] == (
        "OBSERVATION_RUNNING"
    )


def test_cycle_and_alternative_controller_fail_closed(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    raw["taskcards"][0]["dependencies"] = [raw["taskcards"][1]["task_id"]]
    raw["taskcards"][1]["dependencies"] = [raw["taskcards"][0]["task_id"]]
    cyclic = tmp_path / "cyclic-mission.yaml"
    cyclic.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="cycle detected"):
        load_mission_graph(cyclic)

    raw["taskcards"][0]["dependencies"] = []
    raw["taskcards"][1]["dependencies"] = [raw["taskcards"][0]["task_id"]]
    raw["autonomous_execution_contract"]["mechanism_type"] = "autonomous_cycle"
    alternative = tmp_path / "alternative-controller.yaml"
    alternative.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="locked to autonomous_supervision"):
        load_mission_graph(alternative)


def test_requirement_coverage_reference_is_hash_bound(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    raw["requirement_coverage"]["sha256"] = "0" * 64
    invalid = tmp_path / "invalid-closure-mission.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="requirement coverage hash mismatch"):
        load_mission_graph(invalid)


def test_deferred_index_metadata_is_bound_to_its_exact_catalog_record(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    first = raw["deferred_task_index"][0]
    second = raw["deferred_task_index"][1]
    first["record_sha256"], second["record_sha256"] = (
        second["record_sha256"],
        first["record_sha256"],
    )
    invalid = tmp_path / "swapped-deferred-index.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="deferred task index metadata mismatch"):
        load_mission_graph(invalid)


def _redirect_first_taskcard_dependency_to_a_deferred_task(tmp_path, deferred_task_id: str):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    raw["taskcards"][0]["dependencies"] = [deferred_task_id]
    retargeted = tmp_path / "retargeted-deferred-dependency.yaml"
    retargeted.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return retargeted


def test_active_task_may_depend_on_a_closed_deferred_task(tmp_path):
    """Retiring a durably-CLOSED active task into the deferred catalog must not
    strand its dependants (l8-horizon-01-deferral-2026-08-13 Finding 3)."""

    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    deferred_task_id = raw["deferred_task_index"][0]["task_id"]
    retargeted = _redirect_first_taskcard_dependency_to_a_deferred_task(tmp_path, deferred_task_id)

    graph, graph_hash = load_mission_graph(retargeted)
    dependant = graph.taskcards[0]
    assert dependant.dependencies == [deferred_task_id]

    statuses = _all_closed_statuses(graph)
    statuses[dependant.task_id] = "TODO"
    statuses[deferred_task_id] = "CLOSED"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert evaluation.next_task is not None
    assert evaluation.next_task.task_id == dependant.task_id


def test_active_task_depending_on_a_non_closed_deferred_task_stays_blocked(tmp_path):
    """Negative control: a deferred dependency that is not CLOSED must still
    leave its dependant un-ready, not merely resolvable-by-existence."""

    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    deferred_task_id = raw["deferred_task_index"][0]["task_id"]
    retargeted = _redirect_first_taskcard_dependency_to_a_deferred_task(tmp_path, deferred_task_id)

    graph, graph_hash = load_mission_graph(retargeted)
    dependant = graph.taskcards[0]

    statuses = _all_closed_statuses(graph)
    statuses[dependant.task_id] = "TODO"
    statuses[deferred_task_id] = "DEFERRED_WITH_REASON"
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    evaluation = evaluate_mission(graph, state)

    assert dependant.task_id in evaluation.unresolved_task_ids
    assert evaluation.next_task is None or evaluation.next_task.task_id != dependant.task_id


def test_requirement_catalog_is_typed_even_when_a_tampered_hash_matches(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    source = REPO_ROOT / raw["requirement_catalog"]["path"]
    lines = source.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["priority"] = "P9"
    lines[0] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    catalog = tmp_path / "tampered-requirements.jsonl"
    catalog.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raw["requirement_catalog"].update(
        path=str(catalog), sha256=hashlib.sha256(catalog.read_bytes()).hexdigest()
    )
    invalid = tmp_path / "tampered-requirement-catalog.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="invalid requirement catalog record"):
        load_mission_graph(invalid)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda task: task.update(blocker_attempts=task["blocker_attempts"][:2]), "three attempts"),
        (
            lambda task: task["blocker_attempts"][2].update(attempt_number=2),
            "non-sequential attempts",
        ),
        (
            lambda task: task["blocker_attempts"][2].update(
                hypothesis=task["blocker_attempts"][1]["hypothesis"]
            ),
            "not materially distinct",
        ),
        (lambda task: task.update(exact_external_action=None), "exact external action"),
    ],
)
def test_external_blocker_requires_three_distinct_attempts_and_resume_contract(
    tmp_path, mutation, message
):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    task = raw["taskcards"][0]
    task.update(
        status="BLOCKED_EXTERNAL",
        blocker_attempts=[
            {
                "blocker_id": "SYNTHETIC-EXTERNAL",
                "attempt_number": attempt,
                "hypothesis": f"Distinct external-unblock hypothesis {attempt}",
                "first_failing_boundary": f"External boundary {attempt}",
                "evidence_considered": [f"Evidence {attempt}"],
                "action_taken": f"Safe attempt {attempt}",
                "verification_run": [f"Verification {attempt}"],
                "result": f"External dependency remains after attempt {attempt}",
                "new_information": f"New external fact {attempt}",
                "reason_for_next_attempt": f"Try distinct path {attempt + 1}",
            }
            for attempt in range(1, 4)
        ],
        exact_external_action="External owner grants the missing authority.",
        exact_resume_condition="The authority record is locally observable.",
    )
    mutation(task)
    invalid = tmp_path / "invalid-external-blocker.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_mission_graph(invalid)


def test_state_key_is_separate_from_every_product_repository():
    assert mission_state_key("LEVEL8-CENTRAL-REPOSITORY-PRESENTATION") == (
        "mission/LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
    )
