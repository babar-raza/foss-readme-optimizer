"""PREFLIGHT and FACTS-ONLY mode drivers -- fakes only, zero network/LLM/state effect on the
real repository. `full_pipeline_modes.py` (canaries/fleet/failed-only) has its own test file.
"""

from __future__ import annotations

import argparse

from readme_agent.state.lifecycle_schema import IntakePreflightBindingV1, ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.intake import ReadonlyIntakeExecution
from readme_agent.supervisor.portfolio_proof_engine import intake_classification, registry_cohort
from readme_agent.supervisor.portfolio_proof_engine.deadline import DeadlineBudget
from readme_agent.supervisor.portfolio_proof_engine.modes import run_facts_only, run_preflight
from tests.unit.portfolio_proof_engine_fixtures import make_entry
from tests.unit.test_state_backend import FakeStateBackend


def _ready_binding(revision: str = "a" * 40) -> ReadonlyIntakeExecution:
    return ReadonlyIntakeExecution(
        IntakePreflightBindingV1(
            dedup_key="a" * 64,
            source_revision=revision,
            outcome="READY_FULL_PIPELINE",
            result_hash="b" * 64,
            reason="ok",
            observed_by="test",
        ),
        executed=True,
    )


def _skip_binding(revision: str = "a" * 40) -> ReadonlyIntakeExecution:
    return ReadonlyIntakeExecution(
        IntakePreflightBindingV1(
            dedup_key="a" * 64,
            source_revision=revision,
            outcome="BLOCKED_NO_SUBSTANTIVE_CONTENT",
            result_hash="b" * 64,
            reason="empty tree",
            observed_by="test",
        ),
        executed=True,
    )


def _entries(count: int) -> list:
    return [
        make_entry(
            org_repo=f"acme/repo{i}", repository_id=i + 1, family="widgets", platform="python"
        )
        for i in range(count)
    ]


def test_run_preflight_classifies_every_registry_entry(tmp_path, monkeypatch):
    entries = _entries(3)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: _ready_binding(),
    )
    result = run_preflight(output_root=tmp_path / "proof", state_backend=FakeStateBackend())
    assert result.mode == "preflight"
    assert len(result.receipts) == 3
    assert all(receipt.stage == "INTAKE" for receipt in result.receipts)
    assert all(receipt.provider_call_count == 0 for receipt in result.receipts)


def test_run_preflight_writes_resumable_receipts(tmp_path, monkeypatch):
    entries = _entries(1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: _ready_binding(),
    )
    output_root = tmp_path / "proof"
    first = run_preflight(output_root=output_root, state_backend=FakeStateBackend())
    second = run_preflight(output_root=output_root, state_backend=FakeStateBackend())
    assert first.campaign_id == second.campaign_id
    assert [r.stage for r in first.receipts] == [r.stage for r in second.receipts]

    from readme_agent.supervisor.portfolio_proof_engine.receipt_store import read_receipt

    stored = read_receipt(output_root, first.campaign_id, entries[0].org_repo, "INTAKE")
    assert stored is not None


def test_run_facts_only_skips_terminal_skipped_entries(tmp_path, monkeypatch):
    entries = _entries(2)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))

    def _fake_intake(entry, backend):
        return _skip_binding() if entry.org_repo == entries[0].org_repo else _ready_binding()

    monkeypatch.setattr(intake_classification, "run_readonly_intake_preflight", _fake_intake)

    backend = FakeStateBackend()
    calls: list[argparse.Namespace] = []

    def _fake_supervise(namespace: argparse.Namespace) -> int:
        calls.append(namespace)
        for org_repo in (namespace.only or "").split(","):
            org_repo = org_repo.strip()
            if not org_repo:
                continue
            backend.save(
                org_repo,
                RunStateV2(
                    org_repo=org_repo,
                    readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                        status="FACTS_READY",
                        source_revision="a" * 40,
                        facts_hash="c" * 64,
                    ),
                ),
                None,
            )
        return 0

    result = run_facts_only(
        output_root=tmp_path / "proof", state_backend=backend, supervise_call=_fake_supervise
    )
    assert len(calls) == 1
    # Only the non-skipped repository was ever passed to the underlying scheduler.
    assert calls[0].only == entries[1].org_repo
    assert calls[0].execution_profile == "local_poc"
    assert calls[0].max_readme_poc_stage == "FACTS_READY"

    facts_receipts = [r for r in result.receipts if r.stage == "FACTS_READY"]
    assert len(facts_receipts) == 1
    assert facts_receipts[0].org_repo == entries[1].org_repo
    skipped = [r for r in result.receipts if r.stage == "TERMINAL_SKIPPED"]
    assert len(skipped) == 1


def test_run_facts_only_never_makes_a_provider_call(tmp_path, monkeypatch):
    """No Qwen calls -- the FACTS-ONLY contract. Proven by construction: `run_facts_only` never
    passes a provider-calling profile/stage, and every written receipt records zero."""

    entries = _entries(1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: _ready_binding(),
    )

    def _fake_supervise(namespace: argparse.Namespace) -> int:
        assert namespace.max_readme_poc_stage == "FACTS_READY"
        return 0

    result = run_facts_only(
        output_root=tmp_path / "proof",
        state_backend=FakeStateBackend(),
        supervise_call=_fake_supervise,
    )
    assert all(receipt.provider_call_count == 0 for receipt in result.receipts)


def test_run_facts_only_respects_an_already_expired_deadline(tmp_path, monkeypatch):
    entries = _entries(1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: _ready_binding(),
    )
    calls: list[int] = []

    def _fake_supervise(namespace: argparse.Namespace) -> int:
        calls.append(1)
        return 0

    deadline = DeadlineBudget(total_seconds=0.0)
    result = run_facts_only(
        output_root=tmp_path / "proof",
        state_backend=FakeStateBackend(),
        supervise_call=_fake_supervise,
        deadline=deadline,
    )
    assert result.deadline_expired is True
    assert calls == []  # the underlying scheduler was never invoked once the deadline had passed
