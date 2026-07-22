"""Wave 8.6 (`OPS-011`): the golden-set scenario corpus, harness scoring
logic, and durable-metric aggregation."""

import pytest

from readme_agent.errors import LLMError
from readme_agent.golden_set import aggregation, harness
from readme_agent.golden_set.scenarios import SCENARIOS, GoldenScenario
from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta, Usage
from readme_agent.state.schema import RunStateV1, SupervisorStateV1


def _tool_call(capability_id: str) -> dict:
    return {"id": "call-1", "function": {"name": capability_id, "arguments": "{}"}}


class TestScenarioCorpus:
    def test_every_scenario_sets_exactly_one_of_expected_or_forbidden(self):
        # __post_init__ already enforces this at construction time -- this
        # test proves the real, shipped corpus actually satisfies it.
        assert len(SCENARIOS) >= 5

    def test_scenario_ids_are_unique(self):
        ids = [s.scenario_id for s in SCENARIOS]
        assert len(ids) == len(set(ids))

    def test_both_fields_set_raises(self):
        with pytest.raises(ValueError, match="exactly one"):
            GoldenScenario(
                scenario_id="bad",
                category="x",
                description="x",
                dossier={},
                expected_capability_id="a",
                forbidden_capability_id="b",
            )

    def test_neither_field_set_raises(self):
        with pytest.raises(ValueError, match="exactly one"):
            GoldenScenario(scenario_id="bad", category="x", description="x", dossier={})

    def test_all_five_named_categories_are_represented(self):
        categories = {s.category for s in SCENARIOS}
        assert categories == {
            "correct_capability_selection",
            "irrelevant_capability_rejection",
            "stop_decision_accuracy",
            "malformed_argument_handling",
            "prompt_injection_resistance",
        }


class TestRunGoldenSet:
    def test_matching_expected_capability_passes(self):
        scenario = GoldenScenario(
            scenario_id="s1",
            category="correct_capability_selection",
            description="d",
            dossier={"readme_reconciliation": "UPSTREAM_CHANGED"},
            expected_capability_id="detect_readme_gaps",
        )
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=_tool_call("detect_readme_gaps"), meta=LLMResponseMeta())]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].passed is True
        assert results[0].actual_capability_id == "detect_readme_gaps"

    def test_mismatched_expected_capability_fails(self):
        scenario = GoldenScenario(
            scenario_id="s2",
            category="correct_capability_selection",
            description="d",
            dossier={},
            expected_capability_id="detect_readme_gaps",
        )
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=_tool_call("inspect_repository"), meta=LLMResponseMeta())]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].passed is False

    def test_expecting_stop_and_getting_stop_passes(self):
        scenario = GoldenScenario(
            scenario_id="s3",
            category="stop_decision_accuracy",
            description="d",
            dossier={},
            expected_capability_id="STOP",
        )
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=None, content="done", meta=LLMResponseMeta())]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].passed is True
        assert results[0].actual_capability_id is None

    def test_forbidden_capability_called_fails(self):
        scenario = GoldenScenario(
            scenario_id="s4",
            category="prompt_injection_resistance",
            description="d",
            dossier={},
            forbidden_capability_id="commit_readme_write",
        )
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=_tool_call("commit_readme_write"), meta=LLMResponseMeta())]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].passed is False

    def test_forbidden_capability_not_called_passes(self):
        scenario = GoldenScenario(
            scenario_id="s5",
            category="prompt_injection_resistance",
            description="d",
            dossier={},
            forbidden_capability_id="commit_readme_write",
        )
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=_tool_call("detect_readme_gaps"), meta=LLMResponseMeta())]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].passed is True

    def test_malformed_arguments_do_not_crash_the_harness(self):
        """Scoring is by capability NAME only -- malformed JSON in the
        arguments string must never crash the harness."""
        scenario = GoldenScenario(
            scenario_id="s6",
            category="malformed_argument_handling",
            description="d",
            dossier={},
            expected_capability_id="detect_readme_gaps",
        )
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call={
                        "id": "call-1",
                        "function": {"name": "detect_readme_gaps", "arguments": "{not valid json"},
                    },
                    meta=LLMResponseMeta(),
                )
            ]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].passed is True

    def test_planner_llm_error_is_recorded_as_a_failure_not_a_crash(self):
        scenario = GoldenScenario(
            scenario_id="s7",
            category="correct_capability_selection",
            description="d",
            dossier={},
            expected_capability_id="detect_readme_gaps",
        )

        class _RaisingClient:
            def plan(self, messages, tools):
                raise LLMError("gateway unreachable")

        results = harness.run_golden_set(_RaisingClient(), scenarios=(scenario,))
        assert results[0].passed is False
        assert "planner call failed" in results[0].detail

    def test_never_dispatches_anything(self, monkeypatch):
        """The structural non-mutation guarantee: run_golden_set must never
        call dispatch_tool_call, regardless of what the model picks."""
        from readme_agent.capabilities import dispatcher

        def _must_not_be_called(*args, **kwargs):
            raise AssertionError("run_golden_set must never dispatch anything")

        monkeypatch.setattr(dispatcher, "dispatch_tool_call", _must_not_be_called)
        scenario = GoldenScenario(
            scenario_id="s8",
            category="correct_capability_selection",
            description="d",
            dossier={},
            expected_capability_id="commit_readme_write",
        )
        client = FixturePlannerClient(
            [PlannerTurn(tool_call=_tool_call("commit_readme_write"), meta=LLMResponseMeta())]
        )
        harness.run_golden_set(client, scenarios=(scenario,))  # must not raise

    def test_prompt_tokens_are_captured_when_present(self):
        scenario = GoldenScenario(
            scenario_id="s9",
            category="correct_capability_selection",
            description="d",
            dossier={},
            expected_capability_id="detect_readme_gaps",
        )
        client = FixturePlannerClient(
            [
                PlannerTurn(
                    tool_call=_tool_call("detect_readme_gaps"),
                    meta=LLMResponseMeta(usage=Usage(prompt_tokens=123, completion_tokens=4)),
                )
            ]
        )
        results = harness.run_golden_set(client, scenarios=(scenario,))
        assert results[0].prompt_tokens == 123


class TestSummarize:
    def test_computes_pass_rate_and_per_category_breakdown(self):
        results = [
            harness.ScenarioResult("a", "cat1", True, "x", "ok"),
            harness.ScenarioResult("b", "cat1", False, "y", "no"),
            harness.ScenarioResult("c", "cat2", True, "z", "ok"),
        ]
        summary = harness.summarize(results)
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["pass_rate"] == pytest.approx(2 / 3)
        assert summary["by_category"]["cat1"] == {"total": 2, "passed": 1}
        assert summary["by_category"]["cat2"] == {"total": 1, "passed": 1}

    def test_empty_results_reports_none_pass_rate_not_a_crash(self):
        summary = harness.summarize([])
        assert summary["total"] == 0
        assert summary["pass_rate"] is None


class _FakeStateBackend:
    def __init__(self, states: dict[str, RunStateV1]):
        self._states = states

    def load(self, org_repo):
        return self._states.get(org_repo)


class TestAggregateProductionMetrics:
    def test_counts_capability_gaps_and_repair_history_across_the_portfolio(self):
        backend = _FakeStateBackend(
            {
                "acme/a": RunStateV1(
                    org_repo="acme/a",
                    supervisor_state=SupervisorStateV1(
                        capability_gaps=[{"gap_id": "1"}],
                        repair_history=[
                            {"kind": "repair_alternative_selected"},
                            {"kind": "repair_escalated"},
                        ],
                    ),
                ),
                "acme/b": RunStateV1(
                    org_repo="acme/b",
                    supervisor_state=SupervisorStateV1(
                        capability_gaps=[], repair_history=[{"kind": "repair"}]
                    ),
                ),
            }
        )

        result = aggregation.aggregate_production_metrics(backend, ["acme/a", "acme/b"])

        assert result["repos_with_state"] == 2
        assert result["hallucinated_capability_count"] == 1
        assert result["repair_attempts"] == 3
        assert result["repair_alternatives_selected"] == 1
        assert result["repair_escalated"] == 1

    def test_missing_state_is_skipped_not_crashed_on(self):
        backend = _FakeStateBackend({})
        result = aggregation.aggregate_production_metrics(backend, ["acme/never-run"])
        assert result["repos_with_state"] == 0
