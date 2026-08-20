"""PREFLIGHT mode's sole implementation: map `IntakePreflightOutcomeV1` -> proof-stage receipt.

Monkeypatches `run_readonly_intake_preflight` at the call boundary this module actually uses --
`registry/intake.py`'s own classification logic is already covered by `test_registry_intake.py`
and is not re-tested here; this file proves only the *mapping* onto `ProofStageReceiptV1`.
"""

from __future__ import annotations

from readme_agent.state.lifecycle_schema import IntakePreflightBindingV1
from readme_agent.supervisor.intake import ReadonlyIntakeExecution
from readme_agent.supervisor.portfolio_proof_engine import intake_classification
from readme_agent.supervisor.portfolio_proof_engine.intake_classification import classify_intake
from tests.unit.portfolio_proof_engine_fixtures import make_entry
from tests.unit.test_state_backend import FakeStateBackend


def _binding(*, outcome: str, reason: str = "test reason") -> IntakePreflightBindingV1:
    return IntakePreflightBindingV1(
        dedup_key="a" * 64,
        source_revision="b" * 40,
        outcome=outcome,
        result_hash="c" * 64,
        reason=reason,
        observed_by="test",
    )


def test_ready_outcome_maps_to_intake_stage(monkeypatch):
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: ReadonlyIntakeExecution(
            _binding(outcome="READY_FULL_PIPELINE"), executed=True
        ),
    )
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.stage == "INTAKE"
    assert receipt.status == "OK"
    assert receipt.source_revision == "b" * 40


def test_no_substantive_content_maps_to_terminal_skipped(monkeypatch):
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: ReadonlyIntakeExecution(
            _binding(outcome="BLOCKED_NO_SUBSTANTIVE_CONTENT"), executed=True
        ),
    )
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.stage == "TERMINAL_SKIPPED"
    assert receipt.status == "OK"


def test_not_applicable_maps_to_terminal_skipped(monkeypatch):
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: ReadonlyIntakeExecution(
            _binding(outcome="NOT_APPLICABLE"), executed=True
        ),
    )
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.stage == "TERMINAL_SKIPPED"


def test_blocked_access_maps_to_blocked_input_with_reason(monkeypatch):
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: ReadonlyIntakeExecution(
            _binding(outcome="BLOCKED_ACCESS", reason="remote unreachable"), executed=True
        ),
    )
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.stage == "BLOCKED_INPUT"
    assert receipt.status == "FAILED"
    assert receipt.failure_reason == "remote unreachable"


def test_system_failure_outcome_maps_to_system_failure(monkeypatch):
    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: ReadonlyIntakeExecution(
            _binding(outcome="SYSTEM_FAILURE", reason="crashed"), executed=True
        ),
    )
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.stage == "SYSTEM_FAILURE"
    assert receipt.status == "FAILED"


def test_an_unhandled_exception_is_classified_not_raised(monkeypatch):
    def _raise(entry, backend):
        raise RuntimeError("clone exploded")

    monkeypatch.setattr(intake_classification, "run_readonly_intake_preflight", _raise)
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.stage == "SYSTEM_FAILURE"
    assert receipt.status == "FAILED"
    assert "clone exploded" in receipt.failure_reason


def test_no_qwen_call_and_no_candidate_are_ever_made(monkeypatch):
    """PREFLIGHT's contract: `provider_call_count` is always zero regardless of outcome."""

    monkeypatch.setattr(
        intake_classification,
        "run_readonly_intake_preflight",
        lambda entry, backend: ReadonlyIntakeExecution(
            _binding(outcome="READY_FULL_PIPELINE"), executed=True
        ),
    )
    receipt = classify_intake(make_entry(), FakeStateBackend())
    assert receipt.provider_call_count == 0
    assert receipt.candidate_hash is None
