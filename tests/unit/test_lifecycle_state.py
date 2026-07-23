"""Restartable trigger lifecycle, migration, recovery, and health tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.health import build_health_report
from readme_agent.state.lifecycle import (
    LifecycleRecorder,
    accept_trigger,
    transition_trigger,
)
from readme_agent.state.lifecycle_schema import TriggerEnvelopeV2
from readme_agent.state.migrations import ensure_run_state_v2, load_run_state_json
from readme_agent.state.recovery import recovery_sweep
from readme_agent.state.schema import RunStateV1, RunStateV2, TriggerRecordV1


class LifecycleBackend:
    def __init__(self):
        self.states: dict[str, RunStateV2] = {}
        self.locked: set[str] = set()

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        new_version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": new_version}
        )
        return SaveResult("saved", new_version)

    def acquire_lock(self, org_repo: str) -> Lock | None:
        if org_repo in self.locked:
            return None
        self.locked.add(org_repo)
        return Lock(org_repo, "test", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        self.locked.discard(lock.org_repo)

    def lock_still_held(self, lock: Lock) -> bool:
        return lock.org_repo in self.locked

    def acquire_run_lock(self, org_repo: str) -> Lock | None:
        return self.acquire_lock(f"run:{org_repo}")

    def release_run_lock(self, lock: Lock) -> None:
        self.release_lock(lock)

    def load_model_route_status(self, job: str):
        return None

    def save_model_route_status(self, status) -> None:
        return None


def envelope(*, key: str = "delivery:1") -> TriggerEnvelopeV2:
    return TriggerEnvelopeV2(
        provider_event_id="provider-1",
        event_type="repository_dispatch",
        repository_scope="org/repo",
        delivery_id="delivery-1",
        dedup_key=key,
        occurred_at="2026-07-23T00:00:00+00:00",
    )


class TestLifecycleSchemasAndMigration:
    def test_schedule_requires_a_window(self):
        with pytest.raises(ValidationError):
            TriggerEnvelopeV2(
                provider_event_id="event",
                event_type="schedule",
                repository_scope="org/repo",
                dedup_key="schedule:missing",
            )

    def test_v1_trigger_migrates_to_v2_lifecycle_and_checkpoint(self):
        legacy = RunStateV1(
            org_repo="org/repo",
            state_version=7,
            trigger_records={
                "manual:req-1": TriggerRecordV1(
                    org_repo="org/repo",
                    manual_request_id="req-1",
                    accepted_at="2026-07-23T00:00:00+00:00",
                )
            },
        )
        migrated = load_run_state_json(legacy.model_dump_json())
        assert migrated.schema_version == 2
        lifecycle = migrated.trigger_lifecycles["manual:req-1"]
        assert lifecycle.status == "accepted"
        assert lifecycle.last_checkpoint_id in migrated.checkpoints
        assert migrated.checkpoints[lifecycle.last_checkpoint_id].stage == "trigger_accepted"

    def test_unknown_newer_version_fails_closed(self):
        with pytest.raises(StateBackendError, match="unsupported durable-state schema version"):
            load_run_state_json(json.dumps({"schema_version": 99, "org_repo": "org/repo"}))

    def test_v2_round_trip_is_explicitly_versioned(self):
        state = RunStateV2(org_repo="org/repo")
        restored = load_run_state_json(state.model_dump_json())
        assert restored == state


class TestLifecycleTransitions:
    def test_full_lifecycle_is_terminal_and_checkpointed(self):
        backend = LifecycleBackend()
        accepted = accept_trigger(backend, envelope())
        assert accepted.should_execute is True
        recorder = LifecycleRecorder(backend, envelope(), "run-1")
        recorder.checkpoint("trigger_accepted", inputs={"source": "test"})
        recorder.start()
        recorder.checkpoint("snapshot_captured", outputs={"revision": "abc"})
        recorder.finish("completed")

        state = backend.load("org/repo")
        lifecycle = state.trigger_lifecycles["delivery:1"]
        assert lifecycle.status == "completed"
        assert [item.stage for item in recorder.checkpoints()] == [
            "trigger_accepted",
            "run_started",
            "snapshot_captured",
            "final_acceptance",
        ]

    def test_completed_duplicate_is_suppressed(self):
        backend = LifecycleBackend()
        accept_trigger(backend, envelope())
        transition_trigger(backend, "org/repo", "delivery:1", "processing")
        transition_trigger(backend, "org/repo", "delivery:1", "completed")
        duplicate = accept_trigger(backend, envelope())
        assert duplicate.should_execute is False
        assert duplicate.lifecycle.status == "deduplicated"

    def test_unfinished_duplicate_resumes_the_same_logical_execution(self):
        backend = LifecycleBackend()
        accept_trigger(backend, envelope())
        resumed = accept_trigger(backend, envelope())
        assert resumed.should_execute is True
        assert resumed.resumed is True
        assert len(backend.load("org/repo").trigger_lifecycles) == 1

    def test_invalid_terminal_transition_fails_closed(self):
        backend = LifecycleBackend()
        accept_trigger(backend, envelope())
        transition_trigger(backend, "org/repo", "delivery:1", "blocked")
        with pytest.raises(StateBackendError, match="invalid trigger transition"):
            transition_trigger(backend, "org/repo", "delivery:1", "processing")

    def test_replayed_checkpoint_is_idempotent_despite_fresh_timestamps(self):
        backend = LifecycleBackend()
        trigger = envelope()
        accept_trigger(backend, trigger)
        recorder = LifecycleRecorder(backend, trigger, "run-1")

        first = recorder.checkpoint(
            "profile_completed",
            action="profile_repository",
            inputs={"revision": "abc"},
            outputs={"ecosystem": "java"},
        )
        replayed = recorder.checkpoint(
            "profile_completed",
            action="profile_repository",
            inputs={"revision": "abc"},
            outputs={"ecosystem": "java"},
        )

        assert replayed == first
        assert len(backend.load("org/repo").checkpoints) == 1

    def test_replayed_checkpoint_rejects_changed_output(self):
        backend = LifecycleBackend()
        trigger = envelope()
        accept_trigger(backend, trigger)
        recorder = LifecycleRecorder(backend, trigger, "run-1")
        recorder.checkpoint(
            "profile_completed",
            action="profile_repository",
            inputs={"revision": "abc"},
            outputs={"ecosystem": "java"},
        )

        with pytest.raises(StateBackendError, match="checkpoint identity collision"):
            recorder.checkpoint(
                "profile_completed",
                action="profile_repository",
                inputs={"revision": "abc"},
                outputs={"ecosystem": "python"},
            )

    def test_recovery_sweep_marks_expired_processing_retryable(self):
        backend = LifecycleBackend()
        accept_trigger(backend, envelope())
        transition_trigger(
            backend,
            "org/repo",
            "delivery:1",
            "processing",
            lease_seconds=1,
        )
        observed = datetime.now(UTC) + timedelta(seconds=2)
        candidates = recovery_sweep(backend, ["org/repo"], now=observed)
        assert len(candidates) == 1
        assert candidates[0].prior_status == "processing"
        lifecycle = backend.load("org/repo").trigger_lifecycles["delivery:1"]
        assert lifecycle.status == "retryable"
        assert lifecycle.recovery_count == 1

    @pytest.mark.parametrize(
        "stage",
        [
            "trigger_accepted",
            "run_started",
            "snapshot_captured",
            "profile_completed",
            "task_started",
            "task_completed",
            "verifier_result",
            "repair_plan",
            "effect_pending",
            "effect_applied",
            "final_acceptance",
        ],
    )
    def test_crash_after_every_checkpoint_resumes_on_the_same_logical_trigger(self, stage):
        backend = LifecycleBackend()
        trigger = envelope()
        accept_trigger(backend, trigger)
        transition_trigger(backend, "org/repo", trigger.dedup_key, "processing")
        recorder = LifecycleRecorder(backend, trigger, "run-before-crash")

        recorder.checkpoint(stage, action="fault-injection")
        # The process is now considered killed: no later transition or
        # checkpoint occurs. Age the durable record so the next scheduled
        # recovery sweep must pick it up.
        state = backend.load("org/repo")
        lifecycle = state.trigger_lifecycles[trigger.dedup_key].model_copy(
            update={
                "updated_at": "2000-01-01T00:00:00+00:00",
                "lease_expires_at": "2000-01-01T00:01:00+00:00",
            }
        )
        backend.states["org/repo"] = state.model_copy(
            update={"trigger_lifecycles": {trigger.dedup_key: lifecycle}}
        )

        recovered = recovery_sweep(backend, ["org/repo"])
        resumed = accept_trigger(backend, trigger)
        after_restart = LifecycleRecorder(backend, trigger, "run-after-crash", attempt=2)
        after_restart.start()
        after_restart.finish("completed")

        assert recovered[0].last_checkpoint_id is not None
        assert resumed.should_execute is True
        assert resumed.resumed is True
        final = backend.load("org/repo")
        assert len(final.trigger_lifecycles) == 1
        assert final.trigger_lifecycles[trigger.dedup_key].status == "completed"


class TestLifecycleHealth:
    def test_report_exposes_backlog_stale_lease_and_open_state(self):
        backend = LifecycleBackend()
        accept_trigger(backend, envelope())
        transition_trigger(
            backend,
            "org/repo",
            "delivery:1",
            "processing",
            lease_seconds=1,
        )
        report = build_health_report(
            backend,
            ["org/repo"],
            now=datetime.now(UTC) + timedelta(seconds=2),
        )
        assert report.healthy is False
        assert report.backlog[0]["status"] == "processing"
        assert report.stale_leases[0]["dedup_key"] == "delivery:1"
        assert report.missed_schedule_windows

    def test_state_failure_is_visible_not_false_green(self):
        class BrokenBackend(LifecycleBackend):
            def load(self, org_repo: str):
                raise StateBackendError("state unavailable")

        report = build_health_report(BrokenBackend(), ["org/repo"])
        assert report.healthy is False
        assert report.state_failures == [{"repository": "org/repo", "error": "state unavailable"}]
