"""Stage classification from durable lifecycle state alone (plus review-artifact existence).

Proves: hash changes invalidate only the dependent receipt fields (never a rewrite of unrelated
history); a missing lifecycle fails closed to SOURCE_BOUND/FAILED rather than guessing; the
FACTUAL_REVIEWED/VISITOR_REVIEWED split and the RUBRIC_SCORED/ACCEPTED split via `rubric_result`.
"""

from __future__ import annotations

from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.supervisor.portfolio_proof_engine.stage_classifier import (
    classify_repository_stage,
)
from tests.unit.test_state_backend import FakeStateBackend

ORG_REPO = "acme/widget"
SOURCE_REVISION = "a" * 40
FACTS_HASH = "b" * 64
CONTRACT_HASH = "c" * 64


def _backend(status: str, **lifecycle_overrides: object) -> FakeStateBackend:
    defaults: dict[str, object] = {
        "source_revision": SOURCE_REVISION,
        "facts_hash": FACTS_HASH,
        "fact_acceptance_contract_hash": CONTRACT_HASH,
    }
    backend = FakeStateBackend()
    backend.save(
        ORG_REPO,
        RunStateV2(
            org_repo=ORG_REPO,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status=status, **{**defaults, **lifecycle_overrides}
            ),
        ),
        None,
    )
    return backend


def test_no_lifecycle_observed_fails_closed_to_source_bound_failed():
    receipt = classify_repository_stage(ORG_REPO, FakeStateBackend())
    assert receipt.stage == "SOURCE_BOUND"
    assert receipt.status == "FAILED"


def test_facts_ready_status_maps_to_facts_ready_stage():
    receipt = classify_repository_stage(ORG_REPO, _backend("FACTS_READY"))
    assert receipt.stage == "FACTS_READY"
    assert receipt.status == "OK"
    assert receipt.facts_hash == FACTS_HASH


def test_candidate_generated_maps_to_candidate_assembled():
    receipt = classify_repository_stage(ORG_REPO, _backend("CANDIDATE_GENERATED"))
    assert receipt.stage == "CANDIDATE_ASSEMBLED"
    assert receipt.status == "OK"


def test_deterministic_validated_status_maps_directly():
    receipt = classify_repository_stage(ORG_REPO, _backend("DETERMINISTIC_VALIDATED"))
    assert receipt.stage == "DETERMINISTIC_VALIDATED"
    assert receipt.status == "OK"


def test_deterministic_validation_failed_reports_candidate_assembled_failed():
    receipt = classify_repository_stage(ORG_REPO, _backend("DETERMINISTIC_VALIDATION_FAILED"))
    assert receipt.stage == "CANDIDATE_ASSEMBLED"
    assert receipt.status == "FAILED"
    assert receipt.failure_reason


def test_blocked_fact_conflict_maps_to_blocked_input():
    receipt = classify_repository_stage(ORG_REPO, _backend("BLOCKED_FACT_CONFLICT"))
    assert receipt.stage == "BLOCKED_INPUT"
    assert receipt.status == "FAILED"


def test_system_failure_status_maps_directly():
    receipt = classify_repository_stage(ORG_REPO, _backend("SYSTEM_FAILURE"))
    assert receipt.stage == "SYSTEM_FAILURE"
    assert receipt.status == "FAILED"


def test_agent_approved_without_review_files_stays_deterministic_validated(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    receipt = classify_repository_stage(ORG_REPO, _backend("AGENT_APPROVED"))
    assert receipt.stage == "DETERMINISTIC_VALIDATED"


def test_agent_approved_with_factual_review_file_reports_factual_reviewed(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    from readme_agent import paths

    bundle = paths.readme_poc_repository_dir("acme", "widget", SOURCE_REVISION)
    (bundle / "review").mkdir(parents=True)
    (bundle / "review" / "factual-plan-review.json").write_text("{}", encoding="utf-8")

    receipt = classify_repository_stage(ORG_REPO, _backend("AGENT_APPROVED"))
    assert receipt.stage == "FACTUAL_REVIEWED"


def test_agent_approved_with_both_review_files_reports_visitor_reviewed(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    from readme_agent import paths

    bundle = paths.readme_poc_repository_dir("acme", "widget", SOURCE_REVISION)
    (bundle / "review").mkdir(parents=True)
    (bundle / "review" / "factual-plan-review.json").write_text("{}", encoding="utf-8")
    (bundle / "review" / "blind-quality-review.json").write_text("{}", encoding="utf-8")

    receipt = classify_repository_stage(ORG_REPO, _backend("AGENT_APPROVED"))
    assert receipt.stage == "VISITOR_REVIEWED"


def test_rubric_accepted_outcome_promotes_to_accepted():
    outcome = RubricAcceptanceOutcome(
        org_repo=ORG_REPO, accepted=True, score=30, hard_disqualifier_count=0
    )
    receipt = classify_repository_stage(ORG_REPO, _backend("NO_OP_PROVEN"), rubric_result=outcome)
    assert receipt.stage == "ACCEPTED"
    assert receipt.status == "OK"


def test_rubric_rejected_outcome_reports_rubric_scored_failed():
    outcome = RubricAcceptanceOutcome(
        org_repo=ORG_REPO, accepted=False, score=28, hard_disqualifier_count=1
    )
    receipt = classify_repository_stage(ORG_REPO, _backend("NO_OP_PROVEN"), rubric_result=outcome)
    assert receipt.stage == "RUBRIC_SCORED"
    assert receipt.status == "FAILED"
    assert "28/30" in receipt.failure_reason


def test_predecessor_hash_is_chained_into_the_receipt():
    first = classify_repository_stage(ORG_REPO, _backend("FACTS_READY"))
    second = classify_repository_stage(ORG_REPO, _backend("CANDIDATE_GENERATED"), predecessor=first)
    assert second.predecessor_receipt_hash == first.canonical_hash()


def test_changing_facts_hash_produces_a_different_receipt_identity():
    receipt_a = classify_repository_stage(ORG_REPO, _backend("FACTS_READY"))
    backend_b = _backend("FACTS_READY", facts_hash="d" * 64)
    receipt_b = classify_repository_stage(ORG_REPO, backend_b)
    assert receipt_a.canonical_hash() != receipt_b.canonical_hash()
    # But the stage classification itself is unaffected by a hash-only change.
    assert receipt_a.stage == receipt_b.stage == "FACTS_READY"


def test_unmapped_trusted_lane_status_fails_closed_never_guesses():
    """A legacy TRUSTED_* status (out of this proof engine's verified-lane scope) is real,
    constructible lifecycle state this classifier deliberately does not map -- proving the
    fallback branch fails closed instead of silently guessing a stage for it."""

    receipt = classify_repository_stage(
        ORG_REPO,
        _backend("TRUSTED_FACTS_EXTRACTING", content_assurance="trusted_inherited"),
    )
    assert receipt.stage == "SYSTEM_FAILURE"
    assert receipt.status == "FAILED"


# ---------------------------------------------------------------------------
# Qwen section-engine integration: lifecycle stages advance only from a valid revision-bound
# section-authoring document, never from cache fragments or a narrative completion claim.
# ---------------------------------------------------------------------------


def test_section_authoring_adapter_without_evidence_returns_none():

    from readme_agent.supervisor.portfolio_proof_engine.section_authoring_adapter import (
        resolve_section_authoring_progress,
    )

    assert resolve_section_authoring_progress(ORG_REPO, SOURCE_REVISION) is None


def test_facts_ready_lifecycle_never_reports_section_packets_ready_or_sections_authored():
    for status in ("FACTS_READY", "README_ASSESSED", "PLAN_READY"):
        receipt = classify_repository_stage(ORG_REPO, _backend(status))
        assert receipt.stage == "FACTS_READY"
        assert receipt.stage not in {"SECTION_PACKETS_READY", "SECTIONS_AUTHORED"}


def test_review_ready_lifecycle_without_a_rubric_result_never_reports_accepted():
    for status in (
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_REVIEW_READY",
        "HUMAN_ACCEPTED",
        "PR_ELIGIBLE",
        "PR_PROOF_COMPLETE",
    ):
        receipt = classify_repository_stage(ORG_REPO, _backend(status))
        assert receipt.stage != "ACCEPTED"


# ---------------------------------------------------------------------------
# supervise_exit_code: the caller's own dispatch result, carried through verbatim -- this
# function never fabricates or infers it from lifecycle state.
# ---------------------------------------------------------------------------


def test_supervise_exit_code_defaults_to_none_when_the_caller_made_no_dispatch():
    receipt = classify_repository_stage(ORG_REPO, _backend("FACTS_READY"))
    assert receipt.supervise_exit_code is None


def test_supervise_exit_code_carries_through_unmodified_even_on_a_healthy_looking_stage():
    # A nonzero exit code alongside review-ready lifecycle state is exactly the split this field
    # exists to make inspectable: the repository looks fine from lifecycle state alone, but its
    # last supervise_call dispatch did not actually exit clean.
    receipt = classify_repository_stage(ORG_REPO, _backend("AGENT_APPROVED"), supervise_exit_code=3)
    assert receipt.stage == "DETERMINISTIC_VALIDATED"
    assert receipt.supervise_exit_code == 3
