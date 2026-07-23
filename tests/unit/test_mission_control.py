"""Offline tests for the supervisor's central mission-taskcard consumer."""

import hashlib
import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from readme_agent.errors import ConfigError
from readme_agent.state.backend import SaveResult
from readme_agent.state.schema import MissionExecutionStateV1, RunStateV1
from readme_agent.supervisor.mission_control import (
    claim_next_task,
    evaluate_mission,
    mission_state_key,
    persist_evaluation,
    transition_task,
)
from readme_agent.supervisor.mission_graph import load_mission_graph

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


def test_real_level8_graph_is_schema_valid_and_acyclic():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)

    assert graph.mission_authority.mission_id == "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
    assert graph.autonomous_execution_contract.mechanism_locked is True
    assert len(graph.taskcards) == 17
    assert len(graph_hash) == 64
    tasks = {task.task_id: task for task in graph.taskcards}
    local_wave3 = tasks["L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION"]
    assert local_wave3.dependencies == ["L8-WAVE1-CANONICAL-SAFETY-SPINE"]
    assert (
        "L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION"
        in tasks["L8-WAVE3-PRODUCT-TRUTH-OWNERSHIP"].dependencies
    )
    local_wave4 = tasks["L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION"]
    assert local_wave4.dependencies == ["L8-WAVE3-LOCAL-PRODUCT-TRUTH-FOUNDATION"]
    assert (
        "L8-WAVE4-LOCAL-PRESENTATION-PLAN-FOUNDATION"
        in tasks["L8-WAVE4-PRESENTATION-INTELLIGENCE"].dependencies
    )
    coverage = graph.requirement_coverage
    assert coverage is not None
    assert coverage.total_requirement_rows == 390
    assert coverage.mandatory_requirement_rows == 367
    assert coverage.reopened_implemented_rows == 0
    assert len({mapping.requirement_id for mapping in coverage.mappings}) == 390
    l8_mapping = next(
        mapping for mapping in coverage.mappings if mapping.requirement_id == "L8-011"
    )
    assert l8_mapping.task_id == "L8-WAVE8-NINETY-DAY-SELF-MAINTENANCE"
    requirements_path = REPO_ROOT / coverage.source_path
    assert coverage.source_sha256 == hashlib.sha256(requirements_path.read_bytes()).hexdigest()


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


def test_evaluate_initializes_and_preserves_the_bootstrap_claim():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()

    first = persist_evaluation(backend, graph, graph_hash)
    second = persist_evaluation(backend, graph, graph_hash)

    assert first.state_version == 1
    assert second.state_version == 2
    state = second.mission_execution
    assert state is not None
    assert state.active_task_id == "L8-MISSION-CONTROL-CONSUMER"
    assert state.task_statuses[state.active_task_id] == "IN_PROGRESS"
    assert evaluate_mission(graph, state).mission_complete is False


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


def test_closeout_ladder_then_claims_exactly_one_dependency_ready_task():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)
    task_id = "L8-MISSION-CONTROL-CONSUMER"

    for status in ("IMPLEMENTED", "VERIFIED", "SCORED", "CLOSED"):
        record = transition_task(
            backend,
            graph,
            graph_hash,
            task_id=task_id,
            to_status=status,
            observed_by="test-verifier",
            reason=f"test transition to {status}",
            evidence_refs=[f"evidence/{status.lower()}.json"],
        )

    state = record.mission_execution
    assert state is not None
    evaluation = evaluate_mission(graph, state)
    assert [task.task_id for task in evaluation.eligible_tasks] == [
        "L8-REQUIREMENT-TO-TASKCARD-COVERAGE"
    ]

    claimed = claim_next_task(backend, graph, graph_hash, claimed_by="test-worker")
    assert claimed.mission_execution is not None
    assert claimed.mission_execution.active_task_id == "L8-REQUIREMENT-TO-TASKCARD-COVERAGE"


def test_rerouted_wave0_parent_unlocks_children_but_not_wave1():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    statuses = {task.task_id: task.status for task in graph.taskcards}
    statuses.update(
        {
            "L8-MISSION-CONTROL-CONSUMER": "CLOSED",
            "L8-REQUIREMENT-TO-TASKCARD-COVERAGE": "CLOSED",
            "L8-WAVE0-PLAN-TRUTH-RECONCILIATION": "REROUTED",
        }
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_hash,
        task_statuses=statuses,
    )

    eligible = [task.task_id for task in evaluate_mission(graph, state).eligible_tasks]

    assert eligible == [
        "L8-WAVE0-CANDIDATE-ARTIFACT-DISPOSITION",
        "L8-WAVE0-SEMANTIC-CLOSURE-EVIDENCE",
    ]
    assert "L8-WAVE1-CANONICAL-SAFETY-SPINE" not in eligible


def test_direct_close_and_closure_without_evidence_fail_closed():
    graph, graph_hash = load_mission_graph(REAL_GRAPH)
    backend = _MemoryStateBackend()
    persist_evaluation(backend, graph, graph_hash)

    with pytest.raises(ConfigError, match="invalid mission transition"):
        transition_task(
            backend,
            graph,
            graph_hash,
            task_id="L8-MISSION-CONTROL-CONSUMER",
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
            task_id="L8-MISSION-CONTROL-CONSUMER",
            to_status="IMPLEMENTED",
            observed_by="test",
            reason="no evidence",
            evidence_refs=[],
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


def test_semantically_unsupported_implemented_requirement_cannot_be_preserved(tmp_path):
    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    mapping = next(
        item
        for item in raw["requirement_coverage"]["mappings"]
        if item["requirement_status"] == "IMPLEMENTED"
        and item["disposition"] == "preserved_verified"
    )
    mapping["semantic_findings"] = ["synthetic missing semantic proof"]
    invalid = tmp_path / "invalid-closure-mission.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match="has semantic findings but was not reopened"):
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
    task = next(item for item in raw["taskcards"] if item["status"] == "BLOCKED_EXTERNAL")
    mutation(task)
    invalid = tmp_path / "invalid-external-blocker.yaml"
    invalid.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_mission_graph(invalid)


def test_state_key_is_separate_from_every_product_repository():
    assert mission_state_key("LEVEL8-CENTRAL-REPOSITORY-PRESENTATION") == (
        "mission/LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
    )
