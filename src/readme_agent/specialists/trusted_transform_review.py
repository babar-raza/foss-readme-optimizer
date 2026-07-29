"""Run and reduce independent trusted README quality and fidelity reviews."""

from __future__ import annotations

import json

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm import prompt_registry
from readme_agent.llm.call_ledger import (
    LlmAccountingSummaryV1,
    current_llm_accounting_summary,
    record_non_provider_call,
)
from readme_agent.llm.reviewer_client import build_live_trusted_review_clients
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_trusted_fidelity_review_messages,
    trusted_reviewer_standard_hash,
)
from readme_agent.readme.trusted_composition_candidate_validation import (
    validate_trusted_candidate_contract,
)
from readme_agent.readme.trusted_composition_models import TrustedReadmeCompositionOutputV1
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewInputV1,
    BlindQualityReviewResultV1,
    input_hash,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike, run_grounded_role
from readme_agent.specialists.trusted_fidelity_validation import run_trusted_fidelity_role
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedCandidateValidationV1,
    TrustedReviewActorIdentityV1,
    TrustedReviewCacheIdentityV1,
    TrustedReviewExecutionV1,
    TrustedReviewRoleRecordV1,
    TrustedReviewRoleV1,
    TrustedTransformReviewV1,
    TrustedTransformVerdictV1,
    canonical_hash,
)

_AUTHOR_PROMPT_ID = "trusted_readme_section_transform"
_BLIND_PROMPT_ID = "blind_readme_quality_review"
_FIDELITY_PROMPT_ID = "trusted_readme_fidelity_review"
_VALIDATION_CHECKS = (
    "candidate_hash_bound",
    "markdown_and_fence_integrity",
    "no_comments_or_cross_product_leakage",
    "configured_header_badge_navigation_mermaid_links_and_terminology",
    "complete_source_and_standard_accountability",
)


def _identity(
    actor_id: str,
    role: TrustedReviewRoleV1,
    prompt_id: str,
    model_route: str,
) -> TrustedReviewActorIdentityV1:
    return TrustedReviewActorIdentityV1(
        actor_id=actor_id,
        role=role,
        prompt_id=prompt_id,
        prompt_sha256=prompt_registry.prompt_hash(prompt_id),
        model_route=model_route,
    )


def _validation_receipt(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    composition: TrustedReadmeCompositionOutputV1,
) -> TrustedCandidateValidationV1:
    validate_trusted_candidate_contract(source_text, composition.candidate_markdown, graph)
    contract_hash = canonical_hash(
        {
            "version": "trusted-candidate-validation-v1",
            "checks": _VALIDATION_CHECKS,
            "configured_standards": [
                item.model_dump(mode="json") for item in graph.configured_standards
            ],
        }
    )
    return TrustedCandidateValidationV1(
        candidate_sha256=composition.candidate_sha256,
        contract_sha256=contract_hash,
        checks_passed=_VALIDATION_CHECKS,
    )


def _cache_identity(
    graph: TrustedReadmeFactGraphV1,
    composition: TrustedReadmeCompositionOutputV1,
    validation: TrustedCandidateValidationV1,
) -> TrustedReviewCacheIdentityV1:
    return TrustedReviewCacheIdentityV1(
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        source_sha256=graph.readme_sha256,
        fact_graph_sha256=graph.canonical_hash(),
        transform_plan_sha256=composition.plan_hash,
        candidate_sha256=composition.candidate_sha256,
        configured_standards_sha256=canonical_hash(
            [item.model_dump(mode="json") for item in graph.configured_standards]
        ),
        deterministic_validation_sha256=canonical_hash(validation.model_dump(mode="json")),
        author_prompt_sha256=prompt_registry.prompt_hash(_AUTHOR_PROMPT_ID),
        blind_prompt_sha256=prompt_registry.prompt_hash(_BLIND_PROMPT_ID),
        fidelity_prompt_sha256=prompt_registry.prompt_hash(_FIDELITY_PROMPT_ID),
        author_model_route=env.llm_model_for_job(_AUTHOR_PROMPT_ID),
        blind_model_route=env.llm_model_for_job(_BLIND_PROMPT_ID),
        fidelity_model_route=env.llm_model_for_job(_FIDELITY_PROMPT_ID),
        review_contract_sha256=trusted_reviewer_standard_hash(),
    )


def run_trusted_transform_review(
    graph: TrustedReadmeFactGraphV1,
    source_text: str,
    composition: TrustedReadmeCompositionOutputV1,
    *,
    blind_client: AnalysisClientLike | None = None,
    fidelity_client: AnalysisClientLike | None = None,
    cached_review: TrustedTransformReviewV1 | None = None,
) -> TrustedReviewExecutionV1:
    """Require deterministic validation and two identity-separated reviewer accepts."""

    if composition.org_repo != graph.org_repo:
        raise ValueError("trusted review graph and composition belong to different repositories")
    validation = _validation_receipt(graph, source_text, composition)
    identity = _cache_identity(graph, composition, validation)
    before = current_llm_accounting_summary()
    if before.status != "EXACT" or before.ledger_path is None:
        raise RuntimeError("trusted review requires active per-repository LLM call accounting")
    if (
        cached_review is not None
        and cached_review.verdict == "TRUSTED_TRANSFORM_APPROVED"
        and cached_review.cache_identity_sha256 == identity.canonical_hash()
    ):
        record_non_provider_call(
            job=_FIDELITY_PROMPT_ID,
            prompt_id=_FIDELITY_PROMPT_ID,
            prompt_sha256=identity.fidelity_prompt_sha256,
            model=identity.fidelity_model_route,
            disposition="cache_reuse",
            request=identity.model_dump(mode="json"),
        )
        after = current_llm_accounting_summary()
        return _execution(cached_review, True, before, after)
    if (blind_client is None) != (fidelity_client is None):
        raise ValueError("blind and fidelity clients must be supplied together")
    if blind_client is None or fidelity_client is None:
        blind_client, fidelity_client = build_live_trusted_review_clients(
            env.llm_base_url(),
            env.llm_api_key(),
        )
    if blind_client is fidelity_client:
        raise ValueError(
            "blind-quality and inheritance-fidelity reviewers must be separate clients"
        )

    candidate = composition.candidate_markdown
    blind_input = BlindQualityReviewInputV1(
        org_repo=graph.org_repo,
        original_readme_text=source_text,
        candidate_readme_text=candidate,
        candidate_sha256=composition.candidate_sha256,
        rubric_version="2",
    )
    blind_error: str | None = None
    try:
        blind_result_raw, blind_history, blind_grounding = run_grounded_role(
            role="blind_quality",
            prompt_id=_BLIND_PROMPT_ID,
            client=blind_client,
            messages=build_blind_quality_review_messages(graph.org_repo, source_text, candidate),
            candidate_text=candidate,
            product_facts=None,
        )
        if not isinstance(blind_result_raw, BlindQualityReviewResultV1):
            raise TypeError("blind reviewer returned the wrong typed result")
    except (LLMError, TypeError, ValueError) as exc:
        blind_result_raw = None
        blind_history = []
        blind_grounding = None
        blind_error = str(exc)
    fidelity_payload = {
        "org_repo": graph.org_repo,
        "fact_graph": graph.model_dump(mode="json"),
        "transform_plan": composition.plan.model_dump(mode="json"),
        "candidate_sha256": composition.candidate_sha256,
    }
    fidelity_error: str | None = None
    try:
        fidelity_result, fidelity_history = run_trusted_fidelity_role(
            client=fidelity_client,
            messages=build_trusted_fidelity_review_messages(
                graph.org_repo,
                _canonical_json(graph.model_dump(mode="json")),
                _canonical_json(composition.plan.model_dump(mode="json")),
                candidate,
            ),
            graph=graph,
            candidate_text=candidate,
        )
    except (LLMError, TypeError, ValueError) as exc:
        fidelity_result = None
        fidelity_history = ()
        fidelity_error = str(exc)
    author = _identity(
        "llm-route:trusted-readme-author",
        "author",
        _AUTHOR_PROMPT_ID,
        env.llm_model_for_job(_AUTHOR_PROMPT_ID),
    )
    blind_actor = _identity(
        "llm-route:blind-readme-quality",
        "blind_quality_reviewer",
        _BLIND_PROMPT_ID,
        env.llm_model_for_job(_BLIND_PROMPT_ID),
    )
    fidelity_actor = _identity(
        "llm-route:trusted-readme-fidelity",
        "inheritance_fidelity_reviewer",
        _FIDELITY_PROMPT_ID,
        env.llm_model_for_job(_FIDELITY_PROMPT_ID),
    )
    blind_record = TrustedReviewRoleRecordV1(
        identity=blind_actor,
        candidate_sha256=composition.candidate_sha256,
        input_sha256=input_hash(blind_input),
        verdict=blind_result_raw.verdict if blind_result_raw is not None else "SYSTEM_FAILURE",
        result=(
            {
                **blind_result_raw.model_dump(mode="json"),
                "grounding_validation": blind_grounding.model_dump(mode="json"),
                "retry_history": blind_history,
            }
            if blind_result_raw is not None and blind_grounding is not None
            else {
                "verdict": "SYSTEM_FAILURE",
                "reasoning": blind_error or "blind reviewer failed",
                "failed_criteria": [],
                "sections_affected": [],
                "required_repair": "",
                "findings": [],
                "grounding_validation": None,
                "retry_history": blind_history,
            }
        ),
    )
    fidelity_record = TrustedReviewRoleRecordV1(
        identity=fidelity_actor,
        candidate_sha256=composition.candidate_sha256,
        input_sha256=canonical_hash(fidelity_payload),
        verdict=fidelity_result.verdict if fidelity_result is not None else "SYSTEM_FAILURE",
        result=(
            {
                **fidelity_result.model_dump(mode="json"),
                "retry_history": fidelity_history,
            }
            if fidelity_result is not None
            else {
                "verdict": "SYSTEM_FAILURE",
                "reasoning": fidelity_error or "inheritance-fidelity reviewer failed",
                "source_checks": [],
                "unsupported_additions": [],
                "failed_criteria": [],
                "sections_affected": [],
                "required_repair": "",
                "retry_history": fidelity_history,
            }
        ),
    )
    identities_valid = (
        len({author.actor_id, blind_actor.actor_id, fidelity_actor.actor_id}) == 3
        and len({author.prompt_sha256, blind_actor.prompt_sha256, fidelity_actor.prompt_sha256})
        == 3
    )
    verdicts = {blind_record.verdict, fidelity_record.verdict}
    verdict: TrustedTransformVerdictV1 = (
        "SYSTEM_FAILURE"
        if not identities_valid or "SYSTEM_FAILURE" in verdicts
        else (
            "REJECT_REPAIRABLE" if "REJECT_REPAIRABLE" in verdicts else "TRUSTED_TRANSFORM_APPROVED"
        )
    )
    review = TrustedTransformReviewV1(
        org_repo=graph.org_repo,
        candidate_sha256=composition.candidate_sha256,
        validation=validation,
        author=author,
        blind_quality=blind_record,
        inheritance_fidelity=fidelity_record,
        identity_separation_valid=identities_valid,
        verdict=verdict,
        reasons=(
            f"blind_quality:{blind_record.verdict}",
            f"inheritance_fidelity:{fidelity_record.verdict}",
        ),
        cache_identity=identity,
        cache_identity_sha256=identity.canonical_hash(),
    )
    after = current_llm_accounting_summary()
    return _execution(review, False, before, after)


def _execution(
    review: TrustedTransformReviewV1,
    reused: bool,
    before: LlmAccountingSummaryV1,
    after: LlmAccountingSummaryV1,
) -> TrustedReviewExecutionV1:
    if after.status != "EXACT" or after.ledger_path is None or after.ledger_sha256 is None:
        raise RuntimeError("trusted review call ledger is missing or incomplete")
    return TrustedReviewExecutionV1(
        review=review,
        cache_reused=reused,
        provider_calls_before=before.provider_call_count or 0,
        provider_calls_after=after.provider_call_count or 0,
        fixture_calls_before=before.fixture_call_count or 0,
        fixture_calls_after=after.fixture_call_count or 0,
        cache_reuses_before=before.cache_reuse_count or 0,
        cache_reuses_after=after.cache_reuse_count or 0,
        ledger_path=after.ledger_path,
        ledger_sha256=after.ledger_sha256,
        provider_call_ids=tuple(after.call_ids),
        calls_by_job=after.calls_by_job,
        prompt_tokens=after.prompt_tokens,
        completion_tokens=after.completion_tokens,
        total_tokens=after.total_tokens,
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
