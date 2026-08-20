"""ProofStageReceiptV1/campaign identity contract tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from readme_agent.supervisor.portfolio_proof_engine.contracts import (
    STAGE_ORDER,
    RubricAcceptanceOutcome,
    campaign_id_for_mode,
)
from tests.unit.portfolio_proof_engine_fixtures import make_receipt


def test_campaign_id_is_stable_per_mode():
    assert campaign_id_for_mode("preflight") == campaign_id_for_mode("preflight")
    assert campaign_id_for_mode("preflight") != campaign_id_for_mode("facts-only")


def test_campaign_id_is_a_sha256_hex_digest():
    campaign_id = campaign_id_for_mode("canaries")
    assert len(campaign_id) == 64
    assert all(char in "0123456789abcdef" for char in campaign_id)


def test_ok_receipt_rejects_a_failure_reason():
    with pytest.raises(ValidationError):
        make_receipt(stage="INTAKE", status="OK", failure_reason="should not be here")


def test_failed_receipt_requires_a_failure_reason():
    with pytest.raises(ValidationError):
        make_receipt(stage="BLOCKED_INPUT", status="FAILED", failure_reason=None)


def test_org_repo_shape_is_enforced():
    with pytest.raises(ValidationError):
        make_receipt(org_repo="not-a-repo-identity")


def test_canonical_hash_is_stable_and_excludes_timestamp():
    receipt = make_receipt(stage="INTAKE")
    first = receipt.canonical_hash()
    second = receipt.model_copy(update={"generated_at": "2099-01-01T00:00:00+00:00"})
    assert first == second.canonical_hash()


def test_canonical_hash_changes_when_a_bound_field_changes():
    a = make_receipt(stage="INTAKE", facts_hash="a" * 64)
    b = make_receipt(stage="INTAKE", facts_hash="b" * 64)
    assert a.canonical_hash() != b.canonical_hash()


def test_stage_order_covers_every_literal_exactly_once():
    from readme_agent.supervisor.portfolio_proof_engine.contracts import ProofStageV1

    assert set(STAGE_ORDER) == set(ProofStageV1.__args__)
    assert len(STAGE_ORDER) == len(set(STAGE_ORDER))


def test_rubric_outcome_bounded_summary_reports_disqualifiers():
    outcome = RubricAcceptanceOutcome(
        org_repo="acme/widget",
        accepted=False,
        score=30,
        hard_disqualifier_count=1,
        missing_evidence_criteria=(),
    )
    assert "30/30" in outcome.bounded_summary()
    assert "disqualifier" in outcome.bounded_summary()


def test_rubric_outcome_accepted_summary_is_terse():
    outcome = RubricAcceptanceOutcome(
        org_repo="acme/widget", accepted=True, score=30, hard_disqualifier_count=0
    )
    assert outcome.bounded_summary() == "30/30, zero hard disqualifiers"
