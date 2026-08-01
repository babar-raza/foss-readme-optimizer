"""Offline tests for the bounded, uniformly-summarized planner dossier
(AGT-008, Wave 8.5) -- supervisor/dossier.py."""

import json
from hashlib import sha256

from readme_agent.errors import LLMError
from readme_agent.llm.planner_client import PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.state.schema import DomainStateV1
from readme_agent.supervisor import dossier, planner_loop


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


class TestBoundedCapabilityResult:
    def test_small_result_is_preserved_verbatim(self):
        result = {"status": "ready", "count": 2}

        assert dossier.bounded_capability_result("inspect_repository", result) is result

    def test_large_result_becomes_a_content_addressed_decision_receipt(self):
        result = {
            "status": "ready",
            "source_revision": "a" * 40,
            "candidate": {"candidate_hash": "b" * 64, "body": "x" * 50_000},
        }
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)

        bounded = dossier.bounded_capability_result("render_readme_candidate", result)

        assert isinstance(bounded, dict)
        assert bounded["payload_omitted"] is True
        assert bounded["result_sha256"] == sha256(canonical.encode()).hexdigest()
        assert bounded["decision_fields"] == {
            "candidate.candidate_hash": "b" * 64,
            "source_revision": "a" * 40,
            "status": "ready",
        }
        assert "x" * 1_000 not in json.dumps(bounded)


def test_planner_history_uses_bounded_capability_receipts(monkeypatch):
    huge_result = {
        "status": "ready",
        "candidate_hash": "b" * 64,
        "candidate": "x" * 100_000,
    }

    def fake_dispatch(graph, task, **_kwargs):
        return graph.mark(task.task_id, "PASSED", result=huge_result)

    class CaptureThenFailPlanner:
        def __init__(self):
            self.messages: list[list[dict]] = []
            self.tool_names: list[list[str]] = []

        def plan(self, messages, tools):
            self.messages.append(json.loads(json.dumps(messages)))
            self.tool_names.append([(tool.get("function") or {}).get("name") for tool in tools])
            if len(self.messages) == 1:
                return PlannerTurn(
                    tool_call={
                        "id": "call-1",
                        "function": {
                            "name": "detect_readme_gaps",
                            "arguments": '{"org_repo":"example/repo"}',
                        },
                    },
                    meta=LLMResponseMeta(),
                )
            raise LLMError("test stop after history capture")

    client = CaptureThenFailPlanner()
    monkeypatch.setattr(planner_loop, "dispatch_and_record", fake_dispatch)

    planner_loop.run_planner_loop(
        org_repo="example/repo",
        specialist_results={
            "readme_presentation": DomainStateV1(
                domain="readme_presentation",
                accepted_status="CHANGED",
                details={"render_status": "STALE_NONCOMPLIANT"},
            )
        },
        initial_decisions=[],
        state_backend=None,
        planner_client=client,
        repair_planner_client=None,
        allowed_permission_classes=None,
        max_turns=8,
        no_progress_turn_limit=3,
        dossier_token_budget=25_000,
    )

    assert len(client.messages) == 2
    assert set(client.tool_names[0]) == {
        "detect_readme_gaps",
        "get_product_facts",
        "render_readme_candidate",
        "verify_package_acquisition",
    }
    assert "detect_readme_gaps" not in client.tool_names[1]
    assert "inspect_repository" not in client.tool_names[0]
    assert "get_domain_findings" not in client.tool_names[0]
    assert len(json.dumps(client.messages[0])) < 10_000
    second_messages = json.dumps(client.messages[1])
    assert len(second_messages) < 15_000
    assert "x" * 1_000 not in second_messages
    tool_receipt = json.loads(client.messages[1][-1]["content"])
    assert tool_receipt["result"]["payload_omitted"] is True


class TestRenderTurnContext:
    def _template(self) -> str:
        return (
            "Repo: $org_repo turn $turn_number/$max_turns tried=$tried_capabilities "
            "eligible=$eligible_capabilities "
            "bootstrap=$bootstrap_result dossier=$specialist_summaries"
        )

    def test_substitutes_all_fields(self):
        rendered = dossier.render_turn_context(
            self._template(),
            org_repo="acme/widget",
            turn_number=2,
            max_turns=8,
            tried_capability_ids=["detect_readme_gaps"],
            eligible_capability_ids=("render_readme_candidate",),
            bootstrap_result={"has_readme": True},
            dossier={"domain_a": "NO_CHANGE"},
        )
        assert "acme/widget" in rendered
        assert "turn 2/8" in rendered
        assert "detect_readme_gaps" in rendered
        assert "render_readme_candidate" in rendered
        assert "has_readme" in rendered
        assert "domain_a" in rendered

    def test_no_tried_capabilities_yet_renders_none_yet(self):
        rendered = dossier.render_turn_context(
            self._template(),
            org_repo="acme/widget",
            turn_number=1,
            max_turns=8,
            tried_capability_ids=[],
            eligible_capability_ids=(),
            bootstrap_result={},
            dossier={},
        )
        assert "none yet" in rendered
        assert "stop only" in rendered
