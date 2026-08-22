"""Run context-isolated quality and factual README reviews and reduce their verdicts."""

from __future__ import annotations

import json
from typing import cast

from pydantic import ValidationError

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.capabilities.schema import PermissionClass
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm import prompt_registry
from readme_agent.llm.merged_readme_review import (
    MAX_MERGED_REVIEW_REQUEST_BYTES,
    build_merged_readme_review_messages,
    merged_review_request_size_bytes,
)
from readme_agent.llm.reviewer_client import (
    build_live_merged_review_client,
    build_live_role_review_clients,
)
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.presentation.visitor_contract import build_presentation_visitor_contract
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_structure import parse_headings
from readme_agent.specialists.bounded_review_contracts import (
    DEFAULT_BOUNDED_PACKET_BUDGET_CHARS,
)
from readme_agent.specialists.bounded_review_execution import execute_bounded_review
from readme_agent.specialists.bounded_review_packets import (
    build_atomic_units,
    build_coverage_ledger,
    plan_bounded_review_packets,
)
from readme_agent.specialists.factual_review_packet import build_factual_review_packet
from readme_agent.specialists.independent_readme_review import (
    record_review_verdict,
)
from readme_agent.specialists.merged_readme_review import execute_merged_readme_review
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
_BOUNDED_REVIEW_TRIGGER_CHARS = 240_000
_BOUNDED_REVIEW_MAX_WORKERS = 4


def _role_identity(actor_id: str, role: ReviewRole, prompt_id: str) -> ReviewActorIdentityV1:
    return ReviewActorIdentityV1(
        actor_id=actor_id,
        role=role,
        prompt_id=prompt_id,
        prompt_sha256=prompt_registry.prompt_hash(prompt_id),
    )


def _primary_example_language(product_facts: dict) -> str | None:
    fact_id = (product_facts.get("selected_fact_ids") or {}).get("example.minimal")
    fact = next(
        (
            item
            for item in product_facts.get("facts") or []
            if isinstance(item, dict) and item.get("fact_id") == fact_id
        ),
        None,
    )
    value = fact.get("value") if isinstance(fact, dict) else None
    language = value.get("language") if isinstance(value, dict) else None
    return str(language).strip().casefold() or None if language is not None else None


def run_separated_readme_review(
    org_repo: str,
    original_readme_text: str,
    candidate_readme_text: str,
    presentation_plan: dict,
    product_facts_v2: dict | None,
    *,
    blind_client: AnalysisClientLike | None = None,
    factual_client: AnalysisClientLike | None = None,
    merged_client: AnalysisClientLike | None = None,
    blind_fallback_client: AnalysisClientLike | None = None,
    factual_fallback_client: AnalysisClientLike | None = None,
    backend: StateBackend | None = None,
    repair_attempt: int = 0,
    author_identity: ReviewActorIdentityV1 | None = None,
) -> SeparatedReadmeReviewResultV1:
    """Run one merged review by default, retaining explicit separated compatibility."""

    if (blind_client is None) != (factual_client is None):
        raise ValueError("blind and factual review clients must be supplied together")
    explicit_separated = blind_client is not None and factual_client is not None
    if explicit_separated and merged_client is not None:
        raise ValueError("merged and separated review clients are mutually exclusive")
    if explicit_separated and (
        blind_fallback_client is not None or factual_fallback_client is not None
    ):
        raise ValueError("a review fallback client is only valid with the merged reviewer")
    if not explicit_separated and merged_client is None:
        merged_client = build_live_merged_review_client(env.llm_base_url(), env.llm_api_key())
        blind_fallback_client, factual_fallback_client = build_live_role_review_clients(
            env.llm_base_url(), env.llm_api_key()
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
    applicable_h2_headings = [
        heading.title for heading in parse_headings(candidate_readme_text) if heading.level == 2
    ]
    visitor_contract = build_presentation_visitor_contract(
        applicable_h2_headings=applicable_h2_headings,
        primary_example_language=_primary_example_language(product_facts_v2),
    )
    factual_packet = build_factual_review_packet(
        org_repo,
        candidate_readme_text,
        product_facts_v2,
        presentation_plan,
    )
    factual_packet_payload = factual_packet.model_dump(mode="json")
    blind_input = BlindQualityReviewInputV1(
        org_repo=org_repo,
        original_readme_text=original_readme_text,
        candidate_readme_text=candidate_readme_text,
        candidate_sha256=candidate_sha256,
        rubric_version="1",
        visitor_contract=visitor_contract,
    )
    factual_input = FactualPlanReviewInputV1(
        org_repo=org_repo,
        candidate_readme_text=candidate_readme_text,
        candidate_sha256=candidate_sha256,
        product_facts=product_facts_v2,
        product_facts_sha256=json_hash(product_facts_v2),
        presentation_plan=presentation_plan,
        presentation_plan_sha256=json_hash(presentation_plan),
        review_packet=factual_packet_payload,
        review_packet_sha256=json_hash(factual_packet_payload),
        rubric_version="1",
    )

    bounded_context_chars = (
        len(candidate_readme_text)
        + len(_canonical_json(factual_packet.fact_context()))
        + len(_canonical_json(factual_packet.plan_context()))
    )
    merged_messages = build_merged_readme_review_messages(
        org_repo,
        candidate_readme_text,
        _canonical_json(visitor_contract),
        _canonical_json(factual_packet.fact_context()),
        _canonical_json(factual_packet.plan_context()),
    )
    merged_request_too_large = (
        merged_review_request_size_bytes(merged_messages) > MAX_MERGED_REVIEW_REQUEST_BYTES
    )
    bounded_execution = None
    document_plan = None
    facts_model = None
    canonical_bounded_contract = (
        "readme_document_plan" in presentation_plan or "claim_accountability" in presentation_plan
    )
    if (
        bounded_context_chars > _BOUNDED_REVIEW_TRIGGER_CHARS or merged_request_too_large
    ) and canonical_bounded_contract:
        document_plan_payload = presentation_plan.get("readme_document_plan") or presentation_plan
        try:
            document_plan = ReadmeDocumentPlanV1.model_validate(document_plan_payload)
            facts_model = ProductFactsV2.model_validate(product_facts_v2)
        except ValidationError as exc:
            raise RuntimeError(
                "oversized review requires valid typed document-plan and product-facts contracts"
            ) from exc
        if document_plan is not None and document_plan.claim_accountability is None:
            raise RuntimeError("bounded review requires the validated claim-accountability map")
    if document_plan is not None and facts_model is not None:
        assert document_plan.claim_accountability is not None
        bounded_plan = plan_bounded_review_packets(
            candidate_text=candidate_readme_text,
            document_plan=document_plan,
            claim_accountability=document_plan.claim_accountability,
            product_facts=facts_model,
            budget_chars=DEFAULT_BOUNDED_PACKET_BUDGET_CHARS,
            factual_prompt_sha256=prompt_registry.prompt_hash(_FACTUAL_PROMPT_ID),
            visitor_prompt_sha256=prompt_registry.prompt_hash(_BLIND_PROMPT_ID),
            candidate_content_provenance=document_plan.candidate_content_provenance,
        )
        atomic_units = build_atomic_units(
            candidate_readme_text,
            document_plan.claim_accountability,
            facts_model,
            document_plan.candidate_content_provenance,
        )
        coverage_ledger = build_coverage_ledger(bounded_plan, atomic_units=atomic_units)
        bounded_blind_client = blind_client or blind_fallback_client
        bounded_factual_client = factual_client or factual_fallback_client
        if bounded_blind_client is None or bounded_factual_client is None:
            raise RuntimeError("bounded review requires independent blind and factual role clients")
        bounded_execution = execute_bounded_review(
            org_repo=org_repo,
            candidate_text=candidate_readme_text,
            product_facts=product_facts_v2,
            visitor_contract=visitor_contract,
            plan=bounded_plan,
            coverage_ledger=coverage_ledger,
            blind_client=bounded_blind_client,
            factual_client=bounded_factual_client,
            blind_prompt_id=_BLIND_PROMPT_ID,
            factual_prompt_id=_FACTUAL_PROMPT_ID,
            max_workers=(1 if explicit_separated else _BOUNDED_REVIEW_MAX_WORKERS),
        )

    if bounded_execution is not None:
        blind_result = bounded_execution.blind_result
        factual_result = bounded_execution.factual_result
        blind_grounding = bounded_execution.blind_grounding
        factual_grounding = bounded_execution.factual_grounding
        grounding_history = list(bounded_execution.grounding_history)
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
        merged_call_receipt = None
        review_recovery_receipt = None
    elif explicit_separated:
        assert blind_client is not None and factual_client is not None
        raw_blind_result, blind_retry_history, blind_grounding = run_grounded_role(
            role="blind_quality",
            prompt_id=_BLIND_PROMPT_ID,
            client=blind_client,
            messages=build_blind_quality_review_messages(
                blind_input.org_repo,
                blind_input.original_readme_text,
                blind_input.candidate_readme_text,
                _canonical_json(blind_input.visitor_contract),
            ),
            candidate_text=candidate_readme_text,
            product_facts=None,
            visitor_contract=blind_input.visitor_contract,
        )
        raw_factual_result, factual_retry_history, factual_grounding = run_grounded_role(
            role="factual_plan",
            prompt_id=_FACTUAL_PROMPT_ID,
            client=factual_client,
            messages=build_factual_plan_review_messages(
                factual_input.org_repo,
                factual_input.candidate_readme_text,
                _canonical_json(factual_packet.fact_context()),
                _canonical_json(factual_packet.plan_context()),
            ),
            candidate_text=candidate_readme_text,
            product_facts=product_facts_v2,
        )
        blind_result = cast(BlindQualityReviewResultV1, raw_blind_result)
        factual_result = cast(FactualPlanReviewResultV1, raw_factual_result)
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
        merged_call_receipt = None
        review_recovery_receipt = None
        grounding_history = [*blind_retry_history, *factual_retry_history]
    else:
        assert merged_client is not None
        execution = execute_merged_readme_review(
            org_repo=org_repo,
            candidate_text=candidate_readme_text,
            visitor_contract=blind_input.visitor_contract,
            fact_context=factual_packet.fact_context(),
            plan_context=factual_packet.plan_context(),
            product_facts=product_facts_v2,
            blind_input=blind_input,
            factual_input=factual_input,
            client=merged_client,
            blind_fallback_client=blind_fallback_client,
            factual_fallback_client=factual_fallback_client,
        )
        blind_result = execution.blind_result
        factual_result = execution.factual_result
        blind_record = execution.blind_record
        factual_record = execution.factual_record
        merged_call_receipt = execution.receipt
        review_recovery_receipt = execution.recovery_receipt
        grounding_history = execution.grounding_history
    author = author_identity or _role_identity(
        "producer:readme-composition",
        "author",
        _AUTHOR_PROMPT_ID,
    )
    combined = combine_review_verdicts(
        author=author,
        blind_quality=blind_record,
        factual_plan=factual_record,
        merged_call_receipt=merged_call_receipt,
    )
    review = build_compatibility_result(
        blind_result,
        factual_result,
        blind_record,
        factual_record,
        combined,
        grounding_history,
        review_recovery_receipt,
        (bounded_execution.model_dump(mode="json") if bounded_execution is not None else None),
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
