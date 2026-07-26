"""Supervisor-owned product-truth preparation, persistence, and narrow blocking."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from readme_agent import paths
from readme_agent.capabilities.dispatcher import DispatchResult
from readme_agent.facts.schema_v2 import (
    README_DRAFTABLE_PRODUCT_FIELDS,
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.readme_poc_lifecycle import (
    record_repository_profile,
    record_repository_snapshot,
    transition_readme_poc_status,
)
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor import product_truth

ORG_REPO = "acme/widget"
REVISION = "a" * 40


class _Backend:
    def __init__(self):
        self.states: dict[str, RunStateV2] = {}

    def load(self, org_repo):
        return self.states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        next_version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": next_version}
        )
        return SaveResult("saved", next_version)

    def acquire_lock(self, org_repo):
        return Lock(org_repo, "test", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock):
        return None

    def lock_still_held(self, lock):
        return True

    def acquire_run_lock(self, org_repo):
        return self.acquire_lock(org_repo)

    def release_run_lock(self, lock):
        return None

    def load_model_route_status(self, job):
        return None

    def save_model_route_status(self, status):
        return None


def _snapshot(tmp_path: Path) -> RepositorySnapshotV1:
    (tmp_path / "README.md").write_text("# Widget\n", encoding="utf-8")
    return RepositorySnapshotV1(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        snapshot_root=str(tmp_path.resolve()),
        readme_path="README.md",
        readme_sha256="b" * 64,
        inventory_sha256="c" * 64,
        captured_at="2026-07-25T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="c" * 64,
        ),
    )


def _facts(*, draftable_missing: bool = False, conflict_field: str | None = None):
    source = FactSourceV2(
        source_type="mechanical_repository",
        location=f"repository://{ORG_REPO}",
        source_revision=REVISION,
    )
    records = []
    for field in REQUIRED_PRODUCT_FIELDS:
        missing = draftable_missing and field in README_DRAFTABLE_PRODUCT_FIELDS
        records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field, "fixture"),
                field=field,
                value=None if missing else {"field": field},
                source=source,
                verification_state=(
                    "conflicting"
                    if field == conflict_field
                    else ("missing" if missing else "verified")
                ),
                authoritative_owner="repository-owner",
                confidence=0.0 if missing else 1.0,
                conflicts=[],
                affected_surfaces=["readme"],
            )
        )
    return ProductFactsV2(
        org_repo=ORG_REPO,
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def _ready_backend(snapshot: RepositorySnapshotV1) -> _Backend:
    backend = _Backend()
    record_repository_snapshot(
        backend,
        ORG_REPO,
        source_revision=REVISION,
        evidence_refs=["snapshot"],
    )
    record_repository_profile(
        backend,
        ORG_REPO,
        source_revision=REVISION,
        evidence_refs=["profile"],
    )
    return backend


@pytest.mark.parametrize(
    "ecosystem",
    ["java", "net", "python", "typescript", "cpp", "go", "rust"],
)
def test_supported_ecosystem_draft_becomes_the_persisted_run_graph(
    tmp_path, monkeypatch, ecosystem
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    drafted = _facts()
    observed = {}
    dispatch_calls = []

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem=ecosystem),
    )

    def dispatch(tool_call, permissions, **kwargs):
        dispatch_calls.append(tool_call)
        observed.update(kwargs["extra_kwargs"])
        return DispatchResult(
            outcome="executed",
            result={
                "product_facts_v2": drafted.model_dump(mode="json"),
                "proposed_product_truth": {"audience": ["Widget users"]},
                "findings": [],
            },
        )

    monkeypatch.setattr(product_truth, "dispatch_tool_call", dispatch)

    result = product_truth.prepare_local_product_truth(
        ORG_REPO,
        snapshot,
        backend,
        client=object(),
    )

    assert result.lifecycle_status == "FACTS_READY"
    assert result.facts == drafted
    assert observed["repository_snapshot"] is snapshot
    assert observed["base_facts"] == base
    assert backend.load(ORG_REPO).readme_poc_lifecycle.facts_hash == drafted.canonical_hash()
    assert (Path(result.bundle_dir) / "facts" / "product-facts.json").is_file()
    assert (Path(result.bundle_dir) / "facts" / "proposed-product-truth.json").is_file()

    cached = product_truth.prepare_local_product_truth(
        ORG_REPO,
        snapshot,
        backend,
        client=object(),
    )
    assert cached.resolution_source == "durable_revision_cache"
    assert len(dispatch_calls) == 1


def test_same_revision_reuses_durable_fact_graph_without_collection_or_llm(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    drafted = _facts()
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )
    monkeypatch.setattr(
        product_truth,
        "dispatch_tool_call",
        lambda *args, **kwargs: DispatchResult(
            outcome="executed",
            result={
                "product_facts_v2": drafted.model_dump(mode="json"),
                "proposed_product_truth": {"audience": ["Widget users"]},
                "findings": [],
            },
        ),
    )
    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("durable fact cache must avoid recollection"),
    )
    monkeypatch.setattr(
        product_truth,
        "dispatch_tool_call",
        lambda *args, **kwargs: pytest.fail("durable fact cache must avoid another LLM call"),
    )

    second = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert second.facts == first.facts
    assert second.resolution_source == "durable_revision_cache"
    assert second.proposed_product_truth == first.proposed_product_truth
    assert len(backend.load(ORG_REPO).readme_poc_lifecycle.history) == 4


def test_same_inputs_reuse_a_narrowly_blocked_draft_without_repeating_the_llm(
    tmp_path, monkeypatch
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    calls = []
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="rust"),
    )

    def dispatch(*args, **kwargs):
        calls.append(kwargs)
        return DispatchResult(
            outcome="executed",
            result={
                "product_facts_v2": base.model_dump(mode="json"),
                "proposed_product_truth": {"audience": ["Widget users"]},
                "findings": [{"field": "example.minimal", "status": "BLOCKED"}],
            },
        )

    monkeypatch.setattr(product_truth, "dispatch_tool_call", dispatch)

    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    second = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert first.lifecycle_status == "BLOCKED_MISSING_EVIDENCE"
    assert second.resolution_source == "durable_revision_cache"
    assert len(calls) == 1


def test_later_lifecycle_stage_reuses_the_same_durable_fact_graph(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    facts = _facts()
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: {"product_facts_v2": facts},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )

    product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    transition_readme_poc_status(
        backend,
        ORG_REPO,
        "README_ASSESSED",
        observed_by="test",
        reason="prove facts remain reusable after downstream progress",
    )
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("downstream progress must not recollect product facts"),
    )

    cached = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert cached.resolution_source == "durable_revision_cache"
    assert cached.lifecycle_status == "README_ASSESSED"
    assert cached.facts == facts


def test_missing_durable_fact_evidence_fails_closed(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    facts = _facts()
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: {"product_facts_v2": facts},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )

    prepared = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    (Path(prepared.bundle_dir) / "facts" / "product-facts.json").unlink()

    with pytest.raises(RuntimeError, match="evidence is missing"):
        product_truth.load_prepared_product_truth(ORG_REPO, backend, REVISION)


def test_changed_fact_input_contract_invalidates_only_the_cached_agent_draft(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    drafted = _facts()
    prompt_hash = {"value": "1" * 64}
    verification_hash = {"value": "a" * 64}
    calls = []

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )
    monkeypatch.setattr(
        product_truth.prompt_registry,
        "prompt_hash",
        lambda prompt_id: prompt_hash["value"],
    )
    monkeypatch.setattr(
        product_truth,
        "local_verification_contract_hash",
        lambda: verification_hash["value"],
    )

    def dispatch(*args, **kwargs):
        calls.append(kwargs)
        return DispatchResult(
            outcome="executed",
            result={
                "product_facts_v2": drafted.model_dump(mode="json"),
                "proposed_product_truth": {"audience": ["Widget users"]},
                "findings": [],
            },
        )

    monkeypatch.setattr(product_truth, "dispatch_tool_call", dispatch)

    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    cached = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    verification_hash["value"] = "b" * 64
    verifier_refreshed = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    prompt_hash["value"] = "2" * 64
    prompt_refreshed = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert first.resolution_source == "agent_draft"
    assert cached.resolution_source == "durable_revision_cache"
    assert verifier_refreshed.resolution_source == "agent_draft"
    assert prompt_refreshed.resolution_source == "agent_draft"
    assert len(calls) == 3
    assert backend.load(ORG_REPO).readme_poc_lifecycle.prompt_hash == "2" * 64
