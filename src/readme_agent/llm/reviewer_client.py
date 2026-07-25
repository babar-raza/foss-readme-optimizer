"""Force independent README reviews through the governed verdict tool schema."""

from __future__ import annotations

from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import INDEPENDENT_README_REVIEW_TOOL_SCHEMA
from readme_agent.llm.verifier_client import LiveForcedToolClient

DEFAULT_MAX_TOKENS = 2400


class LiveIndependentReviewClient:
    """Expose the analysis-client seam using reliable forced native tool calling."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: float = 90,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        self._client = LiveForcedToolClient(
            base_url,
            api_key,
            model,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        result = self._client.call(messages, INDEPENDENT_README_REVIEW_TOOL_SCHEMA)
        return AnalysisResult(parsed=result.arguments, meta=result.meta)
