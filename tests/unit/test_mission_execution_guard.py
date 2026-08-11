"""Tests for binding visible canaries to one current small mission goal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from readme_agent.errors import ConfigError
from readme_agent.state.schema import MissionExecutionStateV1, RunStateV1
from readme_agent.supervisor.approach_control import start_approach_attempt
from readme_agent.supervisor.mission_control import mission_state_key
from readme_agent.supervisor.mission_execution_guard import require_visible_execution_binding
from readme_agent.supervisor.mission_graph import load_mission_graph

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH = (
    REPO_ROOT / "plans" / "investigations" / "control" / "level8-autonomous-mission-task-graph.yaml"
)
TASK_ID = "L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES"
REPOSITORY = "aspose-pdf-foss/Aspose-PDF-FOSS-for-Python"


class _LoadBackend:
    def __init__(self, key: str, record: RunStateV1):
        self.key = key
        self.record = record

    def load(self, org_repo: str):
        return self.record if org_repo == self.key else None


def _backend(
    *, now: datetime, expires_in: timedelta = timedelta(minutes=30), task_id: str = TASK_ID
):
    graph, graph_sha256 = load_mission_graph(GRAPH)
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


def test_current_claimed_pdf_goal_is_admitted():
    now = datetime(2026, 8, 8, tzinfo=UTC)
    assert (
        require_visible_execution_binding(
            _backend(now=now),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )
        == "DELIVERY-PY-PDF-CURRENT"
    )


def test_wrong_repository_is_rejected_before_runtime():
    now = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="outside immediate goal"):
        require_visible_execution_binding(
            _backend(now=now),
            task_id=TASK_ID,
            repository="aspose-page-foss/Aspose.Page-FOSS-for-Python",
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )


def test_expired_claim_is_rejected_before_runtime():
    now = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="claim expired"):
        require_visible_execution_binding(
            _backend(now=now, expires_in=timedelta()),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )


def test_foreign_observer_is_rejected_before_runtime():
    now = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="claimed by"):
        require_visible_execution_binding(
            _backend(now=now),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="different-agent",
            graph_path=GRAPH,
            now=now,
        )


def test_platform_scoped_task_admits_a_python_repository_not_named_literally():
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
            _backend(now=now, task_id=task_id),
            task_id=task_id,
            repository="aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )
        == "DELIVERY-PY-REMAINING-COHORT"
    )


def test_platform_scoped_task_rejects_a_repository_on_a_different_platform():
    task_id = "L8-VPY-03-ALL-PYTHON-VERIFIED-POC"
    now = datetime(2026, 8, 11, tzinfo=UTC)
    with pytest.raises(ConfigError, match="outside immediate goal"):
        require_visible_execution_binding(
            _backend(now=now, task_id=task_id),
            task_id=task_id,
            repository="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
            observer="codex",
            graph_path=GRAPH,
            now=now,
        )


def test_fifteen_minute_stall_is_rejected_before_runtime():
    started_at = datetime(2026, 8, 8, tzinfo=UTC)
    with pytest.raises(ConfigError, match="15 minutes without material narrowing"):
        require_visible_execution_binding(
            _backend(now=started_at),
            task_id=TASK_ID,
            repository=REPOSITORY,
            observer="codex",
            graph_path=GRAPH,
            now=started_at + timedelta(minutes=16),
        )
