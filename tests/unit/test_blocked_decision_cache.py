"""The blocked-decision cache: a triaged BLOCKED outcome is never re-executed
until one of its bound dependency fingerprints actually changes.

Regression anchor (2026-08-18 Gate A recovery): known-BLOCKED repositories were
re-run in full every portfolio pass -- re-spending provider calls on already-
triaged failures and starving the 22 never-yet-processed registry entries of
slice budget, while non-deterministic corroboration re-rolls turned unchanged
inputs into fluctuating claim counts.
"""

from __future__ import annotations

from readme_agent.supervisor.blocked_decision_cache import (
    BlockedDecisionRecordV1,
    clear_blocked_decision,
    evaluate_blocked_decision_cache,
    load_blocked_decision,
    persist_blocked_decision,
    record_blocked_outcome,
)

_DEPS = {
    "source_revision": "a" * 40,
    "control_plane_fingerprint": "c" * 64,
    "template_hash": "t" * 64,
    "prompt_dependency_hashes": {"PLAN_READY": "p" * 64},
}


def _record(path, reason="claim accountability has 2 blocking claim(s)", deps=None):
    return record_blocked_outcome(
        path,
        org_repo="org/repo",
        status="FACTS_READY",
        exit_code=1,
        blocked_reason=reason,
        blocked_category="agent_fixable",
        dependencies=dict(_DEPS) if deps is None else deps,
        run_id="run-1",
    )


class TestRoundTrip:
    def test_unchanged_dependencies_reuse_the_persisted_decision(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        decision = evaluate_blocked_decision_cache(
            path, org_repo="org/repo", current_dependencies=dict(_DEPS)
        )
        assert decision.reusable is True
        assert decision.mismatch_reasons == []
        assert decision.record is not None
        assert decision.record.status == "FACTS_READY"
        assert decision.record.exit_code == 1
        assert decision.record.blocked_reason.startswith("claim accountability")
        assert decision.record.blocked_category == "agent_fixable"
        assert decision.record.consecutive_count == 1

    def test_missing_file_is_not_reusable(self, tmp_path):
        decision = evaluate_blocked_decision_cache(
            tmp_path / "absent.json", org_repo="org/repo", current_dependencies=dict(_DEPS)
        )
        assert decision.reusable is False
        assert decision.mismatch_reasons == ["blocked_decision_missing_or_invalid"]

    def test_malformed_payload_is_not_reusable(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        path.write_text("{not json", encoding="utf-8")
        decision = evaluate_blocked_decision_cache(
            path, org_repo="org/repo", current_dependencies=dict(_DEPS)
        )
        assert decision.reusable is False
        assert decision.mismatch_reasons == ["blocked_decision_missing_or_invalid"]
        assert load_blocked_decision(path) is None

    def test_unknown_schema_version_is_not_reusable(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        record = BlockedDecisionRecordV1(
            org_repo="org/repo",
            status="FACTS_READY",
            exit_code=1,
            blocked_reason="x",
            dependencies=dict(_DEPS),
        )
        payload = record.model_dump(mode="json")
        payload["schema_version"] = 999
        path.write_text(__import__("json").dumps(payload), encoding="utf-8")
        assert load_blocked_decision(path) is None


class TestInvalidation:
    def test_every_single_dependency_change_invalidates(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        for key in _DEPS:
            current = dict(_DEPS)
            current[key] = "different"
            decision = evaluate_blocked_decision_cache(
                path, org_repo="org/repo", current_dependencies=current
            )
            assert decision.reusable is False, key
            assert decision.mismatch_reasons == [f"{key}_changed"], key

    def test_a_newly_added_dependency_key_invalidates(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        current = dict(_DEPS)
        current["new_contract_hash"] = "n" * 64
        decision = evaluate_blocked_decision_cache(
            path, org_repo="org/repo", current_dependencies=current
        )
        assert decision.reusable is False
        assert decision.mismatch_reasons == ["new_contract_hash_changed"]

    def test_wrong_repository_never_reuses(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        decision = evaluate_blocked_decision_cache(
            path, org_repo="org/other", current_dependencies=dict(_DEPS)
        )
        assert decision.reusable is False
        assert "org_repo_mismatch" in decision.mismatch_reasons


class TestLiveOutcomeBookkeeping:
    def test_same_reason_increments_live_reproduction_count(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        first = _record(path)
        second = _record(path)
        assert first.consecutive_count == 1
        assert second.consecutive_count == 2

    def test_a_different_reason_resets_the_count(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        _record(path)
        changed = _record(path, reason="unauthorized protected-content loss: x")
        assert changed.consecutive_count == 1

    def test_cache_reuse_does_not_inflate_the_count(self, tmp_path):
        # Only record_blocked_outcome (a live run) writes; evaluating never does.
        path = tmp_path / "blocked-decision.json"
        _record(path)
        for _ in range(3):
            evaluate_blocked_decision_cache(
                path, org_repo="org/repo", current_dependencies=dict(_DEPS)
            )
        persisted = load_blocked_decision(path)
        assert persisted is not None
        assert persisted.consecutive_count == 1

    def test_clear_is_idempotent(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        clear_blocked_decision(path)
        assert load_blocked_decision(path) is None
        clear_blocked_decision(path)  # second clear: no error

    def test_persist_is_a_full_replacement(self, tmp_path):
        path = tmp_path / "blocked-decision.json"
        _record(path)
        replacement = BlockedDecisionRecordV1(
            org_repo="org/repo",
            status="BLOCKED_MISSING_EVIDENCE",
            exit_code=1,
            blocked_reason="product_truth_not_ready:BLOCKED_MISSING_EVIDENCE",
            blocked_category="infra_external",
            dependencies={"source_revision": "b" * 40},
        )
        persist_blocked_decision(path, replacement)
        persisted = load_blocked_decision(path)
        assert persisted is not None
        assert persisted.status == "BLOCKED_MISSING_EVIDENCE"
        assert persisted.dependencies == {"source_revision": "b" * 40}
