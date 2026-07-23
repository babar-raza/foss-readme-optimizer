"""Production lifecycle CLI commands expose one matrix, recovery sweep, and health report."""

from __future__ import annotations

import json

from readme_agent.cli import main
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.schema import RunStateV2


class _MemoryBackend:
    def __init__(self) -> None:
        self.states: dict[str, RunStateV2] = {}

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(
        self,
        org_repo: str,
        state: RunStateV2,
        expected_version: int | None,
    ) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult("stale", current_version)
        version = (current_version or 0) + 1
        self.states[org_repo] = state.model_copy(update={"state_version": version})
        return SaveResult("saved", version)

    def acquire_lock(self, org_repo: str) -> Lock:
        return Lock(org_repo, "test", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        pass


def test_runtime_matrix_covers_every_active_registry_entry(capsys):
    from readme_agent.registry.loader import load_products

    assert main(["runtime-matrix"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert {item["repo"] for item in payload["include"]} == {
        entry.org_repo for entry in load_products() if entry.active
    }
    assert any(item["mode"] == "disabled" for item in payload["include"])


def test_recovery_sweep_marks_expired_trigger_retryable(monkeypatch, capsys):
    from readme_agent.state import git_backend
    from readme_agent.state.lifecycle import accept_trigger, transition_trigger
    from readme_agent.state.trigger_v2 import normalize_trigger_envelope

    backend = _MemoryBackend()
    envelope = normalize_trigger_envelope(
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
        event_type="workflow_dispatch",
        workflow_run_id="run-1",
    )
    accept_trigger(backend, envelope)
    transition_trigger(backend, envelope.repository_scope, envelope.dedup_key, "processing")
    state = backend.states[envelope.repository_scope]
    lifecycle = state.trigger_lifecycles[envelope.dedup_key].model_copy(
        update={
            "updated_at": "2000-01-01T00:00:00+00:00",
            "lease_expires_at": "2000-01-01T00:01:00+00:00",
        }
    )
    backend.states[envelope.repository_scope] = state.model_copy(
        update={"trigger_lifecycles": {envelope.dedup_key: lifecycle}}
    )
    monkeypatch.setattr(git_backend, "default_state_backend", lambda: backend)

    assert main(["recovery-sweep", "--only", envelope.repository_scope]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["recovery_candidates"][0]["trigger_dedup_key"] == envelope.dedup_key
    assert (
        backend.states[envelope.repository_scope].trigger_lifecycles[envelope.dedup_key].status
        == "retryable"
    )


def test_health_report_exposes_missing_state_and_optional_failure(monkeypatch, capsys):
    from readme_agent.state import git_backend

    monkeypatch.setattr(git_backend, "default_state_backend", _MemoryBackend)
    repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"

    assert main(["health-report", "--only", repo]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["healthy"] is False
    assert report["missed_schedule_windows"][0]["repository"] == repo

    assert main(["health-report", "--only", repo, "--fail-unhealthy"]) == 1
