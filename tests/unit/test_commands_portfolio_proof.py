"""CLI dispatch for `readme-agent portfolio-proof` -- thin plumbing only.

Real mode-driver behavior is proven in `test_portfolio_proof_engine_modes.py` and
`test_portfolio_proof_engine_full_pipeline_modes.py`; this file proves only that the CLI parses
correctly, dispatches to the right mode function with the right arguments, and that `--dry-run`
never touches intake/facts/candidate/provider machinery at all.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from readme_agent import commands_portfolio_proof as cpp
from readme_agent.supervisor.portfolio_proof_engine.mode_shared import ModePassResultV1
from tests.unit.portfolio_proof_engine_fixtures import make_entry


def _args(**overrides):
    base = dict(
        mode="preflight",
        registry="data/products.json",
        only=None,
        platform=None,
        family=None,
        deadline_seconds=None,
        per_stage_timeout_seconds=None,
        max_deterministic_workers=1,
        max_provider_concurrency=2,
        output_root=None,
        dry_run=False,
        resume=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_max_provider_concurrency_below_one_is_rejected(capsys):
    exit_code = cpp.cmd_portfolio_proof(_args(max_provider_concurrency=0))
    assert exit_code == 2
    assert "max-provider-concurrency" in capsys.readouterr().err


def test_dry_run_never_calls_a_mode_driver(monkeypatch, capsys):
    from readme_agent.supervisor.portfolio_proof_engine import registry_cohort

    entries = [make_entry(org_repo="acme/widget", repository_id=1)]
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))

    called = []
    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        lambda **kwargs: called.append(kwargs),
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode="preflight", dry_run=True))
    assert exit_code == 0
    assert called == []
    assert "acme/widget" in capsys.readouterr().out


def test_preflight_mode_dispatches_to_run_preflight(monkeypatch):
    captured = {}

    def _fake_run_preflight(**kwargs):
        captured.update(kwargs)
        return ModePassResultV1(
            mode="preflight",
            campaign_id="c" * 64,
            output_root=kwargs.get("output_root") or Path("."),
        )

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode="preflight"))
    assert exit_code == 0
    assert "max_deterministic_workers" in captured


def test_facts_only_mode_dispatches_to_run_facts_only(monkeypatch):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return ModePassResultV1(mode="facts-only", campaign_id="c" * 64, output_root=Path("."))

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_facts_only", _fake
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode="facts-only", deadline_seconds=120.0))
    assert exit_code == 0
    assert captured["deadline"] is not None
    assert captured["deadline"].total_seconds == 120.0


@pytest.mark.parametrize(
    ("mode", "function_name"),
    [
        ("canaries", "run_canaries"),
        ("fleet", "run_fleet"),
        ("failed-only", "run_failed_only"),
    ],
)
def test_full_pipeline_modes_dispatch_correctly(monkeypatch, mode, function_name):
    captured = {}

    def _fake(**kwargs):
        captured.update(kwargs)
        return ModePassResultV1(mode=mode, campaign_id="c" * 64, output_root=Path("."))

    monkeypatch.setattr(
        f"readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes.{function_name}",
        _fake,
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode=mode))
    assert exit_code == 0
    assert captured  # the mode function was actually invoked with some kwargs
