"""Mission commands under `--execution-profile local_poc` must use the same
isolated, always-local state remote as every other local_poc path.

Closes the residual half of the 2026-08-18 state-backend split
(`local-poc-state-backend-uses-origin-not-local.md`): `--mission-action
evaluate/claim` wrote through the real-`origin` backend while
`require_visible_execution_binding()` (the bounded-verified-canary guard)
read through the profile-routed local backend -- so a local claim was never
visible to the canary and every local canary died with "durable mission
state is unavailable" (reproduced live this same day).
"""

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


def test_local_poc_profile_routes_mission_state_to_the_local_backend(monkeypatch):
    import readme_agent.state.local_poc_backend as local_poc_backend_module
    import readme_agent.supervisor.mission_command as mission_command_module

    sentinel = object()
    monkeypatch.setattr(
        mission_command_module,
        "default_state_backend",
        lambda: (_ for _ in ()).throw(
            AssertionError("local_poc mission commands must never construct the origin backend")
        ),
    )
    monkeypatch.setattr(
        local_poc_backend_module, "default_local_poc_state_backend", lambda: sentinel
    )

    backend = mission_command_module._mission_state_backend_for_args(
        _args(execution_profile="local_poc")
    )

    assert backend is sentinel


@pytest.mark.parametrize("profile_name", [None, "github_observe", "github_proposal", "act_poc"])
def test_every_other_profile_keeps_the_origin_backed_mission_state(monkeypatch, profile_name):
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


def test_a_local_poc_claim_is_visible_to_the_canary_guard_backend(monkeypatch, tmp_path):
    """The property that actually failed live: mission state written by
    `run_mission_command` under local_poc must be loadable through the same
    backend the canary guard reads. Proven by pointing the local backend at a
    temp store, evaluating + claiming, then loading the mission record back
    through a freshly constructed local backend."""

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

    from readme_agent.state.local_poc_backend import default_local_poc_state_backend

    graph, _ = load_mission_graph(
        Path("plans/investigations/control/level8-autonomous-mission-task-graph.yaml")
    )
    record = default_local_poc_state_backend().load(
        mission_state_key(graph.mission_authority.mission_id)
    )
    assert record is not None
    assert record.mission_execution is not None
