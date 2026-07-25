"""Structural acceptance checks for the independent-review golden corpus."""

from collections.abc import Iterable
from typing import Protocol


class _ScenarioLike(Protocol):
    @property
    def scenario_id(self) -> str: ...

    @property
    def ecosystem(self) -> str: ...

    @property
    def category(self) -> str: ...


def validate_review_scenario_corpus(scenarios: Iterable[_ScenarioLike]) -> None:
    scenarios = tuple(scenarios)
    ids = [scenario.scenario_id for scenario in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("independent-review golden-set scenario IDs must be unique")
    ecosystems = {scenario.ecosystem for scenario in scenarios}
    expected_ecosystems = {"java", "dotnet", "python", "typescript", "cpp", "go", "rust"}
    if ecosystems != expected_ecosystems:
        raise ValueError(f"independent-review golden set has incomplete ecosystems: {ecosystems}")
    required_categories = {
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
    }
    categories = {scenario.category for scenario in scenarios}
    missing = required_categories - categories
    if missing:
        raise ValueError(f"independent-review golden set has missing controls: {sorted(missing)}")
