"""CLI dispatch for `readme-agent portfolio-proof` -- thin plumbing only.

Real mode-driver behavior is proven in `test_portfolio_proof_engine_modes.py` and
`test_portfolio_proof_engine_full_pipeline_modes.py`; this file proves the CLI parses correctly,
dispatches to the right mode function with the right arguments, that `--dry-run` never touches
intake/facts/candidate/provider machinery at all, and (RUNTIME-TRUTH CLOSURE item A) that a real
mode invocation actually writes `portfolio-dashboard.json` to disk -- not merely that
`build_dashboard()` returns a value in isolation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from readme_agent import commands_portfolio_proof as cpp
from readme_agent.supervisor.portfolio_proof_engine import registry_cohort
from readme_agent.supervisor.portfolio_proof_engine.contracts import campaign_id_for_mode
from readme_agent.supervisor.portfolio_proof_engine.dashboard import PortfolioDashboardV1
from readme_agent.supervisor.portfolio_proof_engine.mode_shared import ModePassResultV1
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import write_receipt
from tests.unit.portfolio_proof_engine_fixtures import make_entry, make_receipt


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


def _fake_result(mode: str, output_root: Path, **overrides) -> ModePassResultV1:
    return ModePassResultV1(mode=mode, campaign_id="c" * 64, output_root=output_root, **overrides)


def test_max_provider_concurrency_below_one_is_rejected(capsys):
    exit_code = cpp.cmd_portfolio_proof(_args(max_provider_concurrency=0))
    assert exit_code == 2
    assert "max-provider-concurrency" in capsys.readouterr().err


def test_dry_run_never_calls_a_mode_driver(monkeypatch, capsys):
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


def test_dry_run_never_writes_a_dashboard(tmp_path, monkeypatch):
    entries = [make_entry(org_repo="acme/widget", repository_id=1)]
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    output_root = tmp_path / "proof"
    exit_code = cpp.cmd_portfolio_proof(
        _args(mode="preflight", dry_run=True, output_root=str(output_root))
    )
    assert exit_code == 0
    assert not (output_root / cpp.DASHBOARD_FILENAME).exists()


def test_a_real_mode_invocation_writes_a_valid_dashboard_to_disk(tmp_path, monkeypatch, capsys):
    """The exact property `build_dashboard()` in isolation cannot prove: that going through
    `cmd_portfolio_proof` for a real (non-dry-run) mode leaves a real, re-parseable
    `portfolio-dashboard.json` sitting at the mode's own output root."""

    entries = [
        make_entry(org_repo="acme/widget", repository_id=1),
        make_entry(org_repo="acme/gadget", repository_id=2),
    ]
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    output_root = tmp_path / "proof"

    def _fake_run_preflight(**kwargs):
        assert kwargs["output_root"] == output_root
        receipts = [
            make_receipt(org_repo="acme/widget", stage="INTAKE"),
            make_receipt(org_repo="acme/gadget", stage="TERMINAL_SKIPPED"),
        ]
        for receipt in receipts:
            write_receipt(output_root, campaign_id_for_mode("preflight"), receipt)
        return _fake_result("preflight", output_root, receipts=receipts)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode="preflight", output_root=str(output_root)))
    assert exit_code == 0

    dashboard_path = output_root / cpp.DASHBOARD_FILENAME
    assert dashboard_path.is_file(), "cmd_portfolio_proof must leave a real file on disk"
    on_disk = PortfolioDashboardV1.model_validate_json(dashboard_path.read_text(encoding="utf-8"))
    assert on_disk.summary.total == 2
    assert on_disk.summary.terminal_skipped == 1

    out = capsys.readouterr().out
    assert str(dashboard_path) in out
    assert "accepted_30_of_30=" in out


def test_dashboard_write_is_atomic_and_deterministic(tmp_path, monkeypatch):
    """Two builds against identical on-disk receipts must produce byte-identical JSON -- no live
    timestamp or nondeterministic ordering leaking into the written file."""

    entries = [make_entry(org_repo="acme/widget", repository_id=1)]
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    output_root = tmp_path / "proof"
    write_receipt(
        output_root,
        campaign_id_for_mode("preflight"),
        make_receipt(org_repo="acme/widget", stage="INTAKE"),
    )

    def _fake_run_preflight(**kwargs):
        return _fake_result("preflight", output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )
    dashboard_path = output_root / cpp.DASHBOARD_FILENAME
    cpp.cmd_portfolio_proof(_args(mode="preflight", output_root=str(output_root)))
    first_bytes = dashboard_path.read_bytes()
    cpp.cmd_portfolio_proof(_args(mode="preflight", output_root=str(output_root)))
    second_bytes = dashboard_path.read_bytes()
    assert first_bytes == second_bytes


def test_dashboard_construction_failure_returns_nonzero_and_no_success_claim(
    tmp_path, monkeypatch, capsys
):
    output_root = tmp_path / "proof"

    def _fake_run_preflight(**kwargs):
        return _fake_result("preflight", output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )

    def _broken_build_dashboard(**kwargs):
        raise RuntimeError("simulated evidence read failure")

    monkeypatch.setattr(cpp, "build_dashboard", _broken_build_dashboard)
    exit_code = cpp.cmd_portfolio_proof(_args(mode="preflight", output_root=str(output_root)))
    assert exit_code != 0
    assert "dashboard construction failed" in capsys.readouterr().err
    assert not (output_root / cpp.DASHBOARD_FILENAME).exists()


def test_dashboard_revalidation_failure_returns_nonzero(tmp_path, monkeypatch, capsys):
    """Even if a file gets written, `cmd_portfolio_proof` must not claim success unless it
    re-parses as a valid dashboard -- proven by corrupting the write step itself."""

    output_root = tmp_path / "proof"

    def _fake_run_preflight(**kwargs):
        return _fake_result("preflight", output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )

    def _corrupting_write(path, data):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{not valid json", encoding="utf-8")

    monkeypatch.setattr(cpp, "write_redacted_json", _corrupting_write)
    exit_code = cpp.cmd_portfolio_proof(_args(mode="preflight", output_root=str(output_root)))
    assert exit_code != 0
    assert "failed re-validation" in capsys.readouterr().err


def test_serial_provider_execution_is_reported_honestly(tmp_path, monkeypatch, capsys):
    output_root = tmp_path / "proof"

    def _fake_run_preflight(**kwargs):
        return _fake_result("preflight", output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )
    exit_code = cpp.cmd_portfolio_proof(
        _args(mode="preflight", output_root=str(output_root), max_provider_concurrency=2)
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "provider execution is serial" in out
    assert "not yet enforced" in out


def test_pending_repositories_print_a_resume_command(tmp_path, monkeypatch, capsys):
    output_root = tmp_path / "proof"

    def _fake_run_facts_only(**kwargs):
        return _fake_result(
            "facts-only",
            output_root,
            targeted_count=2,
            completed_count=1,
            pending_count=1,
            pending_org_repos=("acme/pending",),
        )

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_facts_only",
        _fake_run_facts_only,
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode="facts-only", output_root=str(output_root)))
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "resume with" in out
    assert "--mode facts-only --only acme/pending" in out


def test_preflight_mode_dispatches_to_run_preflight(tmp_path, monkeypatch):
    captured = {}
    output_root = tmp_path / "proof"

    def _fake_run_preflight(**kwargs):
        captured.update(kwargs)
        return _fake_result("preflight", kwargs.get("output_root") or output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_preflight",
        _fake_run_preflight,
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode="preflight", output_root=str(output_root)))
    assert exit_code == 0
    assert "max_deterministic_workers" in captured


def test_facts_only_mode_dispatches_to_run_facts_only(tmp_path, monkeypatch):
    captured = {}
    output_root = tmp_path / "proof"

    def _fake(**kwargs):
        captured.update(kwargs)
        return _fake_result("facts-only", output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_facts_only", _fake
    )
    exit_code = cpp.cmd_portfolio_proof(
        _args(mode="facts-only", deadline_seconds=120.0, output_root=str(output_root))
    )
    assert exit_code == 0
    assert captured["deadline"] is not None
    assert captured["deadline"].total_seconds == 120.0


def test_facts_only_mode_passes_only_platform_family_through(tmp_path, monkeypatch):
    """CLI-to-runner wiring for item C: `--only`/`--platform`/`--family` must actually reach
    `run_facts_only`, not be silently dropped."""

    captured = {}
    output_root = tmp_path / "proof"

    def _fake(**kwargs):
        captured.update(kwargs)
        return _fake_result("facts-only", output_root)

    monkeypatch.setattr(
        "readme_agent.supervisor.portfolio_proof_engine.modes.run_facts_only", _fake
    )
    exit_code = cpp.cmd_portfolio_proof(
        _args(
            mode="facts-only",
            only="acme/a, acme/b",
            platform="python",
            family="widgets",
            output_root=str(output_root),
        )
    )
    assert exit_code == 0
    assert captured["only"] == ["acme/a", "acme/b"]
    assert captured["platform"] == "python"
    assert captured["family"] == "widgets"


@pytest.mark.parametrize(
    ("mode", "function_name"),
    [
        ("canaries", "run_canaries"),
        ("fleet", "run_fleet"),
        ("failed-only", "run_failed_only"),
    ],
)
def test_full_pipeline_modes_dispatch_correctly(tmp_path, monkeypatch, mode, function_name):
    captured = {}
    output_root = tmp_path / "proof"

    def _fake(**kwargs):
        captured.update(kwargs)
        return _fake_result(mode, output_root)

    monkeypatch.setattr(
        f"readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes.{function_name}",
        _fake,
    )
    exit_code = cpp.cmd_portfolio_proof(_args(mode=mode, output_root=str(output_root)))
    assert exit_code == 0
    assert captured  # the mode function was actually invoked with some kwargs
