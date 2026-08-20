"""Execute one physical README review call and recover unresolved facets deterministically."""

import json
from dataclasses import dataclass
from typing import Literal, cast

from readme_agent.errors import (
    LLMError,
    LLMInfrastructureError,
    LLMTruncatedResponseError,
    MergedReviewRequestTooLargeError,
    MergedReviewSchemaError,
)
from readme_agent.llm import prompt_registry
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.merged_readme_review import (
    build_merged_readme_review_messages,
    enforce_merged_review_request_ceiling,
)
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.specialists.merged_readme_review_contracts import (
    FacetRecoveryV1,
    MergedReadmeReviewResultV1,
    MergedReviewCallReceiptV1,
    QwenReviewRecoveryReceiptV1,
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
from readme_agent.specialists.review_finding_grounding import FindingGroundingResultV1
from readme_agent.specialists.review_role_execution import (
    AnalysisClientLike,
    GroundedRoleFailure,
    run_grounded_role,
)

_MERGED_PROMPT_ID = "merged_readme_review"
_MERGED_ACTOR_ID = "llm-route:merged-readme-review"
_BLIND_PROMPT_ID = "blind_readme_quality_review"
_BLIND_ACTOR_ID = "llm-route:blind-readme-quality"
_FACTUAL_PROMPT_ID = "factual_readme_plan_review"
_FACTUAL_ACTOR_ID = "llm-route:factual-readme-plan"

# Every recovery-path grounding call is bounded to 1 initial + 1 compact retry, capping
# worst-case physical calls for one merged review at 1 (normal) + 2 (blind) + 2 (factual) = 5.
_RECOVERY_MAX_ATTEMPTS = 2

_MergedCallOutcome = Literal[
    "success",
    "request_ceiling_exceeded",
    "truncated_response",
    "malformed_arguments",
    "transport_failure",
    "top_level_schema_failure",
]
_FacetRecoveryReason = Literal[
    "request_ceiling_exceeded",
    "truncated_response",
    "malformed_arguments",
    "transport_failure",
    "top_level_schema_failure",
    "grounding_failure",
]


def _facet_recovery_reason(
    *, unresolved_via_grounding: bool, merged_call_outcome: _MergedCallOutcome
) -> _FacetRecoveryReason:
    if unresolved_via_grounding:
        return "grounding_failure"
    assert merged_call_outcome != "success"
    return merged_call_outcome


@dataclass(frozen=True)
class MergedReviewExecutionV1:
    """Compatibility projection and physical-call evidence from one merged review."""

    blind_result: BlindQualityReviewResultV1
    factual_result: FactualPlanReviewResultV1
    blind_record: RoleReviewRecordV1
    factual_record: RoleReviewRecordV1
    receipt: MergedReviewCallReceiptV1 | None
    recovery_receipt: QwenReviewRecoveryReceiptV1 | None
    grounding_history: list[dict]


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


class _MeteringClient:
    """Wrap a recovery client to capture per-attempt telemetry for the recovery receipt,
    without threading new fields through run_grounded_role's shared attempt history."""

    def __init__(self, inner: AnalysisClientLike) -> None:
        self._inner = inner
        self.responses: list[LLMResponseMeta] = []

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        result = self._inner.analyze(messages)
        self.responses.append(result.meta)
        return result


def _system_failure_result(
    role: str, reasoning: str
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    payload = {
        "verdict": "SYSTEM_FAILURE",
        "reasoning": reasoning,
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [],
    }
    if role == "blind_quality":
        return BlindQualityReviewResultV1.model_validate(payload)
    return FactualPlanReviewResultV1.model_validate(payload)


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
    blind_fallback_client: AnalysisClientLike | None = None,
    factual_fallback_client: AnalysisClientLike | None = None,
) -> MergedReviewExecutionV1:
    """Make one merged call, recovering only whichever facet(s) it left unresolved."""

    messages = build_merged_readme_review_messages(
        org_repo,
        candidate_text,
        _canonical_json(visitor_contract),
        _canonical_json(fact_context),
        _canonical_json(plan_context),
    )

    merged_call_outcome: _MergedCallOutcome = "success"
    analysis: AnalysisResult | None = None
    quality_payload: dict | None = None
    factual_payload: dict | None = None
    top_level_exception: LLMError | None = None

    try:
        enforce_merged_review_request_ceiling(messages)
        analysis = client.analyze(messages)
        if not isinstance(analysis.parsed, dict) or set(analysis.parsed) != {"quality", "factual"}:
            raise MergedReviewSchemaError(
                "merged README review must return exactly quality and factual facets"
            )
        quality_payload = analysis.parsed["quality"]
        factual_payload = analysis.parsed["factual"]
        if not isinstance(quality_payload, dict) or not isinstance(factual_payload, dict):
            raise MergedReviewSchemaError(
                "merged README review facets must each be structured objects"
            )
    except MergedReviewRequestTooLargeError as exc:
        merged_call_outcome = "request_ceiling_exceeded"
        top_level_exception = exc
    except LLMTruncatedResponseError as exc:
        merged_call_outcome = "truncated_response"
        top_level_exception = exc
    except MergedReviewSchemaError as exc:
        merged_call_outcome = "top_level_schema_failure"
        top_level_exception = exc
    except LLMInfrastructureError as exc:
        merged_call_outcome = "transport_failure"
        top_level_exception = exc
    except LLMError as exc:
        merged_call_outcome = "malformed_arguments"
        top_level_exception = exc

    recovery_events: list[dict] = []
    facets_unresolved: set[str] = set()
    if top_level_exception is not None:
        facets_unresolved = {"blind", "factual"}
        if blind_fallback_client is None or factual_fallback_client is None:
            raise top_level_exception
        recovery_events.append(
            {
                "role": "merged",
                "fallback": "isolated_blind_and_factual",
                "trigger": merged_call_outcome,
                "merged_call_error": str(top_level_exception),
            }
        )

    blind_result: BlindQualityReviewResultV1 | None = None
    factual_result: FactualPlanReviewResultV1 | None = None
    blind_history: list[dict] = []
    factual_history: list[dict] = []
    blind_grounding: FindingGroundingResultV1 | None = None
    factual_grounding: FindingGroundingResultV1 | None = None
    blind_unresolved_via_grounding = False
    factual_unresolved_via_grounding = False

    if "factual" not in facets_unresolved:
        assert factual_payload is not None and analysis is not None
        try:
            factual_raw, factual_history, factual_grounding = run_grounded_role(
                role="factual_plan",
                prompt_id=_MERGED_PROMPT_ID,
                client=_OneResultClient(factual_payload, analysis),
                messages=messages,
                candidate_text=candidate_text,
                product_facts=product_facts,
                max_attempts_override=1,
            )
            factual_result = cast(FactualPlanReviewResultV1, factual_raw)
        except GroundedRoleFailure as exc:
            if factual_fallback_client is None:
                raise
            facets_unresolved.add("factual")
            factual_unresolved_via_grounding = True
            recovery_events.append(
                {
                    "role": "factual_plan",
                    "fallback": "isolated_factual_plan",
                    "trigger": "merged_factual_contract_failure",
                    "merged_raw_output_sha256": json_hash(analysis.parsed),
                    "merged_provider_request_id": analysis.meta.request_id,
                    "merged_failure_history": list(exc.retry_history),
                }
            )

    if "blind" not in facets_unresolved:
        assert quality_payload is not None and analysis is not None
        try:
            blind_raw, blind_history, blind_grounding = run_grounded_role(
                role="blind_quality",
                prompt_id=_MERGED_PROMPT_ID,
                client=_OneResultClient(quality_payload, analysis),
                messages=messages,
                candidate_text=candidate_text,
                product_facts=None,
                visitor_contract=visitor_contract,
                max_attempts_override=1,
            )
            blind_result = cast(BlindQualityReviewResultV1, blind_raw)
        except GroundedRoleFailure as exc:
            if blind_fallback_client is None:
                raise
            facets_unresolved.add("blind")
            blind_unresolved_via_grounding = True
            recovery_events.append(
                {
                    "role": "blind_quality",
                    "fallback": "isolated_blind_quality",
                    "trigger": "merged_quality_contract_failure",
                    "merged_raw_output_sha256": json_hash(analysis.parsed),
                    "merged_provider_request_id": analysis.meta.request_id,
                    "merged_failure_history": list(exc.retry_history),
                }
            )

    blind_recovery: FacetRecoveryV1 | None = None
    factual_recovery: FacetRecoveryV1 | None = None

    if "factual" in facets_unresolved:
        assert factual_fallback_client is not None
        metering = _MeteringClient(factual_fallback_client)
        reason = _facet_recovery_reason(
            unresolved_via_grounding=factual_unresolved_via_grounding,
            merged_call_outcome=merged_call_outcome,
        )
        try:
            factual_raw, factual_history, factual_grounding = run_grounded_role(
                role="factual_plan",
                prompt_id=_FACTUAL_PROMPT_ID,
                client=metering,
                messages=build_factual_plan_review_messages(
                    factual_input.org_repo,
                    factual_input.candidate_readme_text,
                    _canonical_json(fact_context),
                    _canonical_json(plan_context),
                ),
                candidate_text=candidate_text,
                product_facts=product_facts,
                max_attempts_override=_RECOVERY_MAX_ATTEMPTS,
            )
            factual_result = cast(FactualPlanReviewResultV1, factual_raw)
            factual_resolved = True
        except GroundedRoleFailure as exc:
            factual_result = cast(
                FactualPlanReviewResultV1,
                _system_failure_result(
                    "factual_plan",
                    "Factual review recovery exhausted its bounded compact retry.",
                ),
            )
            factual_grounding = None
            factual_history = [*factual_history, *exc.retry_history]
            factual_resolved = False
        factual_recovery = FacetRecoveryV1(
            facet="factual_plan",
            triggered=True,
            reason=reason,
            attempts=max(len(metering.responses), 1),
            resolved=factual_resolved,
            token_usage=[meta.usage for meta in metering.responses if meta.usage is not None],
            latency_ms=[
                meta.latency_ms for meta in metering.responses if meta.latency_ms is not None
            ],
        )

    if "blind" in facets_unresolved:
        assert blind_fallback_client is not None
        metering = _MeteringClient(blind_fallback_client)
        reason = _facet_recovery_reason(
            unresolved_via_grounding=blind_unresolved_via_grounding,
            merged_call_outcome=merged_call_outcome,
        )
        try:
            blind_raw, blind_history, blind_grounding = run_grounded_role(
                role="blind_quality",
                prompt_id=_BLIND_PROMPT_ID,
                client=metering,
                messages=build_blind_quality_review_messages(
                    blind_input.org_repo,
                    blind_input.original_readme_text,
                    blind_input.candidate_readme_text,
                    _canonical_json(blind_input.visitor_contract),
                ),
                candidate_text=candidate_text,
                product_facts=None,
                visitor_contract=visitor_contract,
                max_attempts_override=_RECOVERY_MAX_ATTEMPTS,
            )
            blind_result = cast(BlindQualityReviewResultV1, blind_raw)
            blind_resolved = True
        except GroundedRoleFailure as exc:
            blind_result = cast(
                BlindQualityReviewResultV1,
                _system_failure_result(
                    "blind_quality",
                    "Blind quality review recovery exhausted its bounded compact retry.",
                ),
            )
            blind_grounding = None
            blind_history = [*blind_history, *exc.retry_history]
            blind_resolved = False
        blind_recovery = FacetRecoveryV1(
            facet="blind_quality",
            triggered=True,
            reason=reason,
            attempts=max(len(metering.responses), 1),
            resolved=blind_resolved,
            token_usage=[meta.usage for meta in metering.responses if meta.usage is not None],
            latency_ms=[
                meta.latency_ms for meta in metering.responses if meta.latency_ms is not None
            ],
        )

    assert blind_result is not None and factual_result is not None
    MergedReadmeReviewResultV1(quality=blind_result, factual=factual_result)

    used_blind_fallback = blind_recovery is not None
    used_factual_fallback = factual_recovery is not None
    merged_prompt_sha256 = prompt_registry.prompt_hash(_MERGED_PROMPT_ID)
    blind_identity = ReviewActorIdentityV1(
        actor_id=_BLIND_ACTOR_ID if used_blind_fallback else _MERGED_ACTOR_ID,
        role="blind_quality_reviewer",
        prompt_id=_BLIND_PROMPT_ID if used_blind_fallback else _MERGED_PROMPT_ID,
        prompt_sha256=(
            prompt_registry.prompt_hash(_BLIND_PROMPT_ID)
            if used_blind_fallback
            else merged_prompt_sha256
        ),
    )
    factual_identity = ReviewActorIdentityV1(
        actor_id=_FACTUAL_ACTOR_ID if used_factual_fallback else _MERGED_ACTOR_ID,
        role="factual_plan_reviewer",
        prompt_id=_FACTUAL_PROMPT_ID if used_factual_fallback else _MERGED_PROMPT_ID,
        prompt_sha256=(
            prompt_registry.prompt_hash(_FACTUAL_PROMPT_ID)
            if used_factual_fallback
            else merged_prompt_sha256
        ),
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

    receipt: MergedReviewCallReceiptV1 | None = None
    if not used_blind_fallback and not used_factual_fallback:
        assert analysis is not None
        receipt = MergedReviewCallReceiptV1(
            actor_id=_MERGED_ACTOR_ID,
            prompt_id=_MERGED_PROMPT_ID,
            prompt_sha256=merged_prompt_sha256,
            input_sha256=json_hash({"messages": messages}),
            raw_output_sha256=json_hash(analysis.parsed),
            blind_record_sha256=role_record_hash(blind_record),
            factual_record_sha256=role_record_hash(factual_record),
            provider_request_id=analysis.meta.request_id,
            provider_model=analysis.meta.model,
        )

    recovery_receipt: QwenReviewRecoveryReceiptV1 | None = None
    if blind_recovery is not None or factual_recovery is not None:
        normal_call_spent = 0 if merged_call_outcome == "request_ceiling_exceeded" else 1
        total_physical_calls = (
            normal_call_spent
            + (blind_recovery.attempts if blind_recovery is not None else 0)
            + (factual_recovery.attempts if factual_recovery is not None else 0)
        )
        any_unresolved = (blind_recovery is not None and not blind_recovery.resolved) or (
            factual_recovery is not None and not factual_recovery.resolved
        )
        recovery_receipt = QwenReviewRecoveryReceiptV1(
            merged_call_outcome=merged_call_outcome,
            blind_facet_recovery=blind_recovery,
            factual_facet_recovery=factual_recovery,
            final_disposition="system_failure" if any_unresolved else "resolved_partial",
            total_physical_calls=total_physical_calls,
        )

    return MergedReviewExecutionV1(
        blind_result=blind_result,
        factual_result=factual_result,
        blind_record=blind_record,
        factual_record=factual_record,
        receipt=receipt,
        recovery_receipt=recovery_receipt,
        grounding_history=[*recovery_events, *blind_history, *factual_history],
    )


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
