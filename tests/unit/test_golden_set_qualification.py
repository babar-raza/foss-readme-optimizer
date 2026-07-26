"""Qualification corpus and three-session acceptance tests."""

from __future__ import annotations

import json

from readme_agent.golden_set import qualification, review_harness
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, specific_candidate
from readme_agent.golden_set.review_scenarios import REVIEW_SCENARIOS
from readme_agent.golden_set.scenarios import SCENARIOS, STOP
from readme_agent.llm.analysis_client import (
    AnalysisResult,
    FixtureAnalysisClient,
)
from readme_agent.llm.planner_client import FixturePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta


def _tool_call(capability_id: str) -> dict:
    return {"id": "golden", "function": {"name": capability_id, "arguments": "{}"}}


def _passing_planner_client() -> FixturePlannerClient:
    turns: list[PlannerTurn] = []
    for scenario in SCENARIOS:
        if scenario.expected_capability_id == STOP:
            turns.append(PlannerTurn(tool_call=None, content="complete", meta=LLMResponseMeta()))
        elif scenario.expected_capability_id is not None:
            turns.append(
                PlannerTurn(
                    tool_call=_tool_call(scenario.expected_capability_id),
                    meta=LLMResponseMeta(),
                )
            )
        else:
            turns.append(
                PlannerTurn(
                    tool_call=_tool_call("inspect_repository"),
                    meta=LLMResponseMeta(),
                )
            )
    return FixturePlannerClient(turns)


def _verdict_payload(verdict: str) -> dict:
    if verdict == "ACCEPT":
        return {
            "verdict": verdict,
            "reasoning": "The candidate is specific and every claim is grounded.",
            "failed_criteria": [],
            "sections_affected": [],
            "required_repair": "",
            "preserve": [],
        }
    failed = ["factuality"] if verdict.startswith("BLOCKED_") else ["product specificity"]
    return {
        "verdict": verdict,
        "reasoning": "The candidate reaches the expected controlled failure boundary.",
        "failed_criteria": failed,
        "sections_affected": ["opening"],
        "required_repair": "Repair the controlled defect.",
        "preserve": [],
    }


def _passing_review_client() -> FixtureAnalysisClient:
    return FixtureAnalysisClient(
        [
            AnalysisResult(
                parsed=_verdict_payload(scenario.expected_verdict),
                meta=LLMResponseMeta(),
            )
            for scenario in REVIEW_SCENARIOS
        ]
    )


def _deterministic(*, passed: int = 42, total: int = 42):
    return qualification.DeterministicQualificationResult(
        total=total,
        passed=passed,
        evidence_refs=["tests/unit/test_golden_set_qualification.py"],
    )


def test_review_corpus_covers_every_required_ecosystem_and_control():
    assert len(REVIEW_SCENARIOS) == 36
    assert {scenario.ecosystem for scenario in REVIEW_SCENARIOS} == {
        "java",
        "dotnet",
        "python",
        "typescript",
        "cpp",
        "go",
        "rust",
    }
    categories = {scenario.category for scenario in REVIEW_SCENARIOS}
    assert {
        "generic_template",
        "identity_leakage",
        "unsupported_claim",
        "broken_example",
        "promotional_imbalance",
        "prompt_injection",
        "multi_root",
        "source_build_only",
        "malformed_readme",
        "strong_existing_content",
        "conflicting_fact",
    } <= categories


def test_source_build_fixture_is_concrete_and_self_contained():
    cpp = next(item for item in REVIEW_ARCHETYPES if item.ecosystem == "cpp")
    candidate = specific_candidate(cpp)

    assert "cmake -S . -B build" in candidate
    assert "cmake --build build" in candidate
    assert "#include <acme/slides/presentation.hpp>" in candidate
    assert "int main()" in candidate
    assert "example.invalid" not in candidate
    assert "Release 1.0.0 is recorded at revision golden-set-revision" in candidate


def test_malformed_markdown_control_does_not_introduce_an_unsupported_example():
    scenario = next(item for item in REVIEW_SCENARIOS if item.category == "malformed_readme")
    python_example = next(item.example for item in REVIEW_ARCHETYPES if item.ecosystem == "python")

    assert scenario.candidate_readme.count(python_example) == 2
    assert scenario.candidate_readme.count("```") % 2 == 1
    assert "unterminated code fence" not in scenario.candidate_readme


def test_review_harness_scores_the_real_prompt_contract():
    class CapturingClient:
        def __init__(self):
            self.delegate = _passing_review_client()
            self.messages: list[list[dict]] = []

        def analyze(self, messages: list[dict]) -> AnalysisResult:
            self.messages.append(messages)
            return self.delegate.analyze(messages)

    client = CapturingClient()
    results = review_harness.run_review_golden_set(client)

    assert len(results) == len(REVIEW_SCENARIOS)
    assert all(result.passed for result in results)
    assert {result.expected_verdict for result in results} == {
        "ACCEPT",
        "REJECT_REPAIRABLE",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
    }
    for scenario, messages in zip(REVIEW_SCENARIOS, client.messages, strict=True):
        assert scenario.scenario_id not in json.dumps(messages)


def test_three_session_report_meets_volume_and_route_thresholds():
    report = qualification.run_qualification(
        _passing_planner_client,
        _passing_review_client,
        sessions=3,
        deterministic=_deterministic(),
    )

    assert report["session_count"] == 3
    assert report["total_evaluations"] >= 100
    assert report["pass_rate"] == 1.0
    assert report["qualified"] is True
    assert all(item["pass_rate"] == 1.0 for item in report["routes"].values())


def test_report_fails_closed_below_session_and_volume_minimums():
    report = qualification.run_qualification(
        _passing_planner_client,
        _passing_review_client,
        sessions=1,
        deterministic=_deterministic(),
    )

    assert report["session_count"] == 1
    assert report["total_evaluations"] < report["minimum_evaluations"]
    assert report["volume_complete"] is False
    assert report["qualified"] is False


def test_report_requires_each_route_to_meet_the_threshold():
    planner_results = [
        qualification.QualificationEvaluation(
            session=1,
            job="supervisor_planning",
            scenario_id=f"planner-{index}",
            category="routing",
            ecosystem=None,
            passed=index < 94,
            expected="inspect_repository",
            actual="inspect_repository" if index < 94 else "STOP",
            detail="controlled",
            prompt_tokens=None,
            latency_seconds=None,
        )
        for index in range(100)
    ]
    reviewer_results = [
        qualification.QualificationEvaluation(
            session=1,
            job="independent_readme_review",
            scenario_id=f"review-{index}",
            category="review",
            ecosystem="java",
            passed=True,
            expected="ACCEPT",
            actual="ACCEPT",
            detail="controlled",
            prompt_tokens=None,
            latency_seconds=None,
        )
        for index in range(100)
    ]
    report = qualification.build_qualification_report(
        [*planner_results, *reviewer_results],
        sessions=3,
        deterministic=_deterministic(),
    )

    assert report["pass_rate"] >= 0.95
    assert report["routes"]["supervisor_planning"]["pass_rate"] < 0.95
    assert report["qualified"] is False


def test_report_requires_100_percent_deterministic_validation():
    report = qualification.run_qualification(
        _passing_planner_client,
        _passing_review_client,
        sessions=3,
        deterministic=_deterministic(passed=41, total=42),
    )

    assert report["deterministic_validation"]["complete"] is False
    assert report["qualified"] is False
