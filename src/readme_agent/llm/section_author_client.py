"""Forced-tool-call client for one section-cluster authoring call.

Bounded to `transport_max_attempts=2` per the RELIABILITY contract: the probe observed a ~7.4%
transient-500 backend rate (`RESOLVED_MODEL_AND_ENDPOINT.json`), fully recoverable on one
immediate retry with identical request bytes both times. `response_max_attempts=1` -- this
client never retries on a schema/parse failure; that is a distinct, specialist-level bounded
correction (one same-cluster retry with a semantic-correction turn), not a transport concern.
"""

from readme_agent import env
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.section_authoring_prompts import build_section_cluster_authoring_tool_schema
from readme_agent.llm.verifier_client import LiveForcedToolClient

MAX_OUTPUT_TOKENS = 2048
TRANSPORT_MAX_ATTEMPTS = 2


class LiveSectionClusterAuthorClient:
    """One physical authoring call, bounded transport retry only."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: float = 90,
        max_tokens: int = MAX_OUTPUT_TOKENS,
    ):
        self._client = LiveForcedToolClient(
            base_url,
            api_key,
            model,
            timeout=timeout,
            max_tokens=max_tokens,
            job="section_cluster_authoring",
            prompt_id="section_cluster_authoring",
            transport_max_attempts=TRANSPORT_MAX_ATTEMPTS,
            response_max_attempts=1,
        )

    def analyze_section_cluster(
        self, messages: list[dict], accepted_fact_ids: list[str]
    ) -> AnalysisResult:
        """Mirrors `LiveTrustedFidelityReviewClient.analyze_fidelity`'s shape: the tool
        schema's citable `fact_ids` enum is bound per call, so this is a dedicated method
        rather than the shared `AnalysisClientLike.analyze(messages)` seam."""

        result = self._client.call(
            messages,
            build_section_cluster_authoring_tool_schema(accepted_fact_ids),
        )
        return AnalysisResult(parsed=result.arguments, meta=result.meta)


def build_live_section_cluster_author_client(
    base_url: str,
    api_key: str | None,
    *,
    timeout: float = 90,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> LiveSectionClusterAuthorClient:
    """Construct the canonical section-cluster author from its governed route."""

    return LiveSectionClusterAuthorClient(
        base_url,
        api_key,
        env.llm_model_for_job("section_cluster_authoring"),
        timeout=timeout,
        max_tokens=max_tokens,
    )
