"""Durable read-only intake reservation, resume, and deduplication."""

from __future__ import annotations

import pytest

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.lifecycle_schema import (
    IntakePreflightBindingV1,
    ReadmePocLifecycleStateV2,
    ReadmePocTransitionV2,
)
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.readme_poc_intake import (
    begin_readonly_intake_preflight,
    complete_readonly_intake_preflight,
    intake_preflight_dedup_key,
)
from readme_agent.state.schema import RunStateV2


class IntakeBackend:
    def __init__(self, lifecycle: ReadmePocLifecycleStateV2 | None = None):
        self.states: dict[str, RunStateV2] = {}
        self.save_count = 0
        if lifecycle is not None:
            self.states["org/repo"] = RunStateV2(
                org_repo="org/repo",
                readme_poc_lifecycle=lifecycle,
            )

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": version}
        )
        self.save_count += 1
        return SaveResult("saved", version)

    def acquire_lock(self, org_repo: str) -> Lock:
        return Lock(org_repo, "test", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        pass


def _key(revision: str = "a" * 40) -> str:
    return intake_preflight_dedup_key("org/repo", 123, revision, "c" * 64)


def test_new_repository_progresses_through_intake_and_deduplicates():
    backend = IntakeBackend()
    key = _key()

    accepted = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    binding = complete_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
        outcome="READY_FULL_PIPELINE",
        result_hash="d" * 64,
        reason="ordinary route",
        evidence_refs=["intake/preflight.json"],
    )
    saves_after_completion = backend.save_count
    duplicate = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    lifecycle = backend.load("org/repo").readme_poc_lifecycle

    assert accepted.should_execute is True
    assert binding.outcome == "READY_FULL_PIPELINE"
    assert duplicate.should_execute is False
    assert duplicate.completed == binding
    assert backend.save_count == saves_after_completion
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert lifecycle.status == "INTAKE_READY"
    assert [item.to_status for item in lifecycle.history] == [
        "INTAKE_PREFLIGHTING",
        "INTAKE_READY",
    ]
    assert len(lifecycle.intake_preflight_history) == 1


def test_interrupted_reservation_resumes_without_duplicate_transition():
    backend = IntakeBackend()
    key = _key()

    first = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    second = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    lifecycle = backend.load("org/repo").readme_poc_lifecycle

    assert first.should_execute is True
    assert second.should_execute is True
    assert second.resumed is True
    assert second.reservation == first.reservation
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert [item.to_status for item in lifecycle.history] == ["INTAKE_PREFLIGHTING"]


def test_advanced_lifecycle_keeps_its_stage_while_intake_receipt_is_added():
    backend = IntakeBackend(
        ReadmePocLifecycleStateV2(
            status="FACTS_READY",
            source_revision="a" * 40,
            facts_hash="f" * 64,
        )
    )
    key = _key()

    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    complete_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
        outcome="READY_FAST_PATH",
        result_hash="d" * 64,
        reason="preserve-first route",
        evidence_refs=["intake/preflight.json"],
    )
    lifecycle = backend.load("org/repo").readme_poc_lifecycle

    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert lifecycle.status == "FACTS_READY"
    assert lifecycle.facts_hash == "f" * 64
    assert lifecycle.history == []
    assert lifecycle.intake_preflight_history[-1].outcome == "READY_FAST_PATH"


def test_system_failure_retries_same_logical_key_with_incremented_attempt():
    backend = IntakeBackend()
    key = _key()
    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    failed = complete_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
        outcome="SYSTEM_FAILURE",
        result_hash="e" * 64,
        reason="controlled failure",
        evidence_refs=[],
    )

    retry = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )

    assert failed.attempt == 1
    assert retry.should_execute is True
    assert retry.resumed is False
    assert retry.reservation is not None
    assert retry.reservation.attempt == 2

    repaired = complete_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
        outcome="READY_FULL_PIPELINE",
        result_hash="f" * 64,
        reason="transport repaired",
        evidence_refs=["intake/preflight-a2.json"],
    )
    lifecycle = backend.load("org/repo").readme_poc_lifecycle

    assert repaired.attempt == 2
    assert repaired.outcome == "READY_FULL_PIPELINE"
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert lifecycle.status == "INTAKE_READY"
    assert [item.to_status for item in lifecycle.history] == [
        "INTAKE_PREFLIGHTING",
        "SYSTEM_FAILURE",
        "INTAKE_PREFLIGHTING",
        "INTAKE_READY",
    ]


def test_same_revision_with_changed_classification_contract_gets_new_intake():
    backend = IntakeBackend()
    revision = "a" * 40
    blocked_key = intake_preflight_dedup_key(
        "org/repo",
        123,
        revision,
        "b" * 64,
    )
    ready_key = intake_preflight_dedup_key(
        "org/repo",
        123,
        revision,
        "c" * 64,
    )
    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=blocked_key,
        source_revision=revision,
    )
    complete_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=blocked_key,
        source_revision=revision,
        outcome="BLOCKED_CLASSIFICATION",
        result_hash="d" * 64,
        reason="missing policy",
        evidence_refs=[],
    )

    repaired = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=ready_key,
        source_revision=revision,
    )

    assert repaired.should_execute is True
    lifecycle = backend.load("org/repo").readme_poc_lifecycle
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert lifecycle.status == "INTAKE_PREFLIGHTING"
    assert [item.to_status for item in lifecycle.history] == [
        "INTAKE_PREFLIGHTING",
        "INTAKE_READY",
        "INTAKE_PREFLIGHTING",
    ]


def test_successful_historical_retry_repairs_stale_system_failure_status():
    key = _key()
    backend = IntakeBackend(
        ReadmePocLifecycleStateV2(
            status="SYSTEM_FAILURE",
            intake_preflight_history=[
                IntakePreflightBindingV1(
                    dedup_key=key,
                    source_revision="a" * 40,
                    outcome="SYSTEM_FAILURE",
                    result_hash="e" * 64,
                    reason="first attempt failed",
                    observed_by="registry_intake",
                    attempt=1,
                ),
                IntakePreflightBindingV1(
                    dedup_key=key,
                    source_revision="a" * 40,
                    outcome="READY_FULL_PIPELINE",
                    result_hash="f" * 64,
                    reason="retry succeeded",
                    evidence_refs=["intake/preflight-a2.json"],
                    observed_by="registry_intake",
                    attempt=2,
                ),
            ],
        )
    )

    accepted = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    lifecycle = backend.load("org/repo").readme_poc_lifecycle

    assert accepted.should_execute is False
    assert accepted.completed is not None
    assert accepted.completed.attempt == 2
    assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
    assert lifecycle.status == "INTAKE_READY"
    assert lifecycle.history[-1].from_status == "SYSTEM_FAILURE"
    assert lifecycle.history[-1].to_status == "INTAKE_READY"


def test_successful_intake_does_not_rewind_later_review_failure():
    key = _key()
    lifecycle = ReadmePocLifecycleStateV2(
        status="SYSTEM_FAILURE",
        source_revision="a" * 40,
        facts_hash="1" * 64,
        assessment_hash="2" * 64,
        presentation_plan_hash="3" * 64,
        candidate_hash="4" * 64,
        intake_preflight_history=[
            IntakePreflightBindingV1(
                dedup_key=key,
                source_revision="a" * 40,
                outcome="READY_FULL_PIPELINE",
                result_hash="f" * 64,
                reason="intake succeeded",
                observed_by="registry_intake",
            )
        ],
        history=[
            ReadmePocTransitionV2(
                from_status="AGENT_REVIEWING",
                to_status="SYSTEM_FAILURE",
                reason="review provider timed out",
                observed_by="independent_verification",
                source_revision="a" * 40,
            )
        ],
    )
    backend = IntakeBackend(lifecycle)

    accepted = begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    recovered = backend.load("org/repo").readme_poc_lifecycle

    assert accepted.should_execute is False
    assert isinstance(recovered, ReadmePocLifecycleStateV2)
    assert recovered.status == "DETERMINISTIC_VALIDATED"
    assert recovered.history[-1].reason == (
        "recovered checksum-bound safe boundary after non-intake system failure"
    )


def test_already_rewound_review_failure_is_repaired_to_safe_stage():
    key = _key()
    lifecycle = ReadmePocLifecycleStateV2(
        status="INTAKE_READY",
        source_revision="a" * 40,
        facts_hash="1" * 64,
        assessment_hash="2" * 64,
        presentation_plan_hash="3" * 64,
        candidate_hash="4" * 64,
        intake_preflight_history=[
            IntakePreflightBindingV1(
                dedup_key=key,
                source_revision="a" * 40,
                outcome="READY_FULL_PIPELINE",
                result_hash="f" * 64,
                reason="intake succeeded",
                observed_by="registry_intake",
            )
        ],
        history=[
            ReadmePocTransitionV2(
                from_status="AGENT_REVIEWING",
                to_status="SYSTEM_FAILURE",
                reason="review provider timed out",
                observed_by="independent_verification",
                source_revision="a" * 40,
            ),
            ReadmePocTransitionV2(
                from_status="SYSTEM_FAILURE",
                to_status="INTAKE_READY",
                reason="reconciled successful read-only intake retry",
                observed_by="registry_intake",
                source_revision="a" * 40,
            ),
        ],
    )
    backend = IntakeBackend(lifecycle)

    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )
    recovered = backend.load("org/repo").readme_poc_lifecycle

    assert isinstance(recovered, ReadmePocLifecycleStateV2)
    assert recovered.status == "DETERMINISTIC_VALIDATED"
    assert recovered.history[-1].from_status == "INTAKE_READY"
    assert recovered.history[-1].to_status == "DETERMINISTIC_VALIDATED"


def test_non_intake_failure_without_complete_stage_bindings_remains_failed():
    key = _key()
    lifecycle = ReadmePocLifecycleStateV2(
        status="SYSTEM_FAILURE",
        source_revision="a" * 40,
        facts_hash="1" * 64,
        assessment_hash="2" * 64,
        presentation_plan_hash="3" * 64,
        intake_preflight_history=[
            IntakePreflightBindingV1(
                dedup_key=key,
                source_revision="a" * 40,
                outcome="READY_FULL_PIPELINE",
                result_hash="f" * 64,
                reason="intake succeeded",
                observed_by="registry_intake",
            )
        ],
        history=[
            ReadmePocTransitionV2(
                from_status="AGENT_REVIEWING",
                to_status="SYSTEM_FAILURE",
                reason="review failed before candidate binding",
                observed_by="independent_verification",
                source_revision="a" * 40,
            )
        ],
    )
    backend = IntakeBackend(lifecycle)

    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )

    assert backend.load("org/repo").readme_poc_lifecycle.status == "SYSTEM_FAILURE"


def test_unsupported_later_failure_never_rewinds_to_intake():
    key = _key()
    lifecycle = ReadmePocLifecycleStateV2(
        status="SYSTEM_FAILURE",
        source_revision="a" * 40,
        facts_hash="1" * 64,
        assessment_hash="2" * 64,
        presentation_plan_hash="3" * 64,
        candidate_hash="4" * 64,
        intake_preflight_history=[
            IntakePreflightBindingV1(
                dedup_key=key,
                source_revision="a" * 40,
                outcome="READY_FULL_PIPELINE",
                result_hash="f" * 64,
                reason="intake succeeded",
                observed_by="registry_intake",
            )
        ],
        history=[
            ReadmePocTransitionV2(
                from_status="AGENT_APPROVED",
                to_status="SYSTEM_FAILURE",
                reason="downstream proof failed",
                observed_by="supervisor",
                source_revision="a" * 40,
            )
        ],
    )
    backend = IntakeBackend(lifecycle)

    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )

    assert backend.load("org/repo").readme_poc_lifecycle.status == "SYSTEM_FAILURE"


def test_non_intake_recovery_requires_matching_source_revision():
    key = _key()
    lifecycle = ReadmePocLifecycleStateV2(
        status="SYSTEM_FAILURE",
        source_revision="b" * 40,
        facts_hash="1" * 64,
        assessment_hash="2" * 64,
        presentation_plan_hash="3" * 64,
        candidate_hash="4" * 64,
        intake_preflight_history=[
            IntakePreflightBindingV1(
                dedup_key=key,
                source_revision="a" * 40,
                outcome="READY_FULL_PIPELINE",
                result_hash="f" * 64,
                reason="old intake succeeded",
                observed_by="registry_intake",
            )
        ],
        history=[
            ReadmePocTransitionV2(
                from_status="AGENT_REVIEWING",
                to_status="SYSTEM_FAILURE",
                reason="review failed on another revision",
                observed_by="independent_verification",
                source_revision="b" * 40,
            )
        ],
    )
    backend = IntakeBackend(lifecycle)

    begin_readonly_intake_preflight(
        backend,
        "org/repo",
        dedup_key=key,
        source_revision="a" * 40,
    )

    recovered = backend.load("org/repo").readme_poc_lifecycle
    assert recovered.status == "SYSTEM_FAILURE"
    assert recovered.source_revision == "b" * 40


@pytest.mark.parametrize(
    ("requested_revision", "source_revision_resolved"),
    [("b" * 40, True), ("a" * 40, False)],
)
def test_completed_intake_reuse_requires_matching_identity(
    requested_revision, source_revision_resolved
):
    key = _key()
    lifecycle = ReadmePocLifecycleStateV2(
        status="SYSTEM_FAILURE",
        source_revision="a" * 40,
        intake_preflight_history=[
            IntakePreflightBindingV1(
                dedup_key=key,
                source_revision="a" * 40,
                source_revision_resolved=True,
                outcome="READY_FULL_PIPELINE",
                result_hash="f" * 64,
                reason="intake succeeded",
                observed_by="registry_intake",
            )
        ],
        history=[
            ReadmePocTransitionV2(
                from_status="INTAKE_PREFLIGHTING",
                to_status="SYSTEM_FAILURE",
                reason="intake failed after an older success",
                observed_by="registry_intake",
                source_revision="a" * 40,
            )
        ],
    )
    backend = IntakeBackend(lifecycle)

    with pytest.raises(StateBackendError, match="completed intake identity is inconsistent"):
        begin_readonly_intake_preflight(
            backend,
            "org/repo",
            dedup_key=key,
            source_revision=requested_revision,
            source_revision_resolved=source_revision_resolved,
        )

    assert backend.load("org/repo").readme_poc_lifecycle.status == "SYSTEM_FAILURE"
