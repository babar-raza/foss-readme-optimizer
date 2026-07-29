"""Durable read-only intake reservation, resume, and deduplication."""

from __future__ import annotations

from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
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
