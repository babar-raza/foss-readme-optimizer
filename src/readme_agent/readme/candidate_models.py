"""Immutable typed result of README candidate construction."""

from dataclasses import dataclass
from pathlib import Path

from readme_agent.gitsafety.verify import PushBlockProof
from readme_agent.llm.client import GeneratedResult
from readme_agent.readme.facts import RepositoryFacts
from readme_agent.readme.gap_detector import GapReport
from readme_agent.registry.models import ProductEntry


@dataclass
class ReadmeCandidate:
    """A validated proposal that has not crossed the effect boundary."""

    entry: ProductEntry
    work_path: Path
    readme_path: Path
    baseline_readme_text: str
    original_text: str
    final_text: str
    facts: RepositoryFacts
    facts_hash: str
    fresh_fingerprint: str
    gap_report: GapReport
    skip_regeneration: bool
    durable_skip: bool
    new_spans: dict[str, str]
    existing_rendered_spans: dict[str, str]
    llm_called: bool
    llm_calls: list[str]
    llm_request: list[dict[str, str]] | None
    llm_response: object | None
    generated_result: GeneratedResult | None
    validation_results: list
    status: str
    proof: PushBlockProof
