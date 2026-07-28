"""Run context-isolated quality and factual README reviews and reduce their verdicts."""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import Field, ValidationError

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.errors import LLMError
from readme_agent.llm import prompt_registry
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.reviewer_client import build_live_role_review_clients
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.independent_readme_review import (
    IndependentReadmeReviewResultV1,
    record_review_verdict,
)
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewInputV1,
    BlindQualityReviewResultV1,
    CombinedReadmeReviewV1,
    FactualPlanReviewInputV1,
    FactualPlanReviewResultV1,
    FactualPlanVerdict,
    ReviewActorIdentityV1,
    ReviewRole,
    RoleReviewRecordV1,
    combine_review_verdicts,
    input_hash,
    json_hash,
)
from readme_agent.state.backend import StateBackend

_OBSERVED_BY = "separated_readme_review"
_AUTHOR_PROMPT_ID = "plan_readme_composition"
_BLIND_PROMPT_ID = "blind_readme_quality_review"
_FACTUAL_PROMPT_ID = "factual_readme_plan_review"
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


class _AnalysisClientLike(Protocol):
    def analyze(self, messages: list[dict]) -> AnalysisResult: ...


class SeparatedReadmeReviewResultV1(IndependentReadmeReviewResultV1):
    """Compatibility verdict plus both immutable role records and their reduction."""

    blind_quality_review: RoleReviewRecordV1
    factual_plan_review: RoleReviewRecordV1
    combined_review: CombinedReadmeReviewV1
    review_contract_version: str = Field(default="1", frozen=True)


def _role_identity(actor_id: str, role: ReviewRole, prompt_id: str) -> ReviewActorIdentityV1:
    return ReviewActorIdentityV1(
        actor_id=actor_id,
        role=role,
        prompt_id=prompt_id,
        prompt_sha256=prompt_registry.prompt_hash(prompt_id),
    )


def _parse_blind_result(result: AnalysisResult) -> BlindQualityReviewResultV1:
    try:
        return BlindQualityReviewResultV1.model_validate(result.parsed)
    except ValidationError as exc:
        raise LLMError(f"blind README quality review violated its output contract: {exc}") from exc


def _parse_factual_result(result: AnalysisResult) -> FactualPlanReviewResultV1:
    try:
        return FactualPlanReviewResultV1.model_validate(result.parsed)
    except ValidationError as exc:
        raise LLMError(f"factual README plan review violated its output contract: {exc}") from exc


def _record(
    *,
    identity: ReviewActorIdentityV1,
    candidate_sha256: str,
    input_sha256: str,
    verdict: FactualPlanVerdict,
    reasoning: str,
) -> RoleReviewRecordV1:
    return RoleReviewRecordV1(
        identity=identity,
        candidate_sha256=candidate_sha256,
        input_sha256=input_sha256,
        verdict=verdict,
        reasoning=reasoning,
    )


def _compatibility_result(
    blind: BlindQualityReviewResultV1,
    factual: FactualPlanReviewResultV1,
    blind_record: RoleReviewRecordV1,
    factual_record: RoleReviewRecordV1,
    combined: CombinedReadmeReviewV1,
) -> SeparatedReadmeReviewResultV1:
    failed_criteria = sorted({*blind.failed_criteria, *factual.failed_criteria})
    sections_affected = sorted({*blind.sections_affected, *factual.sections_affected})
    repairs = [
        repair.strip()
        for repair in (blind.required_repair, factual.required_repair)
        if repair.strip()
    ]
    return SeparatedReadmeReviewResultV1(
        verdict=combined.verdict,
        reasoning="; ".join(combined.reasons),
        failed_criteria=failed_criteria,
        sections_affected=sections_affected,
        required_repair="\n".join(repairs),
        preserve=[],
        blind_quality_review=blind_record,
        factual_plan_review=factual_record,
        combined_review=combined,
    )


def run_separated_readme_review(
    org_repo: str,
    original_readme_text: str,
    candidate_readme_text: str,
    presentation_plan: dict,
    product_facts_v2: dict | None,
    *,
    blind_client: _AnalysisClientLike | None = None,
    factual_client: _AnalysisClientLike | None = None,
    backend: StateBackend | None = None,
    repair_attempt: int = 0,
    author_identity: ReviewActorIdentityV1 | None = None,
) -> SeparatedReadmeReviewResultV1:
    """Run both isolated roles against one candidate and record only the reduced verdict."""

    if (blind_client is None) != (factual_client is None):
        raise ValueError("blind and factual review clients must be supplied together")
    if blind_client is None or factual_client is None:
        blind_client, factual_client = build_live_role_review_clients(
            env.llm_base_url(),
            env.llm_api_key(),
        )

    if product_facts_v2 is None:
        facts_dispatch = dispatch_tool_call(
            {
                "function": {
                    "name": "get_product_facts",
                    "arguments": json.dumps({"org_repo": org_repo}),
                }
            },
            _READ_ONLY_PERMISSIONS,
            caller_domain=INDEPENDENT_VERIFICATION,
        )
        if facts_dispatch.outcome != "executed" or facts_dispatch.result is None:
            raise RuntimeError(
                "separated review could not obtain ProductFactsV2: "
                f"{facts_dispatch.outcome}:{facts_dispatch.error}"
            )
        product_facts_v2 = facts_dispatch.result["product_facts_v2"]

    candidate_sha256 = sha256_hex(candidate_readme_text)
    blind_input = BlindQualityReviewInputV1(
        org_repo=org_repo,
        original_readme_text=original_readme_text,
        candidate_readme_text=candidate_readme_text,
        candidate_sha256=candidate_sha256,
        rubric_version="1",
    )
    factual_input = FactualPlanReviewInputV1(
        org_repo=org_repo,
        candidate_readme_text=candidate_readme_text,
        candidate_sha256=candidate_sha256,
        product_facts=product_facts_v2,
        product_facts_sha256=json_hash(product_facts_v2),
        presentation_plan=presentation_plan,
        presentation_plan_sha256=json_hash(presentation_plan),
        rubric_version="1",
    )

    blind_result = _parse_blind_result(
        blind_client.analyze(
            build_blind_quality_review_messages(
                blind_input.org_repo,
                blind_input.original_readme_text,
                blind_input.candidate_readme_text,
            )
        )
    )
    factual_result = _parse_factual_result(
        factual_client.analyze(
            build_factual_plan_review_messages(
                factual_input.org_repo,
                factual_input.candidate_readme_text,
                _canonical_json(product_facts_v2),
                _canonical_json(presentation_plan),
            )
        )
    )
    blind_identity = _role_identity(
        "llm-route:blind-readme-quality",
        "blind_quality_reviewer",
        _BLIND_PROMPT_ID,
    )
    factual_identity = _role_identity(
        "llm-route:factual-readme-plan",
        "factual_plan_reviewer",
        _FACTUAL_PROMPT_ID,
    )
    author = author_identity or _role_identity(
        "llm-route:readme-composition",
        "author",
        _AUTHOR_PROMPT_ID,
    )
    blind_record = _record(
        identity=blind_identity,
        candidate_sha256=candidate_sha256,
        input_sha256=input_hash(blind_input),
        verdict=blind_result.verdict,
        reasoning=blind_result.reasoning,
    )
    factual_record = _record(
        identity=factual_identity,
        candidate_sha256=candidate_sha256,
        input_sha256=input_hash(factual_input),
        verdict=factual_result.verdict,
        reasoning=factual_result.reasoning,
    )
    combined = combine_review_verdicts(
        author=author,
        blind_quality=blind_record,
        factual_plan=factual_record,
    )
    review = _compatibility_result(
        blind_result,
        factual_result,
        blind_record,
        factual_record,
        combined,
    )
    if backend is not None:
        record_review_verdict(
            backend,
            org_repo,
            review,
            repair_attempt=repair_attempt,
            observed_by=_OBSERVED_BY,
        )
    return review


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
