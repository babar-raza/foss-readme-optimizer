"""Execute one physical README review call and ground its two returned facets."""

import json
from dataclasses import dataclass
from typing import cast

from readme_agent.errors import LLMError
from readme_agent.llm import prompt_registry
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.merged_readme_review import build_merged_readme_review_messages
from readme_agent.specialists.merged_readme_review_contracts import (
    MergedReadmeReviewResultV1,
    MergedReviewCallReceiptV1,
    role_record_hash,
)
from readme_agent.specialists.readme_review_reducer import build_role_review_record
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewInputV1,
    BlindQualityReviewResultV1,
    FactualPlanReviewInputV1,
    FactualPlanReviewResultV1,
    ReviewActorIdentityV1,
    RoleReviewRecordV1,
    input_hash,
    json_hash,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike, run_grounded_role

_MERGED_PROMPT_ID = "merged_readme_review"
_MERGED_ACTOR_ID = "llm-route:merged-readme-review"


@dataclass(frozen=True)
class MergedReviewExecutionV1:
    """Compatibility projection and physical-call evidence from one merged review."""

    blind_result: BlindQualityReviewResultV1
    factual_result: FactualPlanReviewResultV1
    blind_record: RoleReviewRecordV1
    factual_record: RoleReviewRecordV1
    receipt: MergedReviewCallReceiptV1
    grounding_history: list[dict]


def execute_merged_readme_review(
    *,
    org_repo: str,
    candidate_text: str,
    visitor_contract: dict,
    fact_context: dict,
    plan_context: dict,
    product_facts: dict,
    blind_input: BlindQualityReviewInputV1,
    factual_input: FactualPlanReviewInputV1,
    client: AnalysisClientLike,
) -> MergedReviewExecutionV1:
    """Make one paid call, then ground both returned facets without provider retries."""

    messages = build_merged_readme_review_messages(
        org_repo,
        candidate_text,
        _canonical_json(visitor_contract),
        _canonical_json(fact_context),
        _canonical_json(plan_context),
    )
    analysis = client.analyze(messages)
    if not isinstance(analysis.parsed, dict) or set(analysis.parsed) != {"quality", "factual"}:
        raise LLMError("merged README review must return exactly quality and factual facets")
    quality_payload = analysis.parsed["quality"]
    factual_payload = analysis.parsed["factual"]
    if not isinstance(quality_payload, dict) or not isinstance(factual_payload, dict):
        raise LLMError("merged README review facets must each be structured objects")
    blind_result, blind_history, blind_grounding = run_grounded_role(
        role="blind_quality",
        prompt_id=_MERGED_PROMPT_ID,
        client=_OneResultClient(quality_payload, analysis),
        messages=messages,
        candidate_text=candidate_text,
        product_facts=None,
        visitor_contract=visitor_contract,
        max_attempts_override=1,
    )
    factual_result, factual_history, factual_grounding = run_grounded_role(
        role="factual_plan",
        prompt_id=_MERGED_PROMPT_ID,
        client=_OneResultClient(factual_payload, analysis),
        messages=messages,
        candidate_text=candidate_text,
        product_facts=product_facts,
        max_attempts_override=1,
    )
    blind_result = cast(BlindQualityReviewResultV1, blind_result)
    factual_result = cast(FactualPlanReviewResultV1, factual_result)
    MergedReadmeReviewResultV1(quality=blind_result, factual=factual_result)
    prompt_sha256 = prompt_registry.prompt_hash(_MERGED_PROMPT_ID)
    blind_identity = ReviewActorIdentityV1(
        actor_id=_MERGED_ACTOR_ID,
        role="blind_quality_reviewer",
        prompt_id=_MERGED_PROMPT_ID,
        prompt_sha256=prompt_sha256,
    )
    factual_identity = ReviewActorIdentityV1(
        actor_id=_MERGED_ACTOR_ID,
        role="factual_plan_reviewer",
        prompt_id=_MERGED_PROMPT_ID,
        prompt_sha256=prompt_sha256,
    )
    blind_record = build_role_review_record(
        identity=blind_identity,
        candidate_sha256=blind_input.candidate_sha256,
        input_sha256=input_hash(blind_input),
        verdict=blind_result.verdict,
        reasoning=blind_result.reasoning,
        failed_criteria=blind_result.failed_criteria,
        sections_affected=blind_result.sections_affected,
        required_repair=blind_result.required_repair,
        findings=blind_result.findings,
        grounding_validation=blind_grounding,
    )
    factual_record = build_role_review_record(
        identity=factual_identity,
        candidate_sha256=factual_input.candidate_sha256,
        input_sha256=input_hash(factual_input),
        verdict=factual_result.verdict,
        reasoning=factual_result.reasoning,
        failed_criteria=factual_result.failed_criteria,
        sections_affected=factual_result.sections_affected,
        required_repair=factual_result.required_repair,
        findings=factual_result.findings,
        grounding_validation=factual_grounding,
    )
    receipt = MergedReviewCallReceiptV1(
        actor_id=_MERGED_ACTOR_ID,
        prompt_id=_MERGED_PROMPT_ID,
        prompt_sha256=prompt_sha256,
        input_sha256=json_hash({"messages": messages}),
        raw_output_sha256=json_hash(analysis.parsed),
        blind_record_sha256=role_record_hash(blind_record),
        factual_record_sha256=role_record_hash(factual_record),
        provider_request_id=analysis.meta.request_id,
        provider_model=analysis.meta.model,
    )
    return MergedReviewExecutionV1(
        blind_result=blind_result,
        factual_result=factual_result,
        blind_record=blind_record,
        factual_record=factual_record,
        receipt=receipt,
        grounding_history=[*blind_history, *factual_history],
    )


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class _OneResultClient:
    """Project one already-paid merged facet through existing deterministic grounding."""

    def __init__(self, parsed: dict, merged_analysis: AnalysisResult) -> None:
        self._parsed = parsed
        self._meta = merged_analysis.meta
        self._used = False

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        if self._used:
            raise LLMError("a merged review facet cannot repeat the same physical response")
        self._used = True
        return AnalysisResult(parsed=self._parsed, meta=self._meta)
