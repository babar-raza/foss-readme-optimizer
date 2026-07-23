"""Legacy CLI verbs are read-only façades over canonical supervision."""

import argparse

from readme_agent.cli import _build_parser
from readme_agent.commands import cmd_generate, cmd_run, cmd_run_registry
from readme_agent.supervisor.models import SuperviseResult
from readme_agent.supervisor.task import TaskGraph


def _converged(repo: str) -> SuperviseResult:
    return SuperviseResult(
        status="CONVERGED_NO_CHANGE",
        org_repo=repo,
        task_graph=TaskGraph(),
    )


def test_generate_routes_to_read_only_supervisor(monkeypatch):
    from readme_agent.supervisor import loop

    captured = {}

    def _supervise(repo, **kwargs):
        captured.update(kwargs)
        return _converged(repo)

    monkeypatch.setattr(loop, "supervise_repo", _supervise)

    result = cmd_generate(argparse.Namespace(repo="acme/widget", force_regenerate=True))

    assert result == 0
    assert captured["allowed_permission_classes"] == {
        "read_only_local",
        "read_only_network",
    }


def test_run_full_mode_cannot_bypass_effect_boundary(monkeypatch):
    from readme_agent.supervisor import loop

    captured = {}

    def _supervise(repo, **kwargs):
        captured.update(kwargs)
        return _converged(repo)

    monkeypatch.setattr(loop, "supervise_repo", _supervise)

    result = cmd_run(
        argparse.Namespace(
            repo="acme/widget",
            mode="full",
            durable_state=False,
            force_regenerate=True,
        )
    )

    assert result == 0
    assert captured["allowed_permission_classes"] == {
        "read_only_local",
        "read_only_network",
    }


def test_registry_returns_nonzero_when_any_supervisor_run_is_blocked(monkeypatch):
    from readme_agent.registry import loader
    from readme_agent.supervisor import loop

    entry = argparse.Namespace(org_repo="acme/widget")
    monkeypatch.setattr(loader, "enabled_entries", lambda: [entry])
    monkeypatch.setattr(
        loop,
        "supervise_repo",
        lambda repo, **kwargs: SuperviseResult(
            status="BLOCKED",
            org_repo=repo,
            task_graph=TaskGraph(),
            blocked_reason="specialist_failed",
        ),
    )

    result = cmd_run_registry(argparse.Namespace(only=None, durable_state=False))

    assert result == 1


def test_top_level_help_identifies_all_legacy_verbs_as_read_only_facades():
    help_text = _build_parser().format_help()

    assert help_text.count("[read-only compatibility façade]") == 3
    assert "legacy `run` engine" not in help_text
