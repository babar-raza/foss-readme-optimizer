"""LLM client Protocol -- live/fixture branch behind one interface."""

from dataclasses import dataclass
from typing import Protocol

from readme_agent.llm.schema import LLMBlockResponse, LLMResponseMeta


@dataclass
class GeneratedResult:
    response: LLMBlockResponse
    meta: LLMResponseMeta
    mode: str  # "live" | "fixture" -- recorded in evidence, never inferred
    was_fenced: bool = False  # flagged, not silently accepted -- the prompt
    # contract says a fenced response shouldn't happen


class LLMClient(Protocol):
    def generate(self, messages: list[dict[str, str]]) -> GeneratedResult: ...
