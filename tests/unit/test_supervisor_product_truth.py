"""Supervisor-owned product-truth preparation, persistence, and narrow blocking."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from readme_agent import paths
from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.facts.schema_v2 import (
    README_DRAFTABLE_PRODUCT_FIELDS,
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.llm import prompt_registry
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.lifecycle_schema import FactAcceptanceBindingV1, ReadmePocTransitionV2
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.readme_poc_lifecycle import (
    record_repository_profile,
    record_repository_snapshot,
    switch_content_assurance,
    transition_readme_poc_status,
)
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor import product_truth

ORG_REPO = "acme/widget"
REVISION = "a" * 40


@pytest.fixture(autouse=True)
def _allow_fixture_repository(monkeypatch):
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )


def test_product_truth_block_category_is_external_only_when_every_finding_is_external():
    external = {"blocked_category": "infra_external"}
    agent = {"blocked_category": "agent_fixable"}

    assert product_truth.product_truth_blocked_category([external]) == "infra_external"
    assert product_truth.product_truth_blocked_category([external, agent]) == "agent_fixable"
    assert product_truth.product_truth_blocked_category([]) == "agent_fixable"


class _Backend:
    def __init__(self):
        self.states: dict[str, RunStateV2] = {}
        self.save_calls = 0

    def load(self, org_repo):
        return self.states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        self.save_calls += 1
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


class _RacingBackend(_Backend):
    """Replace state on a selected load to reproduce a stale-read/CAS overlap."""

    def __init__(self):
        super().__init__()
        self.load_count = 0
        self.race_on_load: int | None = None
        self.race_state: RunStateV2 | None = None

    def load(self, org_repo):
        self.load_count += 1
        if self.load_count == self.race_on_load:
            assert self.race_state is not None
            self.states[org_repo] = self.race_state
        return super().load(org_repo)


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
    renderable_values = {
        "product.audience": ["Developers using Java"],
        "product.problems_solved": ["Process widget files"],
        "product.capabilities": ["Create and inspect widgets"],
        "product.formats": ["WGT"],
    }
    records = []
    for field in REQUIRED_PRODUCT_FIELDS:
        missing = draftable_missing and field in README_DRAFTABLE_PRODUCT_FIELDS
        records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field, "fixture"),
                field=field,
                value=None if missing else renderable_values.get(field, {"field": field}),
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


def _facts_with_missing(field_name: str) -> ProductFactsV2:
    facts = _facts()
    records = [
        (
            fact.model_copy(
                update={
                    "value": None,
                    "verification_state": "missing",
                    "confidence": 0.0,
                }
            )
            if fact.field == field_name
            else fact
        )
        for fact in facts.facts
    ]
    return facts.model_copy(update={"facts": records})


def _advance_to_no_op(backend: _Backend) -> None:
    for status in (
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
    ):
        transition_readme_poc_status(
            backend,
            ORG_REPO,
            status,
            observed_by="legacy-fixture",
            reason="simulate a terminal bundle written before contract binding",
            source_revision=REVISION,
        )


def _remove_fact_acceptance_binding(backend: _Backend, bundle_dir: Path) -> None:
    state = backend.load(ORG_REPO)
    assert state is not None
    lifecycle = state.readme_poc_lifecycle
    assert lifecycle is not None
    backend.states[ORG_REPO] = state.model_copy(
        update={
            "readme_poc_lifecycle": lifecycle.model_copy(
                update={
                    "fact_acceptance_contract_hash": None,
                    "fact_acceptance_component_hashes": {},
                    "fact_acceptance_history": [],
                }
            )
        }
    )
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("fact_acceptance_contract_hash", None)
    manifest.pop("fact_acceptance_component_hashes", None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_interrupted_fact_commit(
    tmp_path: Path,
    monkeypatch,
) -> tuple[RepositorySnapshotV1, _Backend, ProductFactsV2, Path]:
    """Seal a newer fact bundle while leaving durable state on the prior graph."""

    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    contract = product_truth.current_fact_acceptance_contract("java")
    old_facts = _facts_with_missing("installation.verified_acquisition")
    bundle_dir = product_truth.write_local_poc_product_facts(
        snapshot,
        old_facts,
        findings=[],
        resolution_source="repository_and_policy",
        lifecycle_status="BLOCKED_MISSING_EVIDENCE",
        local_verification_contract_hash=product_truth.local_verification_contract_hash("java"),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    product_truth.record_product_facts_outcome(
        backend,
        ORG_REPO,
        source_revision=REVISION,
        facts_hash=old_facts.canonical_hash(),
        outcome="BLOCKED_MISSING_EVIDENCE",
        evidence_refs=[str(bundle_dir / "facts" / "product-facts.json")],
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    records = [
        (
            fact.model_copy(update={"value": ["Create, inspect, and convert widgets"]})
            if fact.field == "product.capabilities"
            else fact
        )
        for fact in old_facts.facts
    ]
    new_facts = old_facts.model_copy(update={"facts": records})
    product_truth.write_local_poc_product_facts(
        snapshot,
        new_facts,
        findings=[],
        resolution_source="repository_and_policy",
        lifecycle_status="BLOCKED_MISSING_EVIDENCE",
        local_verification_contract_hash=product_truth.local_verification_contract_hash("java"),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    return snapshot, backend, new_facts, bundle_dir


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
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(
            ecosystem=ecosystem,
            family={"net": "3d", "python": "pdf"}.get(ecosystem),
        ),
    )

    monkeypatch.setattr(product_truth, "load_salvage_candidate", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        product_truth,
        "salvage_product_truth_candidate",
        lambda *args, **kwargs: pytest.fail("salvage cannot run without a candidate"),
    )

    result = product_truth.prepare_local_product_truth(
        ORG_REPO,
        snapshot,
        backend,
        client=object(),
    )

    assert result.lifecycle_status == "BLOCKED_MISSING_EVIDENCE"
    assert result.facts == base
    assert result.resolution_source == "repository_and_policy"
    assert len(result.findings) == len(README_DRAFTABLE_PRODUCT_FIELDS)
    assert backend.load(ORG_REPO).readme_poc_lifecycle.facts_hash == base.canonical_hash()
    assert (Path(result.bundle_dir) / "facts" / "product-facts.json").is_file()
    assert not (Path(result.bundle_dir) / "facts" / "proposed-product-truth.json").is_file()

    cached = product_truth.prepare_local_product_truth(
        ORG_REPO,
        snapshot,
        backend,
        client=object(),
    )
    assert cached.resolution_source == "durable_revision_cache"


def test_dotnet_fact_acceptance_contract_fails_closed_without_family() -> None:
    with pytest.raises(ValueError, match="family is required for the 'net' fact acceptance"):
        product_truth.current_fact_acceptance_contract("net")


def test_current_revision_candidate_is_salvaged_once_then_reused(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    salvaged = _facts()
    candidate = {"candidate": "current-revision"}
    salvage_calls = []
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )
    monkeypatch.setattr(product_truth, "load_salvage_candidate", lambda *args, **kwargs: candidate)

    def salvage(facts, observed_snapshot, observed_candidate):
        salvage_calls.append((facts, observed_snapshot, observed_candidate))
        return SimpleNamespace(facts=salvaged, findings=[])

    monkeypatch.setattr(product_truth, "salvage_product_truth_candidate", salvage)
    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("durable fact cache must avoid recollection"),
    )
    monkeypatch.setattr(
        product_truth,
        "salvage_product_truth_candidate",
        lambda *args, **kwargs: pytest.fail("durable fact cache must avoid resalvage"),
    )

    second = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert second.facts == first.facts
    assert first.resolution_source == "deterministic_salvage"
    assert second.resolution_source == "durable_revision_cache"
    assert second.proposed_product_truth == first.proposed_product_truth
    assert salvage_calls == [(base, snapshot, candidate)]
    assert len(backend.load(ORG_REPO).readme_poc_lifecycle.history) == 4


def test_truth_resolution_passes_current_readme_identity_to_historical_hint_loader(
    tmp_path, monkeypatch
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    observed: dict[str, object] = {}
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )

    def load(*args, **kwargs):
        observed.update(kwargs)
        return None

    monkeypatch.setattr(product_truth, "load_salvage_candidate", load)

    result = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert result.lifecycle_status == "BLOCKED_MISSING_EVIDENCE"
    assert observed["org_repo"] == ORG_REPO
    assert observed["source_revision"] == snapshot.source_revision
    assert observed["current_readme_sha256"] == snapshot.readme_sha256


def test_interrupted_sealed_fact_bundle_recovers_state_without_collection_or_llm(
    tmp_path, monkeypatch
):
    snapshot, backend, new_facts, _bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("sealed crash recovery must not recollect facts"),
    )
    recovered = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert recovered.resolution_source == "durable_revision_cache"
    assert recovered.facts == new_facts
    assert recovered.lifecycle_status == "BLOCKED_MISSING_EVIDENCE"
    assert lifecycle.facts_hash == new_facts.canonical_hash()
    assert [item.to_status for item in lifecycle.history[-2:]] == [
        "FACTS_COLLECTING",
        "BLOCKED_MISSING_EVIDENCE",
    ]
    latest_binding = lifecycle.fact_acceptance_history[-1]
    assert latest_binding.facts_hash == new_facts.canonical_hash()
    history_count = len(lifecycle.history)
    binding_count = len(lifecycle.fact_acceptance_history)
    state_version = backend.load(ORG_REPO).state_version
    save_calls = backend.save_calls

    repeated = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    repeated_lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert repeated.facts == new_facts
    assert len(repeated_lifecycle.history) == history_count
    assert len(repeated_lifecycle.fact_acceptance_history) == binding_count
    assert repeated_lifecycle == lifecycle
    assert backend.load(ORG_REPO).state_version == state_version
    assert backend.save_calls == save_calls


@pytest.mark.parametrize("starting_status", ["PROFILED", "FACTS_COLLECTING"])
def test_first_collection_sealed_bundle_recovers_from_fact_boundary(
    tmp_path, monkeypatch, starting_status
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    if starting_status == "FACTS_COLLECTING":
        transition_readme_poc_status(
            backend,
            ORG_REPO,
            "FACTS_COLLECTING",
            observed_by="test",
            reason="simulate collection interrupted before the durable outcome",
            source_revision=REVISION,
        )
    facts = _facts()
    contract = product_truth.current_fact_acceptance_contract("java")
    product_truth.write_local_poc_product_facts(
        snapshot,
        facts,
        findings=[],
        resolution_source="repository_and_policy",
        local_verification_contract_hash=product_truth.local_verification_contract_hash("java"),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("first-collection recovery must reuse sealed facts"),
    )

    recovered = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert recovered.facts == facts
    assert lifecycle.status == "FACTS_READY"
    assert lifecycle.fact_acceptance_history[-1].facts_hash == facts.canonical_hash()
    expected_tail = (
        ["FACTS_COLLECTING", "FACTS_READY"] if starting_status == "PROFILED" else ["FACTS_READY"]
    )
    assert [item.to_status for item in lifecycle.history[-len(expected_tail) :]] == expected_tail


def test_interrupted_fact_recovery_rejects_corrupt_bundle_before_collection(tmp_path, monkeypatch):
    snapshot, backend, _new_facts, bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    facts_path = bundle_dir / "facts" / "product-facts.json"
    facts_path.write_text(facts_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("corrupt sealed evidence must fail before recollection"),
    )

    with pytest.raises(RuntimeError, match="invalid checksum inventory"):
        product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)


@pytest.mark.parametrize("inventory_defect", ["missing", "extra"])
def test_interrupted_fact_recovery_requires_exact_checksum_inventory(
    tmp_path, monkeypatch, inventory_defect
):
    snapshot, backend, _new_facts, bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    if inventory_defect == "missing":
        (bundle_dir / "facts" / "findings.json").unlink()
    else:
        (bundle_dir / "facts" / "unexpected.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid checksum inventory"):
        product_truth.load_prepared_product_truth(ORG_REPO, backend, REVISION)


@pytest.mark.parametrize(
    ("resolution_source", "proposal", "prompt_hash", "error"),
    [
        (
            "agent_draft",
            None,
            prompt_registry.prompt_hash("draft_product_truth"),
            "requires a proposal artifact",
        ),
        (
            "repository_and_policy",
            {"audience": ["stale proposal"]},
            None,
            "cannot retain agent proposal provenance",
        ),
        ("unknown_mode", None, None, "unknown product-truth resolution source"),
    ],
)
def test_interrupted_fact_recovery_rejects_incoherent_proposal_provenance(
    tmp_path,
    monkeypatch,
    resolution_source,
    proposal,
    prompt_hash,
    error,
):
    snapshot, backend, new_facts, _bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    contract = product_truth.current_fact_acceptance_contract("java")
    product_truth.write_local_poc_product_facts(
        snapshot,
        new_facts,
        findings=[],
        resolution_source=resolution_source,
        proposed_product_truth=proposal,
        lifecycle_status="BLOCKED_MISSING_EVIDENCE",
        prompt_hash=prompt_hash,
        local_verification_contract_hash=product_truth.local_verification_contract_hash("java"),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    before = backend.states[ORG_REPO].model_dump(mode="json")

    with pytest.raises(RuntimeError, match=error):
        product_truth.load_prepared_product_truth(ORG_REPO, backend, REVISION)

    assert backend.states[ORG_REPO].model_dump(mode="json") == before


def test_interrupted_fact_recovery_refuses_to_overwrite_downstream_state(tmp_path, monkeypatch):
    snapshot, backend, _new_facts, _bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    state = backend.load(ORG_REPO)
    lifecycle = state.readme_poc_lifecycle
    old_hash = lifecycle.fact_acceptance_history[0].facts_hash
    backend.states[ORG_REPO] = state.model_copy(
        update={
            "readme_poc_lifecycle": lifecycle.model_copy(
                update={"status": "README_ASSESSED", "facts_hash": old_hash}
            )
        }
    )

    with pytest.raises(RuntimeError, match="evidence hash does not match lifecycle state"):
        product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)


def test_recovered_non_intake_failure_recollects_mismatched_fact_bundle(tmp_path, monkeypatch):
    snapshot, backend, new_facts, _bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    state = backend.load(ORG_REPO)
    lifecycle = state.readme_poc_lifecycle
    old_hash = lifecycle.fact_acceptance_history[0].facts_hash
    backend.states[ORG_REPO] = state.model_copy(
        update={
            "readme_poc_lifecycle": lifecycle.model_copy(
                update={
                    "status": "DETERMINISTIC_VALIDATED",
                    "facts_hash": old_hash,
                    "assessment_hash": "a" * 64,
                    "presentation_plan_hash": "b" * 64,
                    "candidate_hash": "c" * 64,
                    "history": [
                        *lifecycle.history,
                        ReadmePocTransitionV2(
                            from_status="AGENT_REVIEWING",
                            to_status="SYSTEM_FAILURE",
                            reason="review provider timed out",
                            observed_by="independent_verification",
                            source_revision=REVISION,
                        ),
                        ReadmePocTransitionV2(
                            from_status="SYSTEM_FAILURE",
                            to_status="DETERMINISTIC_VALIDATED",
                            reason=(
                                "recovered checksum-bound safe boundary after non-intake "
                                "system failure"
                            ),
                            observed_by="registry_intake",
                            source_revision=REVISION,
                        ),
                    ],
                }
            )
        }
    )
    collection_calls = []
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: collection_calls.append(org_repo) or {"product_facts_v2": new_facts},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )

    refreshed = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    recovered = backend.load(ORG_REPO).readme_poc_lifecycle
    assert collection_calls == [ORG_REPO]
    assert refreshed.facts == new_facts
    assert recovered.facts_hash == new_facts.canonical_hash()
    assert recovered.assessment_hash is None
    assert recovered.presentation_plan_hash is None
    assert recovered.candidate_hash is None
    assert [item.to_status for item in recovered.history[-2:]] == [
        "FACTS_COLLECTING",
        "BLOCKED_MISSING_EVIDENCE",
    ]


def test_interrupted_fact_recovery_rechecks_fresh_state_inside_cas(tmp_path, monkeypatch):
    snapshot, seeded_backend, _new_facts, _bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    racing = _RacingBackend()
    racing.states = dict(seeded_backend.states)
    initial = racing.states[ORG_REPO]
    lifecycle = initial.readme_poc_lifecycle
    advanced_lifecycle = lifecycle.model_copy(
        update={
            "status": "README_ASSESSED",
            "assessment_hash": "d" * 64,
        }
    )
    racing.race_state = initial.model_copy(update={"readme_poc_lifecycle": advanced_lifecycle})
    racing.race_on_load = 2

    with pytest.raises(RuntimeError, match="newer incompatible lifecycle state"):
        product_truth.load_prepared_product_truth(ORG_REPO, racing, REVISION)

    stored = racing.states[ORG_REPO].readme_poc_lifecycle
    assert stored.status == "README_ASSESSED"
    assert stored.assessment_hash == "d" * 64
    assert stored.facts_hash == lifecycle.facts_hash
    assert len(stored.history) == len(advanced_lifecycle.history)


def test_interrupted_fact_recovery_preserves_fresh_downstream_same_binding(tmp_path, monkeypatch):
    snapshot, seeded_backend, new_facts, _bundle_dir = _write_interrupted_fact_commit(
        tmp_path, monkeypatch
    )
    racing = _RacingBackend()
    racing.states = dict(seeded_backend.states)
    initial = racing.states[ORG_REPO]
    lifecycle = initial.readme_poc_lifecycle
    contract = product_truth.current_fact_acceptance_contract("java")
    new_binding = FactAcceptanceBindingV1(
        source_revision=REVISION,
        facts_hash=new_facts.canonical_hash(),
        contract_hash=contract.canonical_hash(),
        component_hashes=contract.component_hashes,
        outcome="BLOCKED_MISSING_EVIDENCE",
        observed_by="concurrent-owner",
        reason="concurrent owner accepted the same sealed graph",
    )
    advanced_lifecycle = lifecycle.model_copy(
        update={
            "status": "README_ASSESSED",
            "facts_hash": new_facts.canonical_hash(),
            "assessment_hash": "e" * 64,
            "fact_acceptance_history": [*lifecycle.fact_acceptance_history, new_binding],
        }
    )
    racing.race_state = initial.model_copy(update={"readme_poc_lifecycle": advanced_lifecycle})
    racing.race_on_load = 2

    cached = product_truth.load_prepared_product_truth(ORG_REPO, racing, REVISION)

    stored = racing.states[ORG_REPO].readme_poc_lifecycle
    assert cached is not None
    assert cached.lifecycle_status == "README_ASSESSED"
    assert stored.status == "README_ASSESSED"
    assert stored.assessment_hash == "e" * 64
    assert len(stored.history) == len(advanced_lifecycle.history)
    assert len(stored.fact_acceptance_history) == len(advanced_lifecycle.fact_acceptance_history)


def test_changed_facts_under_same_contract_append_one_exact_acceptance_binding(
    tmp_path, monkeypatch
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    verification_hash = {"value": "1" * 64}
    current_facts = {"value": _facts()}
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: {"product_facts_v2": current_facts["value"]},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="python", family="pdf"),
    )
    monkeypatch.setattr(
        product_truth,
        "local_verification_contract_hash",
        lambda ecosystem=None: verification_hash["value"],
    )

    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    changed_records = [
        (
            fact.model_copy(update={"value": ["Create and convert widgets"]})
            if fact.field == "product.capabilities"
            else fact
        )
        for fact in first.facts.facts
    ]
    current_facts["value"] = first.facts.model_copy(update={"facts": changed_records})
    verification_hash["value"] = "2" * 64

    refreshed = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle

    assert refreshed.facts.canonical_hash() != first.facts.canonical_hash()
    assert [binding.facts_hash for binding in lifecycle.fact_acceptance_history[-2:]] == [
        first.facts.canonical_hash(),
        refreshed.facts.canonical_hash(),
    ]
    binding_count = len(lifecycle.fact_acceptance_history)

    product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert len(backend.load(ORG_REPO).readme_poc_lifecycle.fact_acceptance_history) == binding_count


def test_verified_truth_reopens_a_trusted_lifecycle_without_promoting_trusted_facts(
    tmp_path, monkeypatch
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    switch_content_assurance(
        backend,
        ORG_REPO,
        "trusted_inherited",
        observed_by="test",
        reason="seed the lower-assurance lane",
    )
    trusted_state = backend.load(ORG_REPO)
    assert trusted_state is not None
    trusted_lifecycle = trusted_state.readme_poc_lifecycle
    assert trusted_lifecycle is not None
    backend.states[ORG_REPO] = trusted_state.model_copy(
        update={
            "readme_poc_lifecycle": trusted_lifecycle.model_copy(
                update={
                    "status": "TRUSTED_NO_OP_PROVEN",
                    "facts_hash": "f" * 64,
                    "candidate_hash": "c" * 64,
                }
            )
        }
    )
    verified_facts = _facts()
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: {"product_facts_v2": verified_facts},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="python", family="pdf"),
    )

    prepared = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    state = backend.load(ORG_REPO)
    assert state is not None
    lifecycle = state.readme_poc_lifecycle
    assert lifecycle is not None
    assert lifecycle.content_assurance == "repository_verified"
    assert lifecycle.status == "FACTS_READY"
    assert lifecycle.facts_hash == verified_facts.canonical_hash()
    assert lifecycle.assurance_history[-1].from_assurance == "trusted_inherited"
    assert lifecycle.assurance_history[-1].to_assurance == "repository_verified"
    assert prepared.resolution_source == "repository_and_policy"


def test_same_inputs_reuse_a_narrow_repository_evidence_block(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth, "collect_product_facts", lambda org_repo: {"product_facts_v2": base}
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="rust"),
    )

    monkeypatch.setattr(product_truth, "load_salvage_candidate", lambda *args, **kwargs: None)

    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    second = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert first.lifecycle_status == "BLOCKED_MISSING_EVIDENCE"
    assert second.resolution_source == "durable_revision_cache"
    assert len(first.findings) == len(README_DRAFTABLE_PRODUCT_FIELDS)


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


def test_legacy_valid_terminal_graph_binds_current_contract_without_reopening(
    tmp_path, monkeypatch
):
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
    _advance_to_no_op(backend)
    _remove_fact_acceptance_binding(backend, Path(prepared.bundle_dir))
    status_history_count = len(backend.load(ORG_REPO).readme_poc_lifecycle.history)
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("valid legacy facts must be rebound without recollection"),
    )

    cached = product_truth.load_prepared_product_truth(ORG_REPO, backend, REVISION)

    assert cached is not None
    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert lifecycle.status == "NO_OP_PROVEN"
    assert len(lifecycle.history) == status_history_count
    assert len(lifecycle.fact_acceptance_history) == 1
    assert lifecycle.fact_acceptance_contract_hash is not None
    manifest = json.loads((Path(prepared.bundle_dir) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["lifecycle_status"] == "FACTS_READY"
    assert manifest["fact_acceptance_contract_hash"] == lifecycle.fact_acceptance_contract_hash


def test_legacy_false_terminal_graph_reopens_at_current_blocked_fact_boundary(
    tmp_path, monkeypatch
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    facts = _facts_with_missing("installation.verified_acquisition")
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: {"product_facts_v2": facts},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="python", family="pdf"),
    )
    prepared = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    _advance_to_no_op(backend)
    _remove_fact_acceptance_binding(backend, Path(prepared.bundle_dir))
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("legacy migration must classify its persisted fact graph"),
    )

    cached = product_truth.load_prepared_product_truth(ORG_REPO, backend, REVISION)

    assert cached is not None
    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert lifecycle.status == "BLOCKED_MISSING_EVIDENCE"
    assert [item.to_status for item in lifecycle.history[-2:]] == [
        "FACTS_COLLECTING",
        "BLOCKED_MISSING_EVIDENCE",
    ]
    assert lifecycle.assessment_hash is None
    assert lifecycle.presentation_plan_hash is None
    assert lifecycle.candidate_hash is None
    assert len(lifecycle.fact_acceptance_history) == 1
    manifest = json.loads((Path(prepared.bundle_dir) / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["lifecycle_status"] == "BLOCKED_MISSING_EVIDENCE"
    assert manifest["complete"] is False
    assert "candidate_hash" not in manifest


def test_current_contract_false_terminal_graph_reopens_at_blocked_fact_boundary(
    tmp_path, monkeypatch
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    facts = _facts_with_missing("installation.verified_acquisition")
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: {"product_facts_v2": facts},
    )
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="python", family="pdf"),
    )
    prepared = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    _advance_to_no_op(backend)
    bundle_dir = Path(prepared.bundle_dir)
    (bundle_dir / "assessment").mkdir()
    (bundle_dir / "assessment" / "current-readme-assessment.json").write_text(
        "{}\n", encoding="utf-8"
    )
    (bundle_dir / "candidate").mkdir()
    (bundle_dir / "candidate" / "README.md").write_text(
        "# Stale approved candidate\n", encoding="utf-8"
    )
    (bundle_dir / "review").mkdir()
    (bundle_dir / "review" / "final-verdict.json").write_text(
        '{"verdict": "AGENT_APPROVED", "agent_approved": true}\n', encoding="utf-8"
    )
    (bundle_dir / "receipts").mkdir()
    (bundle_dir / "receipts" / "CANDIDATE_GENERATED.json").write_text(
        '{"target_stage": "CANDIDATE_GENERATED"}\n', encoding="utf-8"
    )
    (bundle_dir / "receipts" / "DETERMINISTIC_VALIDATED.json").write_text(
        '{"target_stage": "DETERMINISTIC_VALIDATED"}\n', encoding="utf-8"
    )
    monkeypatch.setattr(
        product_truth,
        "collect_product_facts",
        lambda org_repo: pytest.fail("current cached truth must be reclassified in place"),
    )

    cached = product_truth.load_prepared_product_truth(ORG_REPO, backend, REVISION)

    assert cached is not None
    assert cached.lifecycle_status == "BLOCKED_MISSING_EVIDENCE"
    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert lifecycle.status == "BLOCKED_MISSING_EVIDENCE"
    assert lifecycle.fact_acceptance_contract_hash is not None
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["lifecycle_status"] == "BLOCKED_MISSING_EVIDENCE"
    assert manifest["complete"] is False
    assert "candidate_hash" not in manifest
    for name in ("assessment", "planning", "candidate", "review", "receipts"):
        assert not (bundle_dir / name).exists()
    superseded_records = list((bundle_dir / "superseded").glob("*/superseded.json"))
    assert len(superseded_records) == 1
    superseded = json.loads(superseded_records[0].read_text(encoding="utf-8"))
    assert superseded["candidate_binding"] == "retained_artifact_without_current_manifest_binding"
    assert (superseded_records[0].parent / "review" / "final-verdict.json").is_file()
    checksums = (bundle_dir / "sha256sums.txt").read_text(encoding="utf-8")
    inventoried_paths = {line.split("  ", maxsplit=1)[1] for line in checksums.splitlines()}
    assert "review/final-verdict.json" not in inventoried_paths
    assert "receipts/CANDIDATE_GENERATED.json" not in inventoried_paths
    assert verify_sha256sums(bundle_dir)


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


def test_changed_verification_contract_revalidates_deterministic_salvage(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    base = _facts(draftable_missing=True)
    salvaged = _facts()
    verification_hash = {"value": "a" * 64}
    calls = []
    candidate = {"candidate": "current-revision"}

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
        "local_verification_contract_hash",
        lambda ecosystem=None: verification_hash["value"],
    )
    monkeypatch.setattr(product_truth, "load_salvage_candidate", lambda *args, **kwargs: candidate)

    def salvage(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(facts=salvaged, findings=[])

    monkeypatch.setattr(product_truth, "salvage_product_truth_candidate", salvage)

    first = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    cached = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    verification_hash["value"] = "b" * 64
    verifier_refreshed = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    assert first.resolution_source == "deterministic_salvage"
    assert cached.resolution_source == "durable_revision_cache"
    assert verifier_refreshed.resolution_source == "deterministic_salvage"
    assert len(calls) == 2
    assert backend.load(ORG_REPO).readme_poc_lifecycle.prompt_hash is None


@pytest.mark.parametrize(
    "changed_component",
    [
        "fact_schema",
        "fact_eligibility",
        "drafting_and_example_selection",
        "evidence_polarity",
    ],
)
def test_changed_fact_graph_contract_recollects_before_reaccepting(
    tmp_path, monkeypatch, changed_component
):
    snapshot = _snapshot(tmp_path)
    backend = _ready_backend(snapshot)
    facts = _facts()
    collection_calls = []
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")

    def collect(org_repo):
        collection_calls.append(org_repo)
        return {"product_facts_v2": facts}

    monkeypatch.setattr(product_truth, "collect_product_facts", collect)
    monkeypatch.setattr(
        product_truth,
        "require_listed",
        lambda org_repo: SimpleNamespace(ecosystem="java"),
    )
    original_contract = product_truth.current_fact_acceptance_contract("java")
    product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)
    changed_contract = original_contract.model_copy(
        update={
            "component_hashes": {
                **original_contract.component_hashes,
                changed_component: "0" * 64,
            }
        }
    )
    monkeypatch.setattr(
        product_truth,
        "current_fact_acceptance_contract",
        lambda ecosystem=None, family=None: changed_contract,
    )

    refreshed = product_truth.prepare_local_product_truth(ORG_REPO, snapshot, backend)

    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert collection_calls == [ORG_REPO, ORG_REPO]
    assert refreshed.lifecycle_status == "FACTS_READY"
    assert [item.to_status for item in lifecycle.history[-2:]] == [
        "FACTS_COLLECTING",
        "FACTS_READY",
    ]
    assert lifecycle.fact_acceptance_contract_hash == changed_contract.canonical_hash()
