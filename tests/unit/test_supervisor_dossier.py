"""Offline tests for the bounded, uniformly-summarized planner dossier
(AGT-008, Wave 8.5) -- supervisor/dossier.py."""

import json

from readme_agent.llm.prompt_schema import PromptManifest
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor import dossier


class TestSummarizeDomain:
    def test_none_state_returns_not_yet_run(self):
        assert dossier.summarize_domain("readme_reconciliation", None) == "not yet run"

    def test_empty_details_falls_back_to_accepted_status(self):
        state = DomainStateV1(domain="x", accepted_status="NO_CHANGE", details={})
        assert dossier.summarize_domain("x", state) == "NO_CHANGE"

    def test_non_empty_details_produces_a_bounded_json_summary(self):
        state = DomainStateV1(domain="x", accepted_status="CHANGED", details={"a": 1, "b": "value"})
        summary = dossier.summarize_domain("x", state)
        assert len(summary) <= dossier.MAX_SUMMARY_CHARS
        parsed = json.loads(summary)
        assert parsed == {"a": 1, "b": "value"}

    def test_summary_is_truncated_when_details_are_large(self):
        state = DomainStateV1(domain="x", accepted_status="CHANGED", details={"big": "x" * 1000})
        summary = dossier.summarize_domain("x", state)
        assert len(summary) == dossier.MAX_SUMMARY_CHARS

    def test_optional_specialist_override_takes_precedence(self):
        state = DomainStateV1(
            domain="x",
            accepted_status="CHANGED",
            details={"_planner_summary": "a hand-written summary", "raw": "lots of other stuff"},
        )
        assert dossier.summarize_domain("x", state) == "a hand-written summary"

    def test_is_a_pure_function_same_input_same_output(self):
        state = DomainStateV1(domain="x", accepted_status="CHANGED", details={"a": 1})
        assert dossier.summarize_domain("x", state) == dossier.summarize_domain("x", state)


class TestBuildInitialDossier:
    def test_applies_uniformly_to_every_domain(self):
        results = {
            "domain_a": DomainStateV1(domain="domain_a", accepted_status="NO_CHANGE", details={}),
            "domain_b": DomainStateV1(
                domain="domain_b", accepted_status="CHANGED", details={"k": "v"}
            ),
        }
        built = dossier.build_initial_dossier(results)
        assert set(built) == {"domain_a", "domain_b"}
        assert built["domain_a"] == "NO_CHANGE"
        assert json.loads(built["domain_b"]) == {"k": "v"}

    def test_iteration_order_does_not_affect_individual_summaries(self):
        results = {
            "domain_a": DomainStateV1(domain="domain_a", accepted_status="NO_CHANGE", details={}),
            "domain_b": DomainStateV1(domain="domain_b", accepted_status="NO_CHANGE", details={}),
        }
        forward = dossier.build_initial_dossier(results)
        backward = dossier.build_initial_dossier(dict(reversed(list(results.items()))))
        assert forward == backward


class TestRenderTurnContext:
    def _manifest(self) -> PromptManifest:
        return PromptManifest(
            prompt_id="supervisor_turn",
            category="planning",
            version="1",
            model_route="supervisor_planning",
            system="system prompt",
            turn_context_template=(
                "Repo: $org_repo turn $turn_number/$max_turns tried=$tried_capabilities "
                "bootstrap=$bootstrap_result dossier=$specialist_summaries"
            ),
        )

    def test_substitutes_all_fields(self):
        rendered = dossier.render_turn_context(
            self._manifest(),
            org_repo="acme/widget",
            turn_number=2,
            max_turns=8,
            tried_capability_ids=["detect_readme_gaps"],
            bootstrap_result={"has_readme": True},
            dossier={"domain_a": "NO_CHANGE"},
        )
        assert "acme/widget" in rendered
        assert "turn 2/8" in rendered
        assert "detect_readme_gaps" in rendered
        assert "has_readme" in rendered
        assert "domain_a" in rendered

    def test_no_tried_capabilities_yet_renders_none_yet(self):
        rendered = dossier.render_turn_context(
            self._manifest(),
            org_repo="acme/widget",
            turn_number=1,
            max_turns=8,
            tried_capability_ids=[],
            bootstrap_result={},
            dossier={},
        )
        assert "none yet" in rendered
