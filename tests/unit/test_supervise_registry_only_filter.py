"""`supervise --registry ... --only` -- the one small, additive extension to the existing
portfolio scheduler this task makes, so the portfolio proof engine can drive a registry-derived
cohort (e.g. the seven-ecosystem canaries) through the real scheduler without teaching it new
vocabulary. Every other resume/cache/blocked-decision/time-budget/summary behavior is exercised
elsewhere (`test_blocked_decision_portfolio_wiring.py`, `test_cli.py`) and is not re-proven here --
this file proves only that `--only` filters `entries` before the fan-out loop.
"""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest


class _FakeBackend:
    def __init__(self):
        self._state = None

    def load(self, org_repo):
        return self._state

    def save(self, org_repo, state, expected_version):
        from readme_agent.state.backend import SaveResult

        current_version = self._state.state_version if self._state else None
        new_version = (current_version or 0) + 1
        self._state = state.model_copy(update={"state_version": new_version})
        return SaveResult(outcome="saved", new_version=new_version)


@pytest.fixture()
def _two_entry_registry(monkeypatch, tmp_path):
    import readme_agent.gitsafety.clone as clone_module
    import readme_agent.paths as paths
    import readme_agent.registry.loader as loader_module
    import readme_agent.state.local_poc_backend as local_poc_backend_module
    import readme_agent.supervisor.local_poc_cache as cache_module
    import readme_agent.supervisor.registry_revision_preflight as preflight_module

    entries = (
        argparse.Namespace(
            org_repo="acme/first",
            clone_url="https://example.invalid/acme/first.git",
            ecosystem="python",
            family="widgets",
            policy_profile=None,
        ),
        argparse.Namespace(
            org_repo="acme/second",
            clone_url="https://example.invalid/acme/second.git",
            ecosystem="python",
            family="widgets",
            policy_profile=None,
        ),
    )
    monkeypatch.setattr(loader_module, "load_products", lambda path: entries)
    monkeypatch.setattr(clone_module, "remote_head_sha", lambda clone_url: "a" * 40)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        paths, "readme_poc_portfolio_summary_path", lambda: tmp_path / "summary.json"
    )
    backend = _FakeBackend()
    monkeypatch.setattr(
        local_poc_backend_module, "default_local_poc_state_backend", lambda: backend
    )
    monkeypatch.setattr(
        preflight_module,
        "prepare_registry_revision",
        lambda registry_path, state_backend, **kwargs: SimpleNamespace(
            revision=SimpleNamespace(
                revision_id="a" * 64, model_dump=lambda **kw: {"revision_id": "a" * 64}
            ),
            gate=SimpleNamespace(eligible=True, reasons=[]),
        ),
    )
    monkeypatch.setattr(
        cache_module,
        "evaluate_completed_local_poc_cache",
        lambda state, bundle_dir, **kwargs: SimpleNamespace(
            reusable=False, status=None, cache_key="d" * 64
        ),
    )
    return SimpleNamespace(entries=entries, backend=backend)


def _args(**overrides):
    base = dict(
        registry="data/products.json",
        execution_profile="local_poc",
        domain=None,
        resume_trigger_key=None,
        no_registry_heal=True,
        portfolio_time_budget_seconds=300.0,
        only=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_only_filter_restricts_the_fan_out_to_the_named_repository(
    monkeypatch, _two_entry_registry
):
    import readme_agent.commands_supervision as supervision_module
    from readme_agent.supervisor.models import SuperviseResult
    from readme_agent.supervisor.task import TaskGraph

    dispatched: list[str] = []

    def _fake_member_run(member_args):
        dispatched.append(member_args.repo)
        member_args._terminal_supervise_result = SuperviseResult(
            status="STAGE_COMPLETE",
            org_repo=member_args.repo,
            task_graph=TaskGraph(),
        )
        return 0

    monkeypatch.setattr(supervision_module, "cmd_supervise", _fake_member_run)
    exit_code = supervision_module._cmd_supervise_registry(_args(only="acme/second"))
    assert exit_code == 0
    assert dispatched == ["acme/second"]


def test_without_only_the_fan_out_covers_every_entry(monkeypatch, _two_entry_registry):
    import readme_agent.commands_supervision as supervision_module
    from readme_agent.supervisor.models import SuperviseResult
    from readme_agent.supervisor.task import TaskGraph

    dispatched: list[str] = []

    def _fake_member_run(member_args):
        dispatched.append(member_args.repo)
        member_args._terminal_supervise_result = SuperviseResult(
            status="STAGE_COMPLETE",
            org_repo=member_args.repo,
            task_graph=TaskGraph(),
        )
        return 0

    monkeypatch.setattr(supervision_module, "cmd_supervise", _fake_member_run)
    exit_code = supervision_module._cmd_supervise_registry(_args())
    assert exit_code == 0
    assert sorted(dispatched) == ["acme/first", "acme/second"]


def test_only_filter_with_multiple_comma_separated_repos(monkeypatch, _two_entry_registry):
    import readme_agent.commands_supervision as supervision_module
    from readme_agent.supervisor.models import SuperviseResult
    from readme_agent.supervisor.task import TaskGraph

    dispatched: list[str] = []

    def _fake_member_run(member_args):
        dispatched.append(member_args.repo)
        member_args._terminal_supervise_result = SuperviseResult(
            status="STAGE_COMPLETE",
            org_repo=member_args.repo,
            task_graph=TaskGraph(),
        )
        return 0

    monkeypatch.setattr(supervision_module, "cmd_supervise", _fake_member_run)
    exit_code = supervision_module._cmd_supervise_registry(_args(only="acme/first, acme/second"))
    assert exit_code == 0
    assert sorted(dispatched) == ["acme/first", "acme/second"]


def test_only_filter_matching_nothing_dispatches_nothing(monkeypatch, _two_entry_registry):
    import readme_agent.commands_supervision as supervision_module

    dispatched: list[str] = []
    monkeypatch.setattr(
        supervision_module, "cmd_supervise", lambda member_args: dispatched.append(member_args)
    )
    exit_code = supervision_module._cmd_supervise_registry(_args(only="acme/nonexistent"))
    assert exit_code == 0
    assert dispatched == []
