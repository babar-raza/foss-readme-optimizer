"""Run context-isolated quality and factual README reviews and reduce their verdicts."""

from __future__ import annotations

import json
from typing import cast

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.llm import prompt_registry
from readme_agent.llm.reviewer_client import build_live_role_review_clients
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.independent_readme_review import (
    record_review_verdict,
)
from readme_agent.specialists.readme_review_reducer import (
    SeparatedReadmeReviewResultV1,
    build_compatibility_result,
    build_role_review_record,
    combine_review_verdicts,
)
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewInputV1,
    BlindQualityReviewResultV1,
    FactualPlanReviewInputV1,
    FactualPlanReviewResultV1,
    ReviewActorIdentityV1,
    ReviewRole,
    input_hash,
    json_hash,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike, run_grounded_role
from readme_agent.state.backend import StateBackend

_OBSERVED_BY = "separated_readme_review"
_AUTHOR_PROMPT_ID = "plan_readme_composition"
_BLIND_PROMPT_ID = "blind_readme_quality_review"
_FACTUAL_PROMPT_ID = "factual_readme_plan_review"
_READ_ONLY_PERMISSIONS: set[PermissionClass] = {"read_only_local", "read_only_network"}


def _role_identity(actor_id: str, role: ReviewRole, prompt_id: str) -> ReviewActorIdentityV1:
    return ReviewActorIdentityV1(
        actor_id=actor_id,
        role=role,
        prompt_id=prompt_id,
        prompt_sha256=prompt_registry.prompt_hash(prompt_id),
    )


def run_separated_readme_review(
    org_repo: str,
    original_readme_text: str,
    candidate_readme_text: str,
    presentation_plan: dict,
    product_facts_v2: dict | None,
    *,
    blind_client: AnalysisClientLike | None = None,
    factual_client: AnalysisClientLike | None = None,
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

    blind_result, blind_retry_history, blind_grounding = run_grounded_role(
        role="blind_quality",
        prompt_id=_BLIND_PROMPT_ID,
        client=blind_client,
        messages=build_blind_quality_review_messages(
            blind_input.org_repo,
            blind_input.original_readme_text,
            blind_input.candidate_readme_text,
        ),
        candidate_text=candidate_readme_text,
        product_facts=None,
    )
    factual_result, factual_retry_history, factual_grounding = run_grounded_role(
        role="factual_plan",
        prompt_id=_FACTUAL_PROMPT_ID,
        client=factual_client,
        messages=build_factual_plan_review_messages(
            factual_input.org_repo,
            factual_input.candidate_readme_text,
            _canonical_json(product_facts_v2),
            _canonical_json(presentation_plan),
        ),
        candidate_text=candidate_readme_text,
        product_facts=product_facts_v2,
    )
    blind_result = cast(BlindQualityReviewResultV1, blind_result)
    factual_result = cast(FactualPlanReviewResultV1, factual_result)
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
        "producer:readme-composition",
        "author",
        _AUTHOR_PROMPT_ID,
    )
    blind_record = build_role_review_record(
        identity=blind_identity,
        candidate_sha256=candidate_sha256,
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
        candidate_sha256=candidate_sha256,
        input_sha256=input_hash(factual_input),
        verdict=factual_result.verdict,
        reasoning=factual_result.reasoning,
        failed_criteria=factual_result.failed_criteria,
        sections_affected=factual_result.sections_affected,
        required_repair=factual_result.required_repair,
        findings=factual_result.findings,
        grounding_validation=factual_grounding,
    )
    combined = combine_review_verdicts(
        author=author,
        blind_quality=blind_record,
        factual_plan=factual_record,
    )
    review = build_compatibility_result(
        blind_result,
        factual_result,
        blind_record,
        factual_record,
        combined,
        [*blind_retry_history, *factual_retry_history],
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
