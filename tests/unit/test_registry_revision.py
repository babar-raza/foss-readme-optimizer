"""Registry revisions bind source discovery, intake, and campaign admission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from readme_agent.registry.discovery_models import (
    DiscoveryInventoryV1,
    DiscoveryObservationV1,
    DiscoverySourceResultV1,
    DiscoverySourceV1,
)
from readme_agent.registry.models import ProductEntry
from readme_agent.registry.reconciliation import reconcile_registry
from readme_agent.registry.revision import (
    build_registry_revision,
    with_pending_intake,
)
from readme_agent.registry.revision_gate import evaluate_registry_revision
from readme_agent.registry.revision_store import (
    load_current_registry_revision,
    write_registry_revision,
)
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.registry_intake_queue import settle_registry_intake_queue


def _entry(repository_id: int = 10) -> dict:
    return {
        "registry_schema_version": 2,
        "provider_identity": {
            "schema_version": 1,
            "provider": "github",
            "repository_id": repository_id,
            "node_id": f"R_{repository_id}",
        },
        "family": "cells",
        "platform": "python",
        "repo_name": "Aspose.Cells-FOSS-for-Python",
        "repo_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
        "clone_url": "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python.git",
        "active": True,
        "discovered_via": "github",
        "mode": "disabled",
        "ecosystem": "python",
        "policy_profile": "aspose-cells-foss",
    }


def _observation(repository_id: int = 10, *, pushed_at: str = "2026-08-01T00:00:00Z"):
    entry = _entry(repository_id)
    return DiscoveryObservationV1(
        source_id="github-org:aspose-cells-foss",
        provider_repository_id=repository_id,
        provider_node_id=f"R_{repository_id}",
        full_name="aspose-cells-foss/Aspose.Cells-FOSS-for-Python",
        name=entry["repo_name"],
        html_url=entry["repo_url"],
        clone_url=entry["clone_url"],
        visibility="public",
        default_branch="main",
        pushed_at=pushed_at,
        observed_at="2026-08-01T00:00:00+00:00",
        classification="matched",
        classification_reason="fixture",
        disposition="admit_candidate",
        family="cells",
        platform="python",
    )


def _inventory(*observations, failed: bool = False) -> DiscoveryInventoryV1:
    source = DiscoverySourceV1(
        source_id="github-org:aspose-cells-foss",
        organization="aspose-cells-foss",
        family_hint="cells",
    )
    return DiscoveryInventoryV1(
        captured_at="2026-08-01T00:00:00+00:00",
        sources=[
            DiscoverySourceResultV1(
                source=source,
                status="failed" if failed else "complete",
                observed_at="2026-08-01T00:00:00+00:00",
                observation_count=len(observations),
                error="source unavailable" if failed else None,
            )
        ],
        observations=list(observations),
        complete=not failed,
    )


def _revision(*, prior=None, observation=None):
    existing = [_entry()]
    inventory = _inventory(observation or _observation())
    reconciliation = reconcile_registry(existing, inventory)
    return build_registry_revision(
        inventory,
        reconciliation,
        previous_entries=existing,
        prior_revision=prior,
    )


def test_complete_revision_is_current_campaign_eligible():
    revision = _revision()

    gate = evaluate_registry_revision(
        revision,
        [_entry()],
        now=datetime(2026, 8, 1, 1, tzinfo=UTC),
    )

    assert revision.complete is True
    assert revision.pending_intake == []
    assert gate.eligible is True
    assert gate.reasons == []


def test_disabled_source_is_revision_bound_without_blocking_completeness():
    existing = [_entry()]
    excluded_source = DiscoverySourceV1(
        source_id="github-org:aspose-imaging-foss",
        organization="aspose-imaging-foss",
        family_hint="imaging",
        enabled=False,
        exclusion_reason="organization does not exist",
    )
    inventory = DiscoveryInventoryV1(
        captured_at="2026-08-01T00:00:00+00:00",
        sources=[
            DiscoverySourceResultV1(
                source=excluded_source,
                status="excluded",
                observed_at="2026-08-01T00:00:00+00:00",
                observation_count=0,
            )
        ],
        observations=[],
        complete=True,
    )
    revision = build_registry_revision(
        inventory,
        reconcile_registry(existing, inventory),
        previous_entries=existing,
    )

    assert revision.complete is True
    assert revision.source_failures == []
    assert revision.exclusions == [
        {
            "org_repo": "aspose-imaging-foss/*",
            "classification": "source_excluded",
            "reason": "organization does not exist",
        }
    ]
    assert evaluate_registry_revision(revision, existing).eligible is True


def test_changed_observation_creates_one_pending_intake_and_deduplicates_next_scan():
    first = _revision()
    changed = _revision(
        prior=first,
        observation=_observation(pushed_at="2026-08-01T02:00:00Z"),
    )

    assert [(item.org_repo, item.change_kind) for item in changed.observation_changes] == [
        ("aspose-cells-foss/Aspose.Cells-FOSS-for-Python", "refreshed")
    ]
    assert changed.pending_intake == ["aspose-cells-foss/Aspose.Cells-FOSS-for-Python"]

    settled = with_pending_intake(changed, [])
    identical = _revision(
        prior=settled,
        observation=_observation(pushed_at="2026-08-01T02:00:00Z"),
    )
    assert identical.observation_changes == []
    assert identical.pending_intake == []


def test_gate_rejects_stale_incomplete_pending_and_products_drift():
    existing = [_entry()]
    inventory = _inventory(failed=True)
    revision = build_registry_revision(
        inventory,
        reconcile_registry(existing, inventory),
        previous_entries=existing,
        pending_intake=["aspose-cells-foss/Aspose.Cells-FOSS-for-Python"],
        freshness_ttl=timedelta(hours=1),
    )
    drifted = [dict(_entry(), active=False)]

    gate = evaluate_registry_revision(
        revision,
        drifted,
        now=datetime(2026, 8, 2, tzinfo=UTC),
    )

    assert gate.eligible is False
    assert set(gate.reasons) == {
        "source_scan_incomplete",
        "source_failures_present",
        "source_scan_stale",
        "pending_intake_present",
        "products_registry_hash_drift",
    }


def test_gate_rejects_act_fixture_revision_outside_act(monkeypatch):
    existing = [_entry()]
    inventory = _inventory(_observation())
    revision = build_registry_revision(
        inventory,
        reconcile_registry(existing, inventory),
        previous_entries=existing,
        proof_scope="act_fixture",
    )
    monkeypatch.delenv("ACT", raising=False)

    assert evaluate_registry_revision(revision, existing).reasons == ["act_fixture_not_admissible"]

    monkeypatch.setenv("ACT", "true")
    assert evaluate_registry_revision(revision, existing).eligible is True


def test_revision_persistence_is_idempotent_and_checksum_addressed(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    revision = _revision()

    first = write_registry_revision(revision)
    second = write_registry_revision(revision)

    assert first == second
    assert first.name == f"{revision.revision_id}.json"
    assert load_current_registry_revision() == revision


class _Backend:
    def __init__(self):
        self.states: dict[str, RunStateV2] = {}
        self.locked: set[str] = set()

    def load(self, org_repo: str):
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None):
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": version}
        )
        return SaveResult("saved", version)

    def acquire_lock(self, org_repo: str):
        if org_repo in self.locked:
            return None
        self.locked.add(org_repo)
        return Lock(org_repo, "test", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock):
        self.locked.discard(lock.org_repo)

    def lock_still_held(self, lock):
        return lock.org_repo in self.locked


def test_discovery_queue_delivers_one_trigger_and_reuses_duplicate(monkeypatch):
    baseline = _revision()
    revision = _revision(
        prior=baseline,
        observation=_observation(pushed_at="2026-08-01T02:00:00Z"),
    )
    backend = _Backend()
    calls = 0

    def _intake(entry, state_backend):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            executed=calls == 1,
            binding=SimpleNamespace(outcome="READY_FULL_PIPELINE"),
        )

    monkeypatch.setattr(
        "readme_agent.supervisor.registry_intake_queue.run_readonly_intake_preflight",
        _intake,
    )
    entries = [ProductEntry.model_validate(_entry())]

    first = settle_registry_intake_queue(revision, entries, backend)
    second = settle_registry_intake_queue(revision, entries, backend)

    assert first.pending_intake == []
    assert first.items[0].trigger_executed is True
    assert second.items[0].trigger_executed is False
    assert len(backend.states[entries[0].org_repo].trigger_lifecycles) == 1
    assert calls == 2
