"""Wave 8.6 (`OPS-011`): scores a planner client against `scenarios.SCENARIOS`.
Reuses the REAL prompt registry + `supervisor/dossier.py::render_turn_context()`
-- never a duplicate prompt -- and calls the real `PlannerClient.plan()`, but
NEVER `capabilities/dispatcher.py::dispatch_tool_call()`/`supervisor/loop.py::
_dispatch_and_record()`: this is what makes a golden-set run structurally
non-mutating, stronger than `dry_run` mode (which still executes read-only
capabilities) -- a scenario's chosen capability is only ever compared by
name, never actually invoked."""

import time
from dataclasses import dataclass

from readme_agent.capabilities import registry
from readme_agent.errors import LLMError
from readme_agent.golden_set.scenarios import SCENARIOS, STOP, GoldenScenario
from readme_agent.llm import prompt_registry
from readme_agent.llm.planner_client import PlannerClient
from readme_agent.supervisor import dossier


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    passed: bool
    actual_capability_id: str | None  # None means the model stopped (no tool_call)
    detail: str
    prompt_tokens: int | None = None
    latency_seconds: float | None = None


def _score(scenario: GoldenScenario, actual_capability_id: str | None) -> tuple[bool, str]:
    if scenario.expected_capability_id is not None:
        expected = scenario.expected_capability_id
        actual = STOP if actual_capability_id is None else actual_capability_id
        passed = actual == expected
        return passed, f"expected {expected!r}, got {actual!r}"

    forbidden = scenario.forbidden_capability_id
    passed = actual_capability_id != forbidden
    return passed, f"forbidden {forbidden!r}, got {actual_capability_id!r}"


def run_golden_set(
    planner_client: PlannerClient, scenarios: tuple[GoldenScenario, ...] = SCENARIOS
) -> list[ScenarioResult]:
    manifest = prompt_registry.get("supervisor_turn")
    assert manifest is not None, "prompts/planning/supervisor_turn.yaml missing"
    tools = registry.all_tool_schemas()
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        messages = [
            {"role": "system", "content": manifest.system},
            {
                "role": "user",
                "content": dossier.render_turn_context(
                    manifest,
                    org_repo=scenario.bootstrap_result.get("org_repo", "golden-set/scenario"),
                    turn_number=len(scenario.tried_capability_ids) + 1,
                    max_turns=8,
                    tried_capability_ids=scenario.tried_capability_ids,
                    bootstrap_result=scenario.bootstrap_result,
                    dossier=scenario.dossier,
                ),
            },
        ]

        start = time.monotonic()
        try:
            plan = planner_client.plan(messages, tools)
        except LLMError as exc:
            results.append(
                ScenarioResult(
                    scenario_id=scenario.scenario_id,
                    category=scenario.category,
                    passed=False,
                    actual_capability_id=None,
                    detail=f"planner call failed: {exc}",
                )
            )
            continue
        latency = time.monotonic() - start

        actual_capability_id = (
            plan.tool_call.get("function", {}).get("name") if plan.tool_call else None
        )
        passed, detail = _score(scenario, actual_capability_id)
        prompt_tokens = plan.meta.usage.prompt_tokens if plan.meta.usage else None
        results.append(
            ScenarioResult(
                scenario_id=scenario.scenario_id,
                category=scenario.category,
                passed=passed,
                actual_capability_id=actual_capability_id,
                detail=detail,
                prompt_tokens=prompt_tokens,
                latency_seconds=latency,
            )
        )

    return results


def summarize(results: list[ScenarioResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    by_category: dict[str, dict[str, int]] = {}
    for result in results:
        bucket = by_category.setdefault(result.category, {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += 1 if result.passed else 0
    return {
        "total": total,
        "passed": passed,
        "pass_rate": (passed / total) if total else None,
        "by_category": by_category,
    }
