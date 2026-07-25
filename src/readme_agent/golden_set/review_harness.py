"""Score the real independent-review prompt without dispatching effects."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_scenarios import REVIEW_SCENARIOS, ReviewGoldenScenario
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import build_independent_readme_review_messages
from readme_agent.specialists.independent_readme_review import IndependentReadmeReviewResultV1


class _AnalysisClientLike(Protocol):
    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


@dataclass(frozen=True)
class ReviewScenarioResult:
    scenario_id: str
    ecosystem: str
    category: str
    passed: bool
    expected_verdict: str
    actual_verdict: str | None
    detail: str
    prompt_tokens: int | None = None
    latency_seconds: float | None = None


def run_review_golden_set(
    client: _AnalysisClientLike,
    scenarios: tuple[ReviewGoldenScenario, ...] = REVIEW_SCENARIOS,
) -> list[ReviewScenarioResult]:
    results: list[ReviewScenarioResult] = []
    for scenario in scenarios:
        product_facts = ProductFactsV2.model_validate(scenario.product_facts)
        messages = build_independent_readme_review_messages(
            f"golden-set/{scenario.scenario_id}",
            scenario.original_readme,
            scenario.candidate_readme,
            json.dumps(product_facts.model_dump(mode="json"), sort_keys=True),
            json.dumps(
                {
                    "scenario": scenario.scenario_id,
                    "operation": "review_only",
                    "expected_source_revision": "golden-set-revision",
                },
                sort_keys=True,
            ),
            json.dumps({"verdict": "accept", "checks": "deterministic controls passed"}),
        )
        started = time.monotonic()
        try:
            response = client.analyze(messages)
            review = IndependentReadmeReviewResultV1.model_validate(response.parsed)
        except (LLMError, ValueError) as exc:
            results.append(
                ReviewScenarioResult(
                    scenario.scenario_id,
                    scenario.ecosystem,
                    scenario.category,
                    False,
                    scenario.expected_verdict,
                    None,
                    f"review call or schema failed: {type(exc).__name__}: {exc}",
                )
            )
            continue
        latency = time.monotonic() - started
        actual = review.verdict
        passed = actual == scenario.expected_verdict
        usage = response.meta.usage
        results.append(
            ReviewScenarioResult(
                scenario.scenario_id,
                scenario.ecosystem,
                scenario.category,
                passed,
                scenario.expected_verdict,
                actual,
                f"expected {scenario.expected_verdict!r}, got {actual!r}",
                usage.prompt_tokens if usage else None,
                latency,
            )
        )
    return results
