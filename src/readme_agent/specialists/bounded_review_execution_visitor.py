"""Execute one visitor-facing bounded review packet."""

from __future__ import annotations

from collections.abc import Callable

from readme_agent.specialists.bounded_review_execution_cache import (
    BoundedReviewPacketCache,
    PacketExecution,
)
from readme_agent.specialists.bounded_review_execution_contracts import (
    build_bounded_packet_result,
    canonical_review_json,
    project_bounded_role_result,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.bounded_review_packets import (
    BoundedReviewPlanV1,
    BoundedVisitorPacketV1,
    validate_packet_result,
)
from readme_agent.specialists.bounded_review_visitor_scope import (
    bounded_visitor_contract,
    bounded_visitor_scope,
)
from readme_agent.specialists.readme_review_roles import BlindQualityReviewResultV1
from readme_agent.specialists.review_finding_grounding import (
    BLIND_GROUNDING_CONTRACT_VERSION,
    validate_review_findings,
)
from readme_agent.specialists.review_role_execution import (
    AnalysisClientLike,
    reconcile_deterministically_disproven_blind_findings,
)
from readme_agent.specialists.review_standard_premises import (
    REVIEW_STANDARD_PREMISE_CONTRACT_VERSION,
)


def execute_visitor_packet(
    *,
    org_repo: str,
    candidate_text: str,
    visitor_contract: dict,
    plan: BoundedReviewPlanV1,
    packet: BoundedVisitorPacketV1,
    client: AnalysisClientLike,
    prompt_id: str,
    cache: BoundedReviewPacketCache,
    build_messages: Callable[..., object],
    run_role: Callable[..., tuple],
) -> PacketExecution:
    """Execute or safely reuse one visitor packet under scoped authority."""

    bounded_scope = bounded_visitor_scope(
        packet.section_path,
        neighbor_context_before=packet.neighbor_context_before,
        neighbor_context_after=packet.neighbor_context_after,
    )
    scoped_contract = bounded_visitor_contract(visitor_contract, packet.section_path)
    authority_hash = _canonical_hash(
        {
            "blind_grounding_contract_version": BLIND_GROUNDING_CONTRACT_VERSION,
            "review_standard_premise_contract_version": REVIEW_STANDARD_PREMISE_CONTRACT_VERSION,
            "bounded_scope": bounded_scope,
            "scoped_visitor_contract": scoped_contract,
        }
    )
    cached = cache.load(packet, runtime_contract_hash=authority_hash)
    if cached is not None:
        cached_result, cached_history = cached
        role_result = project_bounded_role_result([cached_result], facet="visitor")
        assert isinstance(role_result, BlindQualityReviewResultV1)
        grounding = validate_review_findings(
            candidate_text=candidate_text,
            product_facts=None,
            findings=role_result.findings,
            visitor_contract=scoped_contract,
        )
        normalized, dismissed = reconcile_deterministically_disproven_blind_findings(
            role_result,
            list(grounding.errors),
        )
        if dismissed:
            assert isinstance(normalized, BlindQualityReviewResultV1)
            cached_result = cached_result.model_copy(
                update={
                    "verdict": normalized.verdict,
                    "reasoning": normalized.reasoning,
                    "failed_criteria": tuple(normalized.failed_criteria),
                    "required_repair": normalized.required_repair,
                    "findings": tuple(normalized.findings),
                }
            )
            cached_history = (
                *cached_history,
                {
                    "role": "blind_quality",
                    "attempt": 0,
                    "context_mode": "deterministic_cached_result_reconciliation",
                    "valid": True,
                    "errors": [],
                    "pre_normalization_errors": list(grounding.errors),
                    "deterministically_dismissed_finding_ids": list(dismissed),
                    "packet_id": packet.packet_id,
                },
            )
            cache.persist(
                packet,
                cached_result,
                cached_history,
                runtime_contract_hash=authority_hash,
            )
        return cached_result, cached_history

    allowed_checks = frozenset(bounded_scope["applicable_mechanical_check_ids"])
    messages = build_messages(
        org_repo,
        "",
        packet.section_text,
        canonical_review_json(scoped_contract),
        canonical_review_json(bounded_scope),
        mechanical_candidate_text=candidate_text,
        allowed_mechanical_check_ids=allowed_checks,
    )
    result, attempts, _grounding = run_role(
        role="blind_quality",
        prompt_id=prompt_id,
        client=client,
        messages=messages,
        candidate_text=packet.section_text,
        product_facts=None,
        visitor_contract=scoped_contract,
        allowed_quality_criteria=frozenset(bounded_scope["applicable_criteria"]),
        allowed_mechanical_check_ids=allowed_checks,
        failure_context=packet.packet_id,
        mechanical_candidate_text=candidate_text,
        mechanical_visitor_contract=visitor_contract,
    )
    assert isinstance(result, BlindQualityReviewResultV1)
    bounded = build_bounded_packet_result(packet, result)
    validation = validate_packet_result(plan, bounded)
    if not validation.valid:
        raise RuntimeError(f"invalid bounded visitor result: {validation.errors}")
    history = tuple({**item, "packet_id": packet.packet_id} for item in attempts)
    cache.persist(packet, bounded, history, runtime_contract_hash=authority_hash)
    return bounded, history


__all__ = ["execute_visitor_packet"]
