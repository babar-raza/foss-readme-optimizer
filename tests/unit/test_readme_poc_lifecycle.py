"""`RPOC-070`: per-repo README-POC lifecycle status vocabulary
(`DISCOVERED` .. `PR_PROOF_COMPLETE`) -- transition-table legality,
serialization round-trips, and additive-field migration for old persisted
state / manifest snapshots written before this field existed.

Mirrors `tests/unit/test_lifecycle_state.py`'s own fake-`StateBackend` shape
(a `RunStateV2`-keyed in-memory dict) rather than importing it, matching this
codebase's convention of each state-machine test module owning its own small
fake.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from readme_agent.errors import StateBackendError
from readme_agent.evidence.manifest_v3 import RunManifestV3
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.lifecycle_schema import (
    ReadmePocLifecycleStateV1,
    ReadmePocLifecycleStateV2,
    ReadmePocTransitionV1,
    ReadmePocTransitionV2,
)
from readme_agent.state.migrations import ensure_run_state_v2, load_run_state_json
from readme_agent.state.readme_poc_lifecycle import (
    bind_fact_acceptance_contract,
    legal_next_readme_poc_statuses,
    record_deterministic_validation_failure,
    record_product_facts_outcome,
    record_readme_candidate_artifacts,
    record_repository_profile,
    record_repository_snapshot,
    transition_readme_poc_status,
)
from readme_agent.state.schema import RunStateV1, RunStateV2


class FakeReadmePocBackend:
    """In-memory `StateBackend`, `RunStateV2`-keyed -- mirrors
    `test_lifecycle_state.py::LifecycleBackend` exactly, since `state/
    readme_poc_lifecycle.py::transition_readme_poc_status()` goes through the
    same `state/cas.py::save_state_patch()` primitive `transition_trigger()`
    already uses."""

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


class TestValidTransitions:
    def test_unchanged_deterministic_failure_retry_is_idempotent(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in (
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
        ):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="advance",
                source_revision="abc123",
            )

        first = record_deterministic_validation_failure(
            backend,
            org_repo,
            observed_by="test",
            reason="bundle rejected",
            evidence_refs=["bundle-a"],
        )
        second = record_deterministic_validation_failure(
            backend,
            org_repo,
            observed_by="test",
            reason="unchanged bundle rejected again",
            evidence_refs=["bundle-b"],
        )

        assert first.status == "DETERMINISTIC_VALIDATION_FAILED"
        assert second == first
        assert first.history[-1].evidence_refs == ["bundle-a"]

    def test_snapshot_record_is_idempotent_for_the_same_revision(self):
        backend = FakeReadmePocBackend()
        first = record_repository_snapshot(
            backend,
            "org/repo",
            source_revision="a" * 40,
            evidence_refs=["repository_snapshot_v1"],
        )
        second = record_repository_snapshot(
            backend,
            "org/repo",
            source_revision="a" * 40,
            evidence_refs=["repository_snapshot_v1"],
        )
        assert first.status == "SNAPSHOTTED"
        assert second.history == first.history

    def test_changed_snapshot_reopens_and_clears_derived_state(self):
        backend = FakeReadmePocBackend()
        record_repository_snapshot(
            backend,
            "org/repo",
            source_revision="a" * 40,
            evidence_refs=["repository_snapshot_v1"],
        )
        transition_readme_poc_status(
            backend,
            "org/repo",
            "PROFILED",
            observed_by="test",
            reason="profiled",
        )
        transition_readme_poc_status(
            backend,
            "org/repo",
            "FACTS_COLLECTING",
            observed_by="test",
            reason="collecting",
        )
        transition_readme_poc_status(
            backend,
            "org/repo",
            "FACTS_READY",
            observed_by="test",
            reason="facts",
            facts_hash="f" * 64,
            prompt_hash="p" * 64,
        )

        reopened = record_repository_snapshot(
            backend,
            "org/repo",
            source_revision="b" * 40,
            evidence_refs=["repository_snapshot_v1:new"],
        )

        assert reopened.status == "SNAPSHOTTED"
        assert reopened.source_revision == "b" * 40
        assert reopened.facts_hash is None
        assert reopened.prompt_hash is None
        assert reopened.repair_attempts_for_revision == 0

    def test_profile_record_resumes_idempotently_after_snapshot(self):
        backend = FakeReadmePocBackend()
        revision = "a" * 40
        record_repository_snapshot(
            backend,
            "org/repo",
            source_revision=revision,
            evidence_refs=["repository_snapshot_v1"],
        )

        first = record_repository_profile(
            backend,
            "org/repo",
            source_revision=revision,
            evidence_refs=["repository_profile"],
        )
        second = record_repository_profile(
            backend,
            "org/repo",
            source_revision=revision,
            evidence_refs=["repository_profile"],
        )

        assert first.status == "PROFILED"
        assert second.history == first.history

    def test_profile_record_rejects_missing_or_mismatched_snapshot(self):
        backend = FakeReadmePocBackend()
        with pytest.raises(StateBackendError, match="before its snapshot"):
            record_repository_profile(
                backend,
                "org/repo",
                source_revision="a" * 40,
                evidence_refs=["repository_profile"],
            )
        record_repository_snapshot(
            backend,
            "org/repo",
            source_revision="a" * 40,
            evidence_refs=["repository_snapshot_v1"],
        )
        with pytest.raises(StateBackendError, match="durable snapshot"):
            record_repository_profile(
                backend,
                "org/repo",
                source_revision="b" * 40,
                evidence_refs=["repository_profile"],
            )

    def test_full_happy_path_reaches_pr_proof_complete_with_full_history(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        happy_path = [
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        ]
        result = None
        for to_status in happy_path:
            result = transition_readme_poc_status(
                backend,
                org_repo,
                to_status,
                observed_by="test-suite",
                reason=f"advance to {to_status}",
            )
        assert result is not None
        assert result.status == "PR_PROOF_COMPLETE"
        assert [entry.to_status for entry in result.history] == happy_path
        assert result.history[0].from_status == "DISCOVERED"
        assert result.history[-1].from_status == "PR_ELIGIBLE"
        # Durably persisted, not just returned.
        persisted = backend.load(org_repo)
        assert persisted.readme_poc_lifecycle.status == "PR_PROOF_COMPLETE"

    def test_fact_conflict_reenters_facts_collecting_then_reaches_facts_ready(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        transition_readme_poc_status(backend, org_repo, "SNAPSHOTTED", observed_by="t", reason="r")
        transition_readme_poc_status(backend, org_repo, "PROFILED", observed_by="t", reason="r")
        transition_readme_poc_status(
            backend, org_repo, "FACTS_COLLECTING", observed_by="t", reason="r"
        )
        transition_readme_poc_status(
            backend,
            org_repo,
            "BLOCKED_FACT_CONFLICT",
            observed_by="t",
            reason="conflicting license facts",
        )
        conflict_resolved = transition_readme_poc_status(
            backend,
            org_repo,
            "FACTS_COLLECTING",
            observed_by="t",
            reason="conflict resolved, re-collecting",
        )
        assert conflict_resolved.status == "FACTS_COLLECTING"
        ready = transition_readme_poc_status(
            backend, org_repo, "FACTS_READY", observed_by="t", reason="r"
        )
        assert ready.status == "FACTS_READY"

    def test_deterministic_validation_failure_repairs_back_to_candidate_generated(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        transition_readme_poc_status(
            backend,
            org_repo,
            "SNAPSHOTTED",
            observed_by="t",
            reason="r",
            source_revision="a" * 40,
        )
        for status in [
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
        ]:
            transition_readme_poc_status(backend, org_repo, status, observed_by="t", reason="r")
        transition_readme_poc_status(
            backend, org_repo, "CANDIDATE_GENERATED", observed_by="t", reason="drafted"
        )
        transition_readme_poc_status(
            backend,
            org_repo,
            "DETERMINISTIC_VALIDATION_FAILED",
            observed_by="t",
            reason="schema check failed",
        )
        repairing = transition_readme_poc_status(
            backend, org_repo, "REPAIRING", observed_by="t", reason="repairing candidate"
        )
        assert repairing.status == "REPAIRING"
        regenerated = transition_readme_poc_status(
            backend,
            org_repo,
            "CANDIDATE_GENERATED",
            observed_by="t",
            reason="repaired candidate regenerated",
            evidence_refs=["evidence/repair-1.json"],
        )
        assert regenerated.status == "CANDIDATE_GENERATED"
        assert regenerated.history[-1].evidence_refs == ["evidence/repair-1.json"]

    def test_deterministic_validation_failure_reopens_when_fact_inputs_change(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        transition_readme_poc_status(
            backend,
            org_repo,
            "SNAPSHOTTED",
            observed_by="t",
            reason="r",
            source_revision="a" * 40,
        )
        for status in [
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATION_FAILED",
        ]:
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="t",
                reason="r",
            )

        reopened = transition_readme_poc_status(
            backend,
            org_repo,
            "FACTS_COLLECTING",
            observed_by="supervisor_product_truth",
            reason="fact inputs changed; invalidating the failed candidate",
        )

        assert reopened.status == "FACTS_COLLECTING"

    def test_agent_review_rejection_repairs_back_to_candidate_generated(self):
        """The goal's own explicit example: `AGENT_REVIEW_REJECTED` ->
        `REPAIRING` -> `CANDIDATE_GENERATED` again."""
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in [
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
        ]:
            transition_readme_poc_status(backend, org_repo, status, observed_by="t", reason="r")
        transition_readme_poc_status(
            backend,
            org_repo,
            "AGENT_REVIEW_REJECTED",
            observed_by="independent-reviewer",
            reason="generic template symptoms",
        )
        transition_readme_poc_status(backend, org_repo, "REPAIRING", observed_by="t", reason="r")
        regenerated = transition_readme_poc_status(
            backend, org_repo, "CANDIDATE_GENERATED", observed_by="t", reason="r"
        )
        assert regenerated.status == "CANDIDATE_GENERATED"

    def test_repair_execution_failure_is_recorded_and_recoverable(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in [
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATION_FAILED",
            "REPAIRING",
        ]:
            transition_readme_poc_status(backend, org_repo, status, observed_by="t", reason="r")

        failed = transition_readme_poc_status(
            backend,
            org_repo,
            "SYSTEM_FAILURE",
            observed_by="candidate-repair",
            reason="renderer execution failed",
        )
        assert failed.status == "SYSTEM_FAILURE"

        recovered = transition_readme_poc_status(
            backend,
            org_repo,
            "REPAIRING",
            observed_by="recovery-sweep",
            reason="retry repair",
        )
        assert recovered.status == "REPAIRING"

    def test_human_rejection_routes_through_repairing_back_to_candidate_generated(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in [
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
        ]:
            transition_readme_poc_status(backend, org_repo, status, observed_by="t", reason="r")
        rejected = transition_readme_poc_status(
            backend, org_repo, "REPAIRING", observed_by="human-reviewer", reason="human rejected"
        )
        assert rejected.status == "REPAIRING"
        back = transition_readme_poc_status(
            backend, org_repo, "CANDIDATE_GENERATED", observed_by="t", reason="r"
        )
        assert back.status == "CANDIDATE_GENERATED"


class TestInvalidTransitions:
    def test_skipping_a_stage_is_rejected(self):
        backend = FakeReadmePocBackend()
        with pytest.raises(StateBackendError, match="invalid README-POC lifecycle transition"):
            transition_readme_poc_status(
                backend, "org/repo", "PROFILED", observed_by="t", reason="skip ahead"
            )

    def test_same_status_self_loop_is_rejected(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        transition_readme_poc_status(backend, org_repo, "SNAPSHOTTED", observed_by="t", reason="r")
        with pytest.raises(StateBackendError, match="invalid README-POC lifecycle transition"):
            transition_readme_poc_status(
                backend, org_repo, "SNAPSHOTTED", observed_by="t", reason="repeat"
            )

    def test_pr_proof_reopens_at_a_new_snapshot(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in [
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_APPROVED",
            "NO_OP_PROVEN",
            "HUMAN_REVIEW_READY",
            "HUMAN_ACCEPTED",
            "PR_ELIGIBLE",
            "PR_PROOF_COMPLETE",
        ]:
            transition_readme_poc_status(backend, org_repo, status, observed_by="t", reason="r")
        assert legal_next_readme_poc_statuses("PR_PROOF_COMPLETE") == frozenset(
            {"SNAPSHOTTED", "FACTS_COLLECTING", "README_ASSESSED"}
        )
        reopened = transition_readme_poc_status(
            backend,
            org_repo,
            "SNAPSHOTTED",
            observed_by="t",
            reason="new source snapshot",
            source_revision="b" * 40,
        )
        assert reopened.status == "SNAPSHOTTED"
        assert reopened.source_revision == "b" * 40

    def test_invalid_transition_does_not_persist_a_partial_write(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        with pytest.raises(StateBackendError):
            transition_readme_poc_status(
                backend, org_repo, "FACTS_READY", observed_by="t", reason="skip ahead"
            )
        assert backend.load(org_repo) is None


class TestLegalNextIntrospection:
    def test_matches_the_transition_table_for_a_branching_status(self):
        assert legal_next_readme_poc_statuses("CANDIDATE_GENERATED") == frozenset(
            {
                "DETERMINISTIC_VALIDATION_FAILED",
                "DETERMINISTIC_VALIDATED",
                "FACTS_COLLECTING",
                "README_ASSESSED",
                "SNAPSHOTTED",
                "SYSTEM_FAILURE",
            }
        )

    def test_returns_a_frozenset_not_the_live_mutable_table(self):
        result = legal_next_readme_poc_statuses("DISCOVERED")
        assert isinstance(result, frozenset)
        assert result == frozenset({"SNAPSHOTTED", "SYSTEM_FAILURE"})


class TestProductFactsBoundary:
    def test_current_contract_can_bind_without_reopening_a_valid_later_stage(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in ("SNAPSHOTTED", "PROFILED", "FACTS_COLLECTING"):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="advance",
                source_revision="abc123",
            )
        transition_readme_poc_status(
            backend,
            org_repo,
            "FACTS_READY",
            observed_by="test",
            reason="legacy facts",
            source_revision="abc123",
            facts_hash="facts-a",
        )
        transition_readme_poc_status(
            backend,
            org_repo,
            "README_ASSESSED",
            observed_by="test",
            reason="later stage remains valid",
            source_revision="abc123",
        )
        history_count = len(backend.load(org_repo).readme_poc_lifecycle.history)

        bound = bind_fact_acceptance_contract(
            backend,
            org_repo,
            source_revision="abc123",
            facts_hash="facts-a",
            contract_hash="c" * 64,
            component_hashes={"evidence_polarity": "p" * 64},
            outcome="FACTS_READY",
        )
        repeated = bind_fact_acceptance_contract(
            backend,
            org_repo,
            source_revision="abc123",
            facts_hash="facts-a",
            contract_hash="c" * 64,
            component_hashes={"evidence_polarity": "p" * 64},
            outcome="FACTS_READY",
        )

        assert bound.status == "README_ASSESSED"
        assert repeated.status == "README_ASSESSED"
        assert len(repeated.history) == history_count
        assert len(repeated.fact_acceptance_history) == 1
        assert repeated.fact_acceptance_contract_hash == "c" * 64
        assert repeated.fact_acceptance_history[0].source_revision == "abc123"
        assert repeated.fact_acceptance_history[0].facts_hash == "facts-a"

    def test_records_collecting_then_ready_and_is_idempotent(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        record_repository_snapshot(
            backend, org_repo, source_revision="abc123", evidence_refs=["snapshot"]
        )
        record_repository_profile(
            backend, org_repo, source_revision="abc123", evidence_refs=["profile"]
        )

        first = record_product_facts_outcome(
            backend,
            org_repo,
            source_revision="abc123",
            facts_hash="facts-a",
            outcome="FACTS_READY",
            evidence_refs=["facts"],
        )
        second = record_product_facts_outcome(
            backend,
            org_repo,
            source_revision="abc123",
            facts_hash="facts-a",
            outcome="FACTS_READY",
            evidence_refs=["facts"],
        )

        assert [item.to_status for item in first.history] == [
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
        ]
        assert second == first

    def test_changed_facts_reopen_a_dependent_later_stage(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in ("SNAPSHOTTED", "PROFILED", "FACTS_COLLECTING", "FACTS_READY"):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="advance",
                source_revision="abc123",
                facts_hash="facts-a" if status == "FACTS_READY" else None,
            )
        transition_readme_poc_status(
            backend,
            org_repo,
            "README_ASSESSED",
            observed_by="test",
            reason="advance",
            source_revision="abc123",
        )
        for status in (
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
            "AGENT_REVIEWING",
            "AGENT_REVIEW_REJECTED",
            "REPAIRING",
            "CANDIDATE_GENERATED",
        ):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="consume one repair attempt against the old facts",
                source_revision="abc123",
            )
        assert backend.load(org_repo).readme_poc_lifecycle.repair_attempts_for_revision == 1

        reopened = record_product_facts_outcome(
            backend,
            org_repo,
            source_revision="abc123",
            facts_hash="facts-b",
            outcome="BLOCKED_MISSING_EVIDENCE",
            evidence_refs=["new-facts"],
        )

        assert reopened.status == "BLOCKED_MISSING_EVIDENCE"
        assert [item.to_status for item in reopened.history[-2:]] == [
            "FACTS_COLLECTING",
            "BLOCKED_MISSING_EVIDENCE",
        ]
        assert reopened.facts_hash == "facts-b"
        assert reopened.repair_attempts_for_revision == 0


class TestReadmeCandidateBoundary:
    def test_blocked_facts_continue_through_safe_composition_and_retry_is_idempotent(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in ("SNAPSHOTTED", "PROFILED", "FACTS_COLLECTING"):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="advance",
                source_revision="abc123",
            )
        transition_readme_poc_status(
            backend,
            org_repo,
            "BLOCKED_MISSING_EVIDENCE",
            observed_by="test",
            reason="one optional README claim lacks evidence",
            source_revision="abc123",
            facts_hash="facts-a",
        )

        first = record_readme_candidate_artifacts(
            backend,
            org_repo,
            source_revision="abc123",
            assessment_hash="assessment-a",
            presentation_plan_hash="plan-a",
            candidate_hash="candidate-a",
            reviewer_standard_hash="reviewer-a",
            evidence_refs=["assessment", "plan", "candidate"],
        )
        second = record_readme_candidate_artifacts(
            backend,
            org_repo,
            source_revision="abc123",
            assessment_hash="assessment-a",
            presentation_plan_hash="plan-a",
            candidate_hash="candidate-a",
            reviewer_standard_hash="reviewer-a",
            evidence_refs=["assessment", "plan", "candidate"],
        )

        assert first.status == "CANDIDATE_GENERATED"
        assert first.assessment_hash == "assessment-a"
        assert first.presentation_plan_hash == "plan-a"
        assert first.candidate_hash == "candidate-a"
        assert [item.to_status for item in first.history[-3:]] == [
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
        ]
        assert second == first

    def test_failed_validation_restart_retries_without_spending_content_repair_budget(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in ("SNAPSHOTTED", "PROFILED", "FACTS_COLLECTING", "FACTS_READY"):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="advance",
                source_revision="abc123",
            )
        record_readme_candidate_artifacts(
            backend,
            org_repo,
            source_revision="abc123",
            assessment_hash="assessment-a",
            presentation_plan_hash="plan-a",
            candidate_hash="candidate-a",
            reviewer_standard_hash="reviewer-a",
            evidence_refs=["candidate"],
        )
        transition_readme_poc_status(
            backend,
            org_repo,
            "DETERMINISTIC_VALIDATION_FAILED",
            observed_by="test",
            reason="verifier rejected",
        )

        resumed = record_readme_candidate_artifacts(
            backend,
            org_repo,
            source_revision="abc123",
            assessment_hash="assessment-a",
            presentation_plan_hash="plan-a",
            candidate_hash="candidate-a",
            reviewer_standard_hash="reviewer-a",
            evidence_refs=["candidate"],
        )

        assert resumed.status == "CANDIDATE_GENERATED"
        assert resumed.repair_attempts_for_revision == 0
        assert [item.to_status for item in resumed.history[-3:]] == [
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
        ]

    def test_changed_reviewer_standard_resets_only_its_obsolete_repair_budget(self):
        backend = FakeReadmePocBackend()
        org_repo = "org/repo"
        for status in (
            "SNAPSHOTTED",
            "PROFILED",
            "FACTS_COLLECTING",
            "FACTS_READY",
            "README_ASSESSED",
            "PLAN_READY",
            "CANDIDATE_GENERATED",
            "DETERMINISTIC_VALIDATED",
        ):
            transition_readme_poc_status(
                backend,
                org_repo,
                status,
                observed_by="test",
                reason="advance",
                source_revision="abc123",
            )
        transition_readme_poc_status(
            backend,
            org_repo,
            "AGENT_REVIEWING",
            observed_by="test",
            reason="old review",
            reviewer_standard_hash="reviewer-a",
        )
        for _attempt in range(2):
            transition_readme_poc_status(
                backend,
                org_repo,
                "AGENT_REVIEW_REJECTED",
                observed_by="test",
                reason="rejected",
            )
            transition_readme_poc_status(
                backend,
                org_repo,
                "REPAIRING",
                observed_by="test",
                reason="repair",
            )
            transition_readme_poc_status(
                backend,
                org_repo,
                "CANDIDATE_GENERATED",
                observed_by="test",
                reason="regenerated",
            )
            transition_readme_poc_status(
                backend,
                org_repo,
                "DETERMINISTIC_VALIDATED",
                observed_by="test",
                reason="validated",
            )
            if _attempt == 0:
                transition_readme_poc_status(
                    backend,
                    org_repo,
                    "AGENT_REVIEWING",
                    observed_by="test",
                    reason="same review",
                    reviewer_standard_hash="reviewer-a",
                )

        changed = transition_readme_poc_status(
            backend,
            org_repo,
            "AGENT_REVIEWING",
            observed_by="test",
            reason="new review standard",
            reviewer_standard_hash="reviewer-b",
        )

        assert changed.repair_attempts_for_revision == 0
        assert changed.reviewer_standard_hash == "reviewer-b"


class TestSerializationRoundTrip:
    def test_lifecycle_state_round_trips_through_json(self):
        state = ReadmePocLifecycleStateV1(
            status="PLAN_READY",
            history=[
                ReadmePocTransitionV1(
                    from_status="DISCOVERED",
                    to_status="SNAPSHOTTED",
                    reason="cloned",
                    observed_by="orchestrator",
                    evidence_refs=["evidence/clone.json"],
                )
            ],
            details={"note": "example"},
        )
        restored = ReadmePocLifecycleStateV1.model_validate_json(state.model_dump_json())
        assert restored == state

    def test_v2_state_round_trips_with_provenance_fields(self):
        state = ReadmePocLifecycleStateV2(
            status="AGENT_APPROVED",
            source_revision="abc123",
            facts_hash="facts",
            history=[
                ReadmePocTransitionV2(
                    from_status="AGENT_REVIEWING",
                    to_status="AGENT_APPROVED",
                    reason="review passed",
                    observed_by="independent-reviewer",
                    source_revision="abc123",
                )
            ],
        )
        assert ReadmePocLifecycleStateV2.model_validate_json(state.model_dump_json()) == state

    def test_run_state_v1_with_populated_lifecycle_round_trips(self):
        original = RunStateV1(
            org_repo="org/repo",
            readme_poc_lifecycle=ReadmePocLifecycleStateV1(status="FACTS_READY"),
        )
        restored = RunStateV1.model_validate_json(original.model_dump_json())
        assert restored == original
        assert restored.readme_poc_lifecycle.status == "FACTS_READY"

    def test_run_manifest_v3_round_trips_with_readme_poc_fields(self):
        manifest = RunManifestV3(
            run_id="run-1",
            org_repo="org/repo",
            status="ok",
            timestamp="2026-07-25T00:00:00+00:00",
            readme_poc_status="AGENT_APPROVED",
            readme_poc_transitions=[
                ReadmePocTransitionV1(
                    from_status="CANDIDATE_GENERATED",
                    to_status="AGENT_APPROVED",
                    reason="independent review passed",
                    observed_by="independent-reviewer",
                )
            ],
        )
        restored = RunManifestV3.model_validate_json(manifest.model_dump_json())
        assert restored == manifest


class TestMigrationFromStateWithoutTheNewField:
    def test_old_run_state_v1_dict_without_the_field_still_validates(self):
        """Simulates a durable-state snapshot written before `RPOC-070`
        added `readme_poc_lifecycle` -- the additive-pydantic-field
        convention this project's own memory (`autosave-memory-required`
        aside; see repo docs) requires: an old blob with no such key
        deserializes cleanly to the safe `None` default, never a
        `ValidationError`."""
        old_snapshot = {
            "org_repo": "org/repo",
            "state_version": 3,
            "accepted_status": "GENERATED",
        }
        assert "readme_poc_lifecycle" not in old_snapshot
        migrated = RunStateV1.model_validate(old_snapshot)
        assert migrated.readme_poc_lifecycle is None

    def test_old_run_state_v2_json_without_the_field_migrates_via_load_run_state_json(self):
        old_v2_snapshot = {
            "schema_version": 2,
            "org_repo": "org/repo",
            "state_version": 5,
        }
        loaded = load_run_state_json(json.dumps(old_v2_snapshot))
        assert loaded.readme_poc_lifecycle is None
        # And the now-migrated record can immediately begin a real transition
        # -- proves the default is not just "parses" but "usable."
        backend = FakeReadmePocBackend()
        backend.states["org/repo"] = loaded.model_copy(update={"state_version": 0})
        result = transition_readme_poc_status(
            backend, "org/repo", "SNAPSHOTTED", observed_by="t", reason="first real transition"
        )
        assert result.status == "SNAPSHOTTED"
        assert result.history[0].from_status == "DISCOVERED"

    def test_old_run_manifest_v3_dict_without_the_fields_still_validates(self):
        old_manifest = {
            "run_id": "run-0",
            "org_repo": "org/repo",
            "status": "ok",
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
        restored = RunManifestV3.model_validate(old_manifest)
        assert restored.readme_poc_status is None
        assert restored.readme_poc_transitions == []

    def test_unknown_status_value_fails_closed_not_silently_accepted(self):
        with pytest.raises(ValidationError):
            ReadmePocLifecycleStateV1.model_validate({"status": "NOT_A_REAL_STATUS"})
        with pytest.raises(ValidationError):
            ReadmePocLifecycleStateV2.model_validate({"status": "NOT_A_REAL_STATUS"})
