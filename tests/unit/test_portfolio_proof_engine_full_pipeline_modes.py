"""CANARIES/FLEET/FAILED-ONLY mode drivers -- fakes only, never executed live by this task.

Proves: canaries dispatch one full-pipeline call per registry-resolved repository; fleet never
re-dispatches an already-ACCEPTED repository; failed-only reuses `retry_policy.py`'s fingerprint
gate end to end (refuses an unchanged-fingerprint retry, escalates two identical failures to
REASSESS_REQUIRED); the rubric wiring distinguishes ACCEPTED from RUBRIC_SCORED via the injected
`rubric_evaluator`.
"""

from __future__ import annotations

import argparse

from readme_agent import paths
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.blocked_decision_cache import record_blocked_outcome
from readme_agent.supervisor.convergence import compute_control_plane_fingerprint
from readme_agent.supervisor.local_poc_cache import current_blocked_decision_dependencies
from readme_agent.supervisor.portfolio_proof_engine import registry_cohort
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.supervisor.portfolio_proof_engine.full_pipeline_modes import (
    run_canaries,
    run_failed_only,
    run_fleet,
)
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import write_receipt
from tests.unit.portfolio_proof_engine_fixtures import make_entry, make_receipt
from tests.unit.test_state_backend import FakeStateBackend

SOURCE_REVISION = "a" * 40


def _canary_entries():
    return [
        make_entry(
            org_repo=f"canary-org/{family}-{platform}",
            family=family,
            platform=platform,
            repository_id=index + 1,
        )
        for index, (family, platform) in enumerate(registry_cohort.SEVEN_CANARY_PAIRS)
    ]


def _review_ready_supervise(backend: FakeStateBackend, calls: list):
    def _supervise(namespace: argparse.Namespace) -> int:
        calls.append(namespace)
        org_repo = namespace.only
        # CAS-compliant: a fixture repository may already have prior state (e.g. a pre-seeded
        # failed lifecycle in the failed-only tests) -- overwriting it must respect the fake
        # backend's own optimistic-concurrency contract, exactly like the real state backend.
        existing = backend.load(org_repo)
        expected_version = existing.state_version if existing is not None else None
        backend.save(
            org_repo,
            RunStateV2(
                org_repo=org_repo,
                readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                    status="AGENT_APPROVED",
                    source_revision=SOURCE_REVISION,
                    facts_hash="c" * 64,
                ),
            ),
            expected_version,
        )
        org, repo = org_repo.split("/", maxsplit=1)
        bundle = paths.readme_poc_repository_dir(org, repo, SOURCE_REVISION)
        (bundle / "review").mkdir(parents=True, exist_ok=True)
        (bundle / "review" / "factual-plan-review.json").write_text("{}", encoding="utf-8")
        (bundle / "review" / "blind-quality-review.json").write_text("{}", encoding="utf-8")
        return 0

    return _supervise


def test_run_canaries_dispatches_one_full_pipeline_call_per_canary(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    entries = _canary_entries()
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    backend = FakeStateBackend()
    calls: list[argparse.Namespace] = []

    def _rubric(org_repo: str, _backend) -> RubricAcceptanceOutcome:
        return RubricAcceptanceOutcome(
            org_repo=org_repo, accepted=True, score=30, hard_disqualifier_count=0
        )

    result = run_canaries(
        output_root=tmp_path / "proof",
        state_backend=backend,
        supervise_call=_review_ready_supervise(backend, calls),
        rubric_evaluator=_rubric,
    )
    assert len(calls) == 7
    assert {call.only for call in calls} == {entry.org_repo for entry in entries}
    assert all(call.max_readme_poc_stage is None for call in calls)
    assert all(call.execution_profile == "local_poc" for call in calls)
    assert all(receipt.stage == "ACCEPTED" for receipt in result.receipts)


def test_run_canaries_rubric_rejection_reports_rubric_scored(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    entries = _canary_entries()
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    backend = FakeStateBackend()
    calls: list[argparse.Namespace] = []

    def _rubric(org_repo: str, _backend) -> RubricAcceptanceOutcome:
        return RubricAcceptanceOutcome(
            org_repo=org_repo, accepted=False, score=27, hard_disqualifier_count=0
        )

    result = run_canaries(
        output_root=tmp_path / "proof",
        state_backend=backend,
        supervise_call=_review_ready_supervise(backend, calls),
        rubric_evaluator=_rubric,
    )
    assert all(receipt.stage == "RUBRIC_SCORED" for receipt in result.receipts)
    assert all(receipt.status == "FAILED" for receipt in result.receipts)


def test_run_fleet_never_redispatches_an_already_accepted_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    entries = [
        make_entry(org_repo="acme/accepted", repository_id=1),
        make_entry(org_repo="acme/pending", repository_id=2),
    ]
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    backend = FakeStateBackend()
    backend.save(
        "acme/accepted",
        RunStateV2(
            org_repo="acme/accepted",
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status="AGENT_APPROVED", source_revision=SOURCE_REVISION, facts_hash="c" * 64
            ),
        ),
        None,
    )
    from readme_agent.supervisor.portfolio_proof_engine.contracts import campaign_id_for_mode

    output_root = tmp_path / "proof"
    # ACCEPTED can be recorded by any prior mode pass, e.g. an earlier CANARIES run --
    # `find_accepted_receipt` checks across all five, so seed it there deliberately.
    write_receipt(
        output_root,
        campaign_id_for_mode("canaries"),
        make_receipt(org_repo="acme/accepted", stage="ACCEPTED", source_revision=SOURCE_REVISION),
    )

    calls: list[argparse.Namespace] = []
    result = run_fleet(
        output_root=output_root,
        state_backend=backend,
        supervise_call=_review_ready_supervise(backend, calls),
        rubric_evaluator=lambda org_repo, _b: RubricAcceptanceOutcome(
            org_repo=org_repo, accepted=True, score=30, hard_disqualifier_count=0
        ),
    )
    assert result.campaign_id == campaign_id_for_mode("fleet")
    assert {call.only for call in calls} == {"acme/pending"}
    assert all(receipt.org_repo != "acme/accepted" for receipt in result.receipts)


def test_run_failed_only_refuses_retry_without_a_fingerprint_change(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    entry = make_entry(org_repo="acme/broken", repository_id=1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: (entry,))
    backend = FakeStateBackend()
    backend.save(
        entry.org_repo,
        RunStateV2(
            org_repo=entry.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status="DETERMINISTIC_VALIDATION_FAILED",
                source_revision=SOURCE_REVISION,
                facts_hash="c" * 64,
            ),
        ),
        None,
    )
    org, repo = entry.org_repo.split("/", maxsplit=1)
    decision_path = paths.readme_poc_blocked_decision_path(org, repo)
    record_blocked_outcome(
        decision_path,
        org_repo=entry.org_repo,
        status="DETERMINISTIC_VALIDATION_FAILED",
        exit_code=1,
        blocked_reason="deterministic validation failed",
        blocked_category="agent_fixable",
        dependencies=current_blocked_decision_dependencies(
            org_repo=entry.org_repo,
            source_revision=SOURCE_REVISION,
            control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
            ecosystem=entry.ecosystem,
            family=entry.family,
        ),
    )

    calls: list[argparse.Namespace] = []
    result = run_failed_only(
        output_root=tmp_path / "proof",
        state_backend=backend,
        supervise_call=_review_ready_supervise(backend, calls),
    )
    assert calls == []  # no causal fingerprint change -> retry refused, nothing dispatched
    assert result.receipts == []


def test_run_failed_only_marks_reassess_required_after_two_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    entry = make_entry(org_repo="acme/broken", repository_id=1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: (entry,))
    backend = FakeStateBackend()
    backend.save(
        entry.org_repo,
        RunStateV2(
            org_repo=entry.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status="DETERMINISTIC_VALIDATION_FAILED",
                source_revision=SOURCE_REVISION,
                facts_hash="c" * 64,
            ),
        ),
        None,
    )
    org, repo = entry.org_repo.split("/", maxsplit=1)
    decision_path = paths.readme_poc_blocked_decision_path(org, repo)
    dependencies = current_blocked_decision_dependencies(
        org_repo=entry.org_repo,
        source_revision=SOURCE_REVISION,
        control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
        ecosystem=entry.ecosystem,
        family=entry.family,
    )
    record_blocked_outcome(
        decision_path,
        org_repo=entry.org_repo,
        status="X",
        exit_code=1,
        blocked_reason="same reason",
        blocked_category="agent_fixable",
        dependencies=dependencies,
    )
    record_blocked_outcome(
        decision_path,
        org_repo=entry.org_repo,
        status="X",
        exit_code=1,
        blocked_reason="same reason",
        blocked_category="agent_fixable",
        dependencies=dependencies,
    )

    calls: list[argparse.Namespace] = []
    result = run_failed_only(
        output_root=tmp_path / "proof",
        state_backend=backend,
        supervise_call=_review_ready_supervise(backend, calls),
    )
    assert calls == []
    assert len(result.receipts) == 1
    assert result.receipts[0].stage == "REASSESS_REQUIRED"


def test_run_failed_only_retries_when_the_fingerprint_changed(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    entry = make_entry(org_repo="acme/broken", repository_id=1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: (entry,))
    backend = FakeStateBackend()
    backend.save(
        entry.org_repo,
        RunStateV2(
            org_repo=entry.org_repo,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status="DETERMINISTIC_VALIDATION_FAILED",
                source_revision=SOURCE_REVISION,
                facts_hash="c" * 64,
            ),
        ),
        None,
    )
    org, repo = entry.org_repo.split("/", maxsplit=1)
    decision_path = paths.readme_poc_blocked_decision_path(org, repo)
    record_blocked_outcome(
        decision_path,
        org_repo=entry.org_repo,
        status="X",
        exit_code=1,
        blocked_reason="stale reason",
        blocked_category="agent_fixable",
        dependencies=current_blocked_decision_dependencies(
            org_repo=entry.org_repo,
            # Different from the lifecycle's current SOURCE_REVISION below -- `run_failed_only`
            # compares against the *already-bound* lifecycle revision, not a fresh network probe.
            source_revision="b" * 40,
            control_plane_fingerprint=compute_control_plane_fingerprint(entry.policy_profile),
            ecosystem=entry.ecosystem,
            family=entry.family,
        ),
    )

    calls: list[argparse.Namespace] = []
    result = run_failed_only(
        output_root=tmp_path / "proof",
        state_backend=backend,
        supervise_call=_review_ready_supervise(backend, calls),
        rubric_evaluator=lambda org_repo, _b: RubricAcceptanceOutcome(
            org_repo=org_repo, accepted=True, score=30, hard_disqualifier_count=0
        ),
    )
    assert len(calls) == 1
    assert calls[0].only == entry.org_repo
    assert any(receipt.stage == "ACCEPTED" for receipt in result.receipts)
