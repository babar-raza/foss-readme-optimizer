"""Wave 8.6 (`ORC-003` reversal): `supervisor/specialist_selection.py`'s
deterministic diff+boundary gate and the LLM skip-decision call it wraps.
The central property under test: the LLM can only ever narrow the skip set
a deterministic check already cleared, never expand it, and any failure
mode (no client, LLM error, malformed response, off-menu claim) fails
closed to "skip nothing"."""

import json

from readme_agent.capabilities import domains
from readme_agent.errors import LLMError
from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor import specialist_selection


def _tool_call(skip_domains: list[str]) -> dict:
    return {
        "id": "call-1",
        "function": {
            "name": "select_specialists_to_skip",
            "arguments": json.dumps({"skip_domains": skip_domains}),
        },
    }


class TestCandidateDomainsInvariant:
    def test_never_candidates_are_excluded_by_construction(self):
        never_candidates = {
            domains.GITHUB_GENERATED_SURFACE_AUDIT,
            domains.PACKAGE_RELEASE_AUDIT,
            domains.METADATA_PRESENTATION,
            domains.CROSS_SURFACE_VALIDATION,
            domains.INDEPENDENT_VERIFICATION,
        }
        assert not (set(specialist_selection.CANDIDATE_DOMAINS) & never_candidates)


class TestDecideSkipsForcedRunBoundaries:
    def test_domain_at_max_consecutive_skips_is_forced_never_offered(self, tmp_path, monkeypatch):
        def _must_not_be_called(*args, **kwargs):
            raise AssertionError("diff_changed_paths should never be called for this domain")

        monkeypatch.setattr(specialist_selection, "diff_changed_paths", _must_not_be_called)
        prior = {
            domains.VISUAL_PREPARATION: DomainStateV1(
                domain=domains.VISUAL_PREPARATION,
                upstream_revision_at_accept="sha-1",
                consecutive_skip_count=specialist_selection.MAX_CONSECUTIVE_SKIPS,
            )
        }
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=prior,
            current_revision="sha-2",
            specialist_selection_client=None,
        )
        assert domains.VISUAL_PREPARATION not in plan.skip_domains
        assert (
            plan.forced_run_domains[domains.VISUAL_PREPARATION] == "max_consecutive_skips_reached"
        )

    def test_no_prior_accept_is_forced_run(self, tmp_path):
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states={},
            current_revision="sha-1",
            specialist_selection_client=None,
        )
        for domain in specialist_selection.CANDIDATE_DOMAINS:
            assert plan.forced_run_domains[domain] == "no_prior_accept"
        assert plan.skip_domains == frozenset()

    def test_undeterminable_diff_is_forced_run_fail_closed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: None)
        prior = {
            domain: DomainStateV1(domain=domain, upstream_revision_at_accept="sha-1")
            for domain in specialist_selection.CANDIDATE_DOMAINS
        }
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=prior,
            current_revision="sha-2",
            specialist_selection_client=None,
        )
        for domain in specialist_selection.CANDIDATE_DOMAINS:
            assert plan.forced_run_domains[domain] == "diff_undeterminable"

    def test_diff_showing_a_relevant_path_change_is_forced_run(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            specialist_selection, "diff_changed_paths", lambda *a, **k: ["README.md"]
        )
        prior = {
            domains.README_RECONCILIATION: DomainStateV1(
                domain=domains.README_RECONCILIATION, upstream_revision_at_accept="sha-1"
            )
        }
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=prior,
            current_revision="sha-2",
            specialist_selection_client=None,
        )
        assert plan.forced_run_domains[domains.README_RECONCILIATION] == (
            "diff_shows_relevant_change"
        )

    def test_unrelated_path_change_still_makes_the_domain_eligible(self, tmp_path, monkeypatch):
        """A changed path that matches no candidate domain's own signal
        (e.g. an unrelated source file) must not force any domain to run --
        it should reach the LLM-offering stage."""
        monkeypatch.setattr(
            specialist_selection, "diff_changed_paths", lambda *a, **k: ["src/unrelated.py"]
        )
        prior = {
            domains.README_RECONCILIATION: DomainStateV1(
                domain=domains.README_RECONCILIATION, upstream_revision_at_accept="sha-1"
            )
        }
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=prior,
            current_revision="sha-2",
            specialist_selection_client=None,
        )
        # No client configured -- eligible, but nothing is actually skipped.
        assert domains.README_RECONCILIATION not in plan.forced_run_domains
        assert plan.skip_domains == frozenset()


class TestDecideSkipsLLMDecision:
    def _eligible_prior(self, domain: str) -> dict:
        return {domain: DomainStateV1(domain=domain, upstream_revision_at_accept="sha-1")}

    def test_no_client_configured_skips_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=self._eligible_prior(domains.VISUAL_PREPARATION),
            current_revision="sha-2",
            specialist_selection_client=None,
        )
        assert plan.skip_domains == frozenset()

    def test_llm_selected_skip_is_accepted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call=_tool_call([domains.VISUAL_PREPARATION]), meta=LLMResponseMeta()
                )
            ]
        )
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=self._eligible_prior(domains.VISUAL_PREPARATION),
            current_revision="sha-2",
            specialist_selection_client=client,
        )
        assert plan.skip_domains == frozenset({domains.VISUAL_PREPARATION})
        assert plan.reasons[domains.VISUAL_PREPARATION] == "llm_selected"

    def test_off_menu_claim_is_filtered_out_never_trusted_raw(self, tmp_path, monkeypatch):
        """The final enforcement boundary: even if the model somehow claims
        a domain outside `eligible` (a malformed response bypassing the tool
        schema's own enum), it must never be honored."""
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call=_tool_call(
                        [domains.VISUAL_PREPARATION, domains.GITHUB_GENERATED_SURFACE_AUDIT]
                    ),
                    meta=LLMResponseMeta(),
                )
            ]
        )
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=self._eligible_prior(domains.VISUAL_PREPARATION),
            current_revision="sha-2",
            specialist_selection_client=client,
        )
        assert plan.skip_domains == frozenset({domains.VISUAL_PREPARATION})
        assert domains.GITHUB_GENERATED_SURFACE_AUDIT not in plan.skip_domains

    def test_llm_error_fails_closed_to_no_skips(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])

        class _RaisingClient:
            def plan(self, messages, tools):
                raise LLMError("gateway unreachable")

        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=self._eligible_prior(domains.VISUAL_PREPARATION),
            current_revision="sha-2",
            specialist_selection_client=_RaisingClient(),
        )
        assert plan.skip_domains == frozenset()

    def test_stop_signal_no_tool_call_skips_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=None, content="nothing to skip", meta=LLMResponseMeta())]
        )
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=self._eligible_prior(domains.VISUAL_PREPARATION),
            current_revision="sha-2",
            specialist_selection_client=client,
        )
        assert plan.skip_domains == frozenset()

    def test_malformed_arguments_json_fails_closed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call={
                        "id": "call-1",
                        "function": {
                            "name": "select_specialists_to_skip",
                            "arguments": "{not valid json",
                        },
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states=self._eligible_prior(domains.VISUAL_PREPARATION),
            current_revision="sha-2",
            specialist_selection_client=client,
        )
        assert plan.skip_domains == frozenset()


class TestRealPromptRegistryIntegration:
    """Confirms the real, shipped `specialist_selection_turn` prompt manifest
    is well-formed enough for `decide_skips()` to actually use -- not just a
    mocked/fixture prompt."""

    def test_prompt_is_registered_and_has_a_user_template(self):
        from readme_agent.llm import prompt_registry

        manifest = prompt_registry.get("specialist_selection_turn")
        assert manifest is not None
        assert manifest.user_template is not None
        assert manifest.category == "planning"

    def test_real_prompt_drives_a_real_skip_decision(self, tmp_path, monkeypatch):
        monkeypatch.setattr(specialist_selection, "diff_changed_paths", lambda *a, **k: [])
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call=_tool_call([domains.VISUAL_PREPARATION]), meta=LLMResponseMeta()
                )
            ]
        )
        plan = specialist_selection.decide_skips(
            org_repo="acme/widget",
            baseline_path=tmp_path,
            prior_domain_states={
                domains.VISUAL_PREPARATION: DomainStateV1(
                    domain=domains.VISUAL_PREPARATION, upstream_revision_at_accept="sha-1"
                )
            },
            current_revision="sha-2",
            specialist_selection_client=client,
        )
        assert plan.skip_domains == frozenset({domains.VISUAL_PREPARATION})


class TestPathMatching:
    """`_path_matches_domain()`'s root-level matching, exercised indirectly
    through `_domain_diff_signal()` since it's the actual decision point."""

    def test_readme_change_matches_readme_domains(self):
        assert specialist_selection._domain_diff_signal(
            domains.README_RECONCILIATION, ["README.md"]
        )
        assert specialist_selection._domain_diff_signal(domains.README_PRESENTATION, ["readme.rst"])

    def test_nested_readme_like_path_does_not_match_root_only_lookup(self):
        assert not specialist_selection._domain_diff_signal(
            domains.README_RECONCILIATION, ["docs/README.md"]
        )

    def test_license_change_matches_community_files_domain(self):
        assert specialist_selection._domain_diff_signal(
            domains.COMMUNITY_FILES_PRESENTATION, ["LICENSE"]
        )

    def test_image_asset_in_a_search_dir_matches_visual_preparation(self):
        assert specialist_selection._domain_diff_signal(
            domains.VISUAL_PREPARATION, ["docs/banner.png"]
        )

    def test_unrelated_source_file_matches_nothing(self):
        for domain in specialist_selection.CANDIDATE_DOMAINS:
            assert not specialist_selection._domain_diff_signal(domain, ["src/unrelated.py"])
