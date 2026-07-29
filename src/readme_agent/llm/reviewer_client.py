"""Force independent README reviews through the governed verdict tool schema."""

from __future__ import annotations

from readme_agent import env
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.verification_prompts import (
    BLIND_QUALITY_REVIEW_TOOL_SCHEMA,
    FACTUAL_PLAN_REVIEW_TOOL_SCHEMA,
    INDEPENDENT_README_REVIEW_TOOL_SCHEMA,
    TRUSTED_FIDELITY_REVIEW_TOOL_SCHEMA,
)
from readme_agent.llm.verifier_client import LiveForcedToolClient

DEFAULT_MAX_TOKENS = 2400
TRUSTED_REVIEW_MAX_TOKENS = 8_000


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
            job="independent_readme_review",
            prompt_id="independent_readme_review",
        )

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        result = self._client.call(messages, INDEPENDENT_README_REVIEW_TOOL_SCHEMA)
        return AnalysisResult(parsed=result.arguments, meta=result.meta)


class LiveBlindQualityReviewClient:
    """Forced-schema client for the context-isolated visitor-quality role."""

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
            job="blind_readme_quality_review",
            prompt_id="blind_readme_quality_review",
        )

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        result = self._client.call(messages, BLIND_QUALITY_REVIEW_TOOL_SCHEMA)
        return AnalysisResult(parsed=result.arguments, meta=result.meta)


class LiveFactualPlanReviewClient:
    """Forced-schema client for the context-isolated factual-plan role."""

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
            job="factual_readme_plan_review",
            prompt_id="factual_readme_plan_review",
        )

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        result = self._client.call(messages, FACTUAL_PLAN_REVIEW_TOOL_SCHEMA)
        return AnalysisResult(parsed=result.arguments, meta=result.meta)


class LiveTrustedFidelityReviewClient:
    """Forced-schema client for README-inheritance fidelity only."""

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
            job="trusted_readme_fidelity_review",
            prompt_id="trusted_readme_fidelity_review",
        )

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        result = self._client.call(messages, TRUSTED_FIDELITY_REVIEW_TOOL_SCHEMA)
        return AnalysisResult(parsed=result.arguments, meta=result.meta)


def build_live_role_review_clients(
    base_url: str,
    api_key: str | None,
    *,
    timeout: float = 90,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> tuple[LiveBlindQualityReviewClient, LiveFactualPlanReviewClient]:
    """Construct the two governed role clients from their distinct model routes."""

    return (
        LiveBlindQualityReviewClient(
            base_url,
            api_key,
            env.llm_model_for_job("blind_readme_quality_review"),
            timeout=timeout,
            max_tokens=max_tokens,
        ),
        LiveFactualPlanReviewClient(
            base_url,
            api_key,
            env.llm_model_for_job("factual_readme_plan_review"),
            timeout=timeout,
            max_tokens=max_tokens,
        ),
    )


def build_live_trusted_review_clients(
    base_url: str,
    api_key: str | None,
    *,
    timeout: float = 90,
    max_tokens: int = TRUSTED_REVIEW_MAX_TOKENS,
) -> tuple[LiveBlindQualityReviewClient, LiveTrustedFidelityReviewClient]:
    """Construct disjoint blind-quality and inheritance-fidelity clients."""

    return (
        LiveBlindQualityReviewClient(
            base_url,
            api_key,
            env.llm_model_for_job("blind_readme_quality_review"),
            timeout=timeout,
            max_tokens=max_tokens,
        ),
        LiveTrustedFidelityReviewClient(
            base_url,
            api_key,
            env.llm_model_for_job("trusted_readme_fidelity_review"),
            timeout=timeout,
            max_tokens=max_tokens,
        ),
    )
