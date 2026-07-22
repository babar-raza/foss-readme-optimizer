"""Pure, standalone helpers in `state/domain_state.py` -- `merge_details()`
and `record_failure_or_reset()`. Kept separate from `test_state_backend.py`'s
`TestSaveDomain`, which is about the backend CAS/lock mechanics `save_domain()`
itself needs; these two are plain functions with no backend interaction."""

from datetime import UTC, datetime, timedelta

import pytest
from langgraph.graph import END, START, StateGraph

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.domain_state import (
    _classify_error_reason,
    compute_domain_coverage_complete,
    is_domain_covered,
    mark_domain_skipped,
    merge_details,
    merge_unrecorded_failures,
    record_failure_or_reset,
    save_domain,
    save_domain_with_failure_tracking,
)
from readme_agent.state.schema import DomainStateV1, RunStateV1


class TestMergeDetails:
    def test_merges_new_keys_onto_existing_details(self):
        state = DomainStateV1(domain="test", details={"a": 1})
        assert merge_details(state, b=2) == {"a": 1, "b": 2}

    def test_new_key_overrides_an_existing_one_with_the_same_name(self):
        state = DomainStateV1(domain="test", details={"a": 1})
        assert merge_details(state, a=2) == {"a": 2}

    def test_three_sequential_langgraph_nodes_each_see_the_accumulated_details(self):
        """The actual regression this helper exists to prevent: without it, a
        node's bare `{"details": {...}}` return replaces the whole field
        (LangGraph's default last-write-wins channel behavior for a plain,
        un-annotated dict field), silently erasing an earlier node's
        contribution before a later node reads it -- exactly the hazard a
        naively-written `_verify_node` would have hit in `specialists/
        readme_presentation.py` (Wave 8 design, found by adversarial review)."""

        def node_a(state, config):
            return {"details": merge_details(state, from_a="a-value")}

        def node_b(state, config):
            assert state.details.get("from_a") == "a-value"
            return {"details": merge_details(state, from_b="b-value")}

        def node_c(state, config):
            assert state.details.get("from_a") == "a-value"
            assert state.details.get("from_b") == "b-value"
            return {"details": merge_details(state, from_c="c-value")}

        graph = StateGraph(DomainStateV1)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_node("c", node_c)
        graph.add_edge(START, "a")
        graph.add_edge("a", "b")
        graph.add_edge("b", "c")
        graph.add_edge("c", END)
        compiled = graph.compile()

        result = compiled.invoke(DomainStateV1(domain="test"))

        assert result["details"] == {
            "from_a": "a-value",
            "from_b": "b-value",
            "from_c": "c-value",
        }

    def test_regression_baseline_a_bare_dict_return_would_have_dropped_a_key(self):
        """Proves the *old* pattern (a bare `{"details": {...}}` return, with
        no spreading) really does silently drop an earlier node's
        contribution -- the exact hazard `merge_details()` exists to close,
        not a hypothetical."""

        def node_a(state, config):
            return {"details": {"from_a": "a-value"}}  # deliberately not using merge_details

        def node_b(state, config):
            return {"details": {"from_b": "b-value"}}  # deliberately not using merge_details

        graph = StateGraph(DomainStateV1)
        graph.add_node("a", node_a)
        graph.add_node("b", node_b)
        graph.add_edge(START, "a")
        graph.add_edge("a", "b")
        graph.add_edge("b", END)
        compiled = graph.compile()

        result = compiled.invoke(DomainStateV1(domain="test"))

        # This is the bug, demonstrated: node_a's own contribution is gone.
        assert "from_a" not in result["details"]
        assert result["details"] == {"from_b": "b-value"}


class TestFailureEscalation:
    def test_success_resets_to_zero(self):
        assert record_failure_or_reset(5, "some_reason", None) == (0, None)

    def test_first_failure_starts_at_one(self):
        assert record_failure_or_reset(0, None, "execution_error") == (1, "execution_error")

    def test_same_reason_as_last_time_increments(self):
        assert record_failure_or_reset(2, "execution_error", "execution_error") == (
            3,
            "execution_error",
        )

    def test_a_different_reason_restarts_the_count(self):
        assert record_failure_or_reset(5, "execution_error", "verification_rejected") == (
            1,
            "verification_rejected",
        )

    def test_missing_policy_profile_never_escalates_regardless_of_run_count(self):
        """The named, required carve-out: 22/25 real registry entries have no
        `policy_profile` configured, so `get_product_facts`-dependent domains
        `ERROR` for those repos every run, forever, by design -- a stable,
        expected, permanent condition, never a genuine alarm."""
        assert record_failure_or_reset(100, "missing_policy_profile", "missing_policy_profile") == (
            0,
            "missing_policy_profile",
        )

    def test_missing_policy_profile_carve_out_applies_even_as_the_first_failure(self):
        assert record_failure_or_reset(0, None, "missing_policy_profile") == (
            0,
            "missing_policy_profile",
        )

    def test_disabled_mode_never_escalates_regardless_of_run_count(self):
        """Found live (Wave 8e full-registry pass, 2026-07-21): `readme_
        presentation`'s own `require_permitted()` call raises a *different*
        message than `missing_policy_profile`'s ValueError for every one of
        the 22 `mode: "disabled"` registry entries -- confirmed live to reach
        `consecutive_failure_count: 2` (of the threshold-3 alert) across two
        real consecutive runs, one run away from a false alarm on all 22
        disabled entries at once. Same permanent, config-driven carve-out
        `missing_policy_profile` already gets."""
        assert record_failure_or_reset(100, "disabled_mode", "disabled_mode") == (
            0,
            "disabled_mode",
        )


class TestClassifyErrorReason:
    def test_extracts_the_outcome_class_from_the_error_prefixed_status(self):
        assert _classify_error_reason("ERROR:execution_error:boom") == "execution_error"

    def test_recognizes_a_missing_policy_profile_by_content_not_just_prefix(self):
        """The named carve-out must match regardless of which capability/
        domain produced the message -- content-based, not a literal string
        no real specialist ever actually emits verbatim."""
        assert (
            _classify_error_reason(
                "ERROR:execution_error:acme/widget has no policy_profile configured"
            )
            == "missing_policy_profile"
        )

    def test_recognizes_a_disabled_mode_registry_entry_by_content(self):
        """Found live, Wave 8e: `require_permitted()`'s real, exact message
        for a `mode: "disabled"` entry -- distinct wording from `missing_
        policy_profile`'s ValueError, so it needs its own content match."""
        assert (
            _classify_error_reason(
                "ERROR:execution_error:NotAllowlistedError: acme/widget is not in "
                "data/products.json with an enabled mode -- refusing to touch it. "
                "This is the hard allow-list gate."
            )
            == "disabled_mode"
        )


class TestMergeUnrecordedFailures:
    """`VER-005`: folds domains that never durably recorded themselves this
    run into `domain_states`, applying the same escalation bookkeeping
    `save_domain_with_failure_tracking()` does, but as a pure, no-I/O patch
    onto an already-loaded `RunStateV1` -- the caller (`supervisor/loop.py`)
    folds the result into whatever single save it's already about to make."""

    def test_empty_failures_returns_base_unchanged(self):
        """The healthy-run case: nothing to fold in, no new domain_states
        entries created, matching the cost-mitigation design's own "zero
        added cost on a fully healthy run" claim."""
        base = RunStateV1(org_repo="acme/widget")
        assert merge_unrecorded_failures(base, {}) == base

    def test_first_failure_for_a_never_recorded_domain_produces_an_entry(self):
        """The exact gap this fix closes: a domain that errors on its
        first-ever run for a repo, under the guard-and-skip pattern, would
        otherwise never appear in `domain_states` at all."""
        base = RunStateV1(org_repo="acme/widget")
        failures = {
            "metadata_presentation": DomainStateV1(
                domain="metadata_presentation",
                accepted_status="ERROR:execution_error:acme/widget has no policy_profile "
                "configured",
            )
        }
        updated = merge_unrecorded_failures(base, failures)
        stored = updated.domain_states["metadata_presentation"]
        assert stored.accepted_facts_hash is None
        assert stored.consecutive_failure_count == 0  # missing_policy_profile: non-escalating
        assert stored.last_failure_reason == "missing_policy_profile"

    def test_a_prior_good_baseline_survives_a_folded_in_failure_unchanged(self):
        base = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "package_release_audit": DomainStateV1(
                    domain="package_release_audit",
                    accepted_facts_hash="good-hash",
                    accepted_status="NO_CHANGE",
                    details={"releases_count": 3},
                )
            },
        )
        failures = {
            "package_release_audit": DomainStateV1(
                domain="package_release_audit", accepted_status="ERROR:execution_error:boom"
            )
        }
        updated = merge_unrecorded_failures(base, failures)
        stored = updated.domain_states["package_release_audit"]
        assert stored.accepted_facts_hash == "good-hash"
        assert stored.accepted_status == "NO_CHANGE"
        assert stored.details == {"releases_count": 3}
        assert stored.consecutive_failure_count == 1
        assert stored.last_failure_reason == "execution_error"

    def test_repeated_identical_failure_across_two_folds_increments(self):
        base = RunStateV1(org_repo="acme/widget")
        failure = {
            "community_files_presentation": DomainStateV1(
                domain="community_files_presentation",
                accepted_status="ERROR:execution_error:boom",
            )
        }
        once = merge_unrecorded_failures(base, failure)
        twice = merge_unrecorded_failures(once, failure)
        assert twice.domain_states["community_files_presentation"].consecutive_failure_count == 2

    def test_unrelated_domains_are_left_untouched(self):
        base = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation", accepted_status="NO_CHANGE"
                )
            },
        )
        failures = {
            "visual_preparation": DomainStateV1(
                domain="visual_preparation", accepted_status="ERROR:execution_error:boom"
            )
        }
        updated = merge_unrecorded_failures(base, failures)
        assert updated.domain_states["readme_reconciliation"].accepted_status == "NO_CHANGE"
        assert "visual_preparation" in updated.domain_states

    def test_a_non_error_result_replaces_the_entry_outright(self):
        """Mirrors save_domain_with_failure_tracking()'s own `is_error`
        branch: a non-`ERROR:`-prefixed result (e.g. a caller that folds in
        a genuinely successful result through this same helper) replaces
        the entry, not just patches escalation fields onto the prior one."""
        base = RunStateV1(org_repo="acme/widget")
        results = {
            "readme_reconciliation": DomainStateV1(
                domain="readme_reconciliation",
                accepted_facts_hash="new-hash",
                accepted_status="NO_CHANGE",
            )
        }
        updated = merge_unrecorded_failures(base, results)
        stored = updated.domain_states["readme_reconciliation"]
        assert stored.accepted_facts_hash == "new-hash"
        assert stored.consecutive_failure_count == 0
        assert stored.last_failure_reason is None


class _FakeBackendWithLock:
    def __init__(self):
        self._states: dict[str, RunStateV1] = {}

    def load(self, org_repo):
        return self._states.get(org_repo)

    def save(self, org_repo, state, expected_version):
        current = self._states.get(org_repo)
        current_version = current.state_version if current else None
        if expected_version != current_version:
            return SaveResult(outcome="stale", new_version=current_version)
        new_version = (current_version or 0) + 1
        self._states[org_repo] = state.model_copy(update={"state_version": new_version})
        return SaveResult(outcome="saved", new_version=new_version)

    def acquire_lock(self, org_repo):
        leased_until = (datetime.now(UTC) + timedelta(seconds=900)).isoformat()
        return Lock(org_repo=org_repo, holder_id="holder", leased_until=leased_until)

    def release_lock(self, lock):
        pass


class TestSaveDomainWithFailureTracking:
    """Wave 8d: unlike plain `save_domain()`, this persists a failure even
    when `accepted_status` is `"ERROR:"`-prefixed -- preserving the last-good
    baseline while still tracking how many times in a row it happened."""

    def test_first_failure_preserves_no_prior_baseline_and_counts_one(self):
        backend = _FakeBackendWithLock()
        save_domain_with_failure_tracking(
            backend,
            "acme/widget",
            "readme_presentation",
            DomainStateV1(
                domain="readme_presentation", accepted_status="ERROR:execution_error:boom"
            ),
        )

        stored = backend.load("acme/widget").domain_states["readme_presentation"]
        assert stored.accepted_facts_hash is None
        assert stored.consecutive_failure_count == 1
        assert stored.last_failure_reason == "execution_error"

    def test_a_prior_good_baseline_survives_a_failure_unchanged(self):
        backend = _FakeBackendWithLock()
        backend._states["acme/widget"] = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme_presentation": DomainStateV1(
                    domain="readme_presentation",
                    accepted_facts_hash="good-hash",
                    accepted_status="NO_CHANGE",
                    details={"written": True},
                )
            },
        )

        save_domain_with_failure_tracking(
            backend,
            "acme/widget",
            "readme_presentation",
            DomainStateV1(
                domain="readme_presentation", accepted_status="ERROR:execution_error:boom"
            ),
        )

        stored = backend.load("acme/widget").domain_states["readme_presentation"]
        assert stored.accepted_facts_hash == "good-hash"  # last-good baseline preserved
        assert stored.accepted_status == "NO_CHANGE"
        assert stored.details == {"written": True}
        assert stored.consecutive_failure_count == 1
        assert stored.last_failure_reason == "execution_error"

    def test_repeated_identical_failure_increments(self):
        backend = _FakeBackendWithLock()
        for _ in range(3):
            save_domain_with_failure_tracking(
                backend,
                "acme/widget",
                "readme_presentation",
                DomainStateV1(
                    domain="readme_presentation", accepted_status="ERROR:execution_error:boom"
                ),
            )

        stored = backend.load("acme/widget").domain_states["readme_presentation"]
        assert stored.consecutive_failure_count == 3

    def test_success_resets_and_persists_normally(self):
        backend = _FakeBackendWithLock()
        save_domain_with_failure_tracking(
            backend,
            "acme/widget",
            "readme_presentation",
            DomainStateV1(
                domain="readme_presentation", accepted_status="ERROR:execution_error:boom"
            ),
        )

        save_domain_with_failure_tracking(
            backend,
            "acme/widget",
            "readme_presentation",
            DomainStateV1(
                domain="readme_presentation",
                accepted_facts_hash="new-hash",
                accepted_status="NO_CHANGE",
                details={"written": True},
            ),
        )

        stored = backend.load("acme/widget").domain_states["readme_presentation"]
        assert stored.accepted_facts_hash == "new-hash"
        assert stored.consecutive_failure_count == 0
        assert stored.last_failure_reason is None


class TestSaveDomainRevisionStamping:
    """Wave 8.6 (`ORC-003` reversal prerequisite): `save_domain()` now
    stamps `upstream_revision_at_accept` at the actual persistence point,
    the one place that survives durable storage."""

    def test_current_revision_is_stamped_on_accept(self):
        backend = _FakeBackendWithLock()
        save_domain(
            backend,
            "acme/widget",
            "readme_reconciliation",
            DomainStateV1(domain="readme_reconciliation", accepted_status="NO_CHANGE"),
            current_revision="sha-new",
        )
        stored = backend.load("acme/widget").domain_states["readme_reconciliation"]
        assert stored.upstream_revision_at_accept == "sha-new"

    def test_omitting_current_revision_does_not_stamp_or_crash(self):
        """Every pre-Wave-8.6 call site omits this kwarg -- must be a no-op,
        not a crash or a forced None-overwrite of an existing value."""
        backend = _FakeBackendWithLock()
        save_domain(
            backend,
            "acme/widget",
            "readme_reconciliation",
            DomainStateV1(
                domain="readme_reconciliation",
                accepted_status="NO_CHANGE",
                upstream_revision_at_accept="sha-preexisting",
            ),
        )
        stored = backend.load("acme/widget").domain_states["readme_reconciliation"]
        assert stored.upstream_revision_at_accept == "sha-preexisting"

    def test_a_real_accept_resets_a_prior_skip_streak(self):
        backend = _FakeBackendWithLock()
        save_domain(
            backend,
            "acme/widget",
            "visual_preparation",
            DomainStateV1(
                domain="visual_preparation",
                accepted_status="NO_CHANGE",
                skipped_this_run=True,
                consecutive_skip_count=2,
            ),
            current_revision="sha-new",
        )
        stored = backend.load("acme/widget").domain_states["visual_preparation"]
        assert stored.skipped_this_run is False
        assert stored.consecutive_skip_count == 0


class TestDomainCoverageComplete:
    """Wave 8.6 (`ORC-003` reversal prerequisite): revision-aware, replacing
    the former presence-only check (`set(all_domains()) <= set(domain_
    states.keys())`), which could not tell a domain recomputed against the
    CURRENT upstream revision apart from a stale record left over from a run
    several revisions ago."""

    def test_absent_domain_is_not_covered(self):
        assert is_domain_covered(None, "sha-1") is False

    def test_stale_revision_with_present_key_is_not_covered(self):
        """The exact hole the old presence-only check had: the key exists,
        but it was accepted against a DIFFERENT revision than the current
        one."""
        state = DomainStateV1(
            domain="readme_reconciliation",
            accepted_status="NO_CHANGE",
            upstream_revision_at_accept="sha-old",
        )
        assert is_domain_covered(state, "sha-new") is False

    def test_matching_revision_is_covered(self):
        state = DomainStateV1(
            domain="readme_reconciliation",
            accepted_status="NO_CHANGE",
            upstream_revision_at_accept="sha-1",
        )
        assert is_domain_covered(state, "sha-1") is True

    def test_a_permanent_non_escalating_failure_is_always_covered(self):
        """Without this carve-out, 22/25 real registry entries (disabled-
        mode / no-policy-profile repos) would never satisfy a naive revision
        match for the domains that permanently error for them, permanently
        defeating is_fresh()'s coarse shortcut."""
        state = DomainStateV1(
            domain="metadata_presentation",
            accepted_status="ERROR:missing_policy_profile:no policy_profile configured",
            last_failure_reason="missing_policy_profile",
            upstream_revision_at_accept=None,
        )
        assert is_domain_covered(state, "sha-new") is True

    def test_a_genuine_unexplained_failure_is_not_covered(self):
        state = DomainStateV1(
            domain="metadata_presentation",
            accepted_status="ERROR:execution_error:boom",
            last_failure_reason="execution_error",
            upstream_revision_at_accept=None,
        )
        assert is_domain_covered(state, "sha-new") is False

    def test_a_skip_recorded_against_the_current_revision_is_covered(self):
        state = DomainStateV1(
            domain="visual_preparation",
            accepted_status="NO_CHANGE",
            skipped_this_run=True,
            details={"skipped_at_revision": "sha-new"},
        )
        assert is_domain_covered(state, "sha-new") is True

    def test_a_skip_recorded_against_a_now_stale_revision_is_not_covered(self):
        state = DomainStateV1(
            domain="visual_preparation",
            accepted_status="NO_CHANGE",
            skipped_this_run=True,
            details={"skipped_at_revision": "sha-old"},
        )
        assert is_domain_covered(state, "sha-new") is False

    def test_compute_domain_coverage_complete_requires_every_domain_covered(self):
        base = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="NO_CHANGE",
                    upstream_revision_at_accept="sha-1",
                ),
                "visual_preparation": DomainStateV1(
                    domain="visual_preparation",
                    accepted_status="NO_CHANGE",
                    upstream_revision_at_accept="sha-OLD",
                ),
            },
        )
        assert (
            compute_domain_coverage_complete(
                base, ["readme_reconciliation", "visual_preparation"], "sha-1"
            )
            is False
        )

    def test_compute_domain_coverage_complete_true_when_all_domains_covered(self):
        base = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme_reconciliation": DomainStateV1(
                    domain="readme_reconciliation",
                    accepted_status="NO_CHANGE",
                    upstream_revision_at_accept="sha-1",
                ),
            },
        )
        assert compute_domain_coverage_complete(base, ["readme_reconciliation"], "sha-1") is True


class TestMarkDomainSkipped:
    def test_first_skip_records_streak_of_one_and_leaves_baseline_untouched(self):
        backend = _FakeBackendWithLock()
        backend._states["acme/widget"] = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "visual_preparation": DomainStateV1(
                    domain="visual_preparation",
                    accepted_facts_hash="good-hash",
                    accepted_status="NO_CHANGE",
                    upstream_revision_at_accept="sha-1",
                )
            },
        )
        mark_domain_skipped(
            backend,
            "acme/widget",
            "visual_preparation",
            "sha-2",
            skip_reason="diff_shows_no_relevant_change",
            max_consecutive_skips=3,
        )
        stored = backend.load("acme/widget").domain_states["visual_preparation"]
        assert stored.skipped_this_run is True
        assert stored.consecutive_skip_count == 1
        assert stored.details["skipped_at_revision"] == "sha-2"
        assert stored.details["skip_reason"] == "diff_shows_no_relevant_change"
        # The accepted baseline itself is untouched -- nothing was reclassified.
        assert stored.accepted_facts_hash == "good-hash"
        assert stored.accepted_status == "NO_CHANGE"
        assert stored.upstream_revision_at_accept == "sha-1"

    def test_repeated_skips_increment_the_streak(self):
        backend = _FakeBackendWithLock()
        for revision in ("sha-2", "sha-3"):
            mark_domain_skipped(
                backend,
                "acme/widget",
                "visual_preparation",
                revision,
                skip_reason="diff_shows_no_relevant_change",
                max_consecutive_skips=3,
            )
        stored = backend.load("acme/widget").domain_states["visual_preparation"]
        assert stored.consecutive_skip_count == 2

    def test_refuses_to_skip_past_the_max_consecutive_boundary(self):
        """Last line of defense -- `specialist_selection.py::decide_skips()`
        already checks this before ever offering the domain to the LLM as
        skippable; this raise is for a caller that somehow reaches here
        anyway, a real bug worth surfacing loudly."""
        backend = _FakeBackendWithLock()
        backend._states["acme/widget"] = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "visual_preparation": DomainStateV1(
                    domain="visual_preparation", consecutive_skip_count=3
                )
            },
        )
        with pytest.raises(StateBackendError):
            mark_domain_skipped(
                backend,
                "acme/widget",
                "visual_preparation",
                "sha-2",
                skip_reason="diff_shows_no_relevant_change",
                max_consecutive_skips=3,
            )
