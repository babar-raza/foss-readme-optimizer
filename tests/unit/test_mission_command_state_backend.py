"""Mission commands retain one authority across execution profiles."""

from __future__ import annotations

import argparse

import pytest


def _args(**overrides) -> argparse.Namespace:
    base = dict(
        mission_task_graph="plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
        mission_action="status",
        mission_observer="readme-agent-supervisor",
        mission_task_id=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_local_poc_profile_keeps_the_central_mission_backend(monkeypatch):
    import readme_agent.state.local_poc_backend as local_poc_backend_module
    import readme_agent.supervisor.mission_command as mission_command_module

    sentinel = object()
    monkeypatch.setattr(mission_command_module, "default_state_backend", lambda: sentinel)
    monkeypatch.setattr(
        local_poc_backend_module,
        "default_local_poc_state_backend",
        lambda: (_ for _ in ()).throw(
            AssertionError("execution-profile state must not become mission authority")
        ),
    )

    backend = mission_command_module._mission_state_backend_for_args(
        _args(execution_profile="local_poc")
    )

    assert backend is sentinel


@pytest.mark.parametrize(
    "profile_name", [None, "github_observe", "github_proposal", "act_poc", "local_poc"]
)
def test_every_profile_keeps_the_central_mission_state(monkeypatch, profile_name):
    import readme_agent.state.local_poc_backend as local_poc_backend_module
    import readme_agent.supervisor.mission_command as mission_command_module

    sentinel = object()
    monkeypatch.setattr(mission_command_module, "default_state_backend", lambda: sentinel)
    monkeypatch.setattr(
        local_poc_backend_module,
        "default_local_poc_state_backend",
        lambda: (_ for _ in ()).throw(
            AssertionError("non-local_poc mission commands must never use the local-only backend")
        ),
    )

    backend = mission_command_module._mission_state_backend_for_args(
        _args(execution_profile=profile_name)
    )

    assert backend is sentinel


def test_a_local_poc_mission_command_writes_the_central_backend(monkeypatch, tmp_path):
    """An explicit remote may isolate mission proof without profile forking."""

    import readme_agent.supervisor.mission_command as mission_command_module
    from readme_agent.gitsafety._git import run_git
    from readme_agent.supervisor.mission_control import mission_state_key
    from readme_agent.supervisor.mission_graph import load_mission_graph

    state_remote = tmp_path / "state.git"
    init = run_git(["init", "--bare", str(state_remote)], cwd=tmp_path)
    assert init.returncode == 0, init.stderr
    monkeypatch.setenv("README_AGENT_STATE_REMOTE", str(state_remote))

    exit_code = mission_command_module.run_mission_command(
        _args(execution_profile="local_poc", mission_action="evaluate")
    )
    assert exit_code == 0

    from pathlib import Path

    from readme_agent.state.git_backend import default_state_backend

    graph, _ = load_mission_graph(
        Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")
    )
    record = default_state_backend().load(mission_state_key(graph.mission_authority.mission_id))
    assert record is not None
    assert record.mission_execution is not None
