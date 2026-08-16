"""Tests for binding visible canaries to one current small mission goal."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from readme_agent.errors import ConfigError
from readme_agent.state.schema import MissionExecutionStateV1, RunStateV1
from readme_agent.supervisor.approach_control import start_approach_attempt
from readme_agent.supervisor.mission_control import mission_state_key
from readme_agent.supervisor.mission_execution_guard import require_visible_execution_binding
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_GRAPH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
TASK_ID = "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
REPOSITORY = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python"


@pytest.fixture
def GRAPH(tmp_path):
    """These tests exercise L8-VPY-03A/L8-VPY-03-ALL, now durably CLOSED and
    retired to the deferred catalog. Reactivate them in a throwaway test-local
    graph copy so the guard's real repository_scope-membership behavior
    (narrow literal list vs. `platform:Python`) is still exercised faithfully,
    rather than substituting a currently-active task with different scope
    shape and silently narrowing what these tests verify."""

    raw = yaml.safe_load(REAL_GRAPH.read_text(encoding="utf-8"))
    deferred_catalog_path = REPO_ROOT / raw["deferred_task_catalog"]["path"]
    catalog_lines = [
        line for line in deferred_catalog_path.read_text(encoding="utf-8").splitlines() if line
    ]

    wanted = {"L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES", "L8-VPY-03-ALL-PYTHON-VERIFIED-POC"}
    kept_lines = []
    kept_index = []
    reactivated_tasks = []
    for line, index_entry in zip(catalog_lines, raw["deferred_task_index"], strict=True):
        if index_entry["task_id"] in wanted:
            task = dict(json.loads(line)["task"])
            task["status"] = "TODO"
            reactivated_tasks.append(task)
        else:
            kept_lines.append(line)
            kept_index.append(index_entry)
    assert {task["task_id"] for task in reactivated_tasks} == wanted

    raw["taskcards"].extend(reactivated_tasks)
    raw["deferred_task_index"] = kept_index

    catalog_path = tmp_path / "reactivated-deferred-catalog.jsonl"
    catalog_path.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""), encoding="utf-8")
    raw["deferred_task_catalog"] = {
        "path": catalog_path.name,
        "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "record_count": len(kept_lines),
    }

    graph_path = tmp_path / "reactivated-graph.yaml"
    graph_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return graph_path


class _LoadBackend:
    def __init__(self, key: str, record: RunStateV1):
        self.key = key
        self.record = record

    def load(self, org_repo: str):
        return self.record if org_repo == self.key else None


def _backend(
    graph_path,
    *,
    now: datetime,
    expires_in: timedelta = timedelta(minutes=30),
    task_id: str = TASK_ID,
):
    graph, graph_sha256 = load_mission_graph(graph_path)
    task = next(item for item in graph.taskcards if item.task_id == task_id)
    statuses = {item.task_id: "TODO" for item in graph.taskcards}
    statuses[task_id] = "IN_PROGRESS"
    approach = start_approach_attempt(
        MissionExecutionStateV1(
            mission_id=graph.mission_authority.mission_id,
            graph_sha256=graph_sha256,
            task_statuses=statuses,
        ).approach_control,
        task,
        now=now,
    )
    state = MissionExecutionStateV1(
        mission_id=graph.mission_authority.mission_id,
        graph_sha256=graph_sha256,
        task_statuses=statuses,
        active_task_id=task_id,
        claim_id="claim",
        claimed_by="codex",
        claimed_at=now.isoformat(),
        claim_expires_at=(now + expires_in).isoformat(),
        approach_control=approach,
    )
    key = mission_state_key(graph.mission_authority.mission_id)
    return _LoadBackend(key, RunStateV1(org_repo=key, mission_execution=state))


def test_current_claimed_pdf_goal_is_admitted(GRAPH):
    now = datetime(2026, 8, 8, tzinfo=UTC)
    assert (
        require_visible_execution_binding(
            _backend(GRAPH, now=now),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )
        == "DELIVERY-PY-PDF-CURRENT"
    )


def test_wrong_repository_is_rejected_before_runtime(GRAPH):
    now = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="outside immediate goal"):
        require_visible_execution_binding(
            _backend(GRAPH, now=now),
            task_id=TASK_ID,
            repository="aspose-page-foss/Aspose.Page-FOSS-for-Python",
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )


def test_expired_claim_is_rejected_before_runtime(GRAPH):
    now = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="claim expired"):
        require_visible_execution_binding(
            _backend(GRAPH, now=now, expires_in=timedelta()),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )


def test_foreign_observer_is_rejected_before_runtime(GRAPH):
    now = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="claimed by"):
        require_visible_execution_binding(
            _backend(GRAPH, now=now),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="different-agent",
            graph_path=GRAPH,
            now=now,
        )


def test_platform_scoped_task_admits_a_python_repository_not_named_literally(GRAPH):
    """Regression: L8-VPY-03-ALL-PYTHON-VERIFIED-POC scopes to `platform:Python`, not a
    literal repository list. The guard used to do a plain `repository not in
    repository_scope` membership check, so every real Python repository under this task
    failed with "is outside immediate goal" even though the taskcard's own repository_scope
    is `['platform:Python']` by design.
    """

    task_id = "L8-VPY-03-ALL-PYTHON-VERIFIED-POC"
    now = datetime(2026, 8, 11, tzinfo=UTC)
    assert (
        require_visible_execution_binding(
            _backend(GRAPH, now=now, task_id=task_id),
            task_id=task_id,
            repository="aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )
        == "DELIVERY-PY-REMAINING-COHORT"
    )


def test_platform_scoped_task_rejects_a_repository_on_a_different_platform(GRAPH):
    task_id = "L8-VPY-03-ALL-PYTHON-VERIFIED-POC"
    now = datetime(2026, 8, 11, tzinfo=UTC)
    with pytest.raises(ConfigError, match="outside immediate goal"):
        require_visible_execution_binding(
            _backend(GRAPH, now=now, task_id=task_id),
            task_id=task_id,
            repository="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )


def test_fifteen_minute_stall_is_rejected_before_runtime(GRAPH):
    started_at = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="15 minutes without material narrowing"):
        require_visible_execution_binding(
            _backend(GRAPH, now=started_at),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="codex",
            graph_path=GRAPH,
            now=started_at + timedelta(minutes=16),
        )
