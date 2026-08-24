"""Orchestrate bounded README review packet execution and aggregation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path

from readme_agent.llm.call_ledger import record_non_provider_call
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.specialists.bounded_review_cache import BoundedReviewCacheContextV1
from readme_agent.specialists.bounded_review_execution_cache import BoundedReviewPacketCache
from readme_agent.specialists.bounded_review_execution_contracts import (
    BoundedReviewExecutionV1,
    project_bounded_role_result,
)
from readme_agent.specialists.bounded_review_execution_factual import (
    execute_factual_packet,
    product_facts_with_packet_evidence_locations,
)
from readme_agent.specialists.bounded_review_execution_visitor import execute_visitor_packet
from readme_agent.specialists.bounded_review_packets import (
    BoundedReviewPlanV1,
    CoverageLedgerV1,
    aggregate_packet_results,
)
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_finding_grounding import validate_review_findings
from readme_agent.specialists.review_role_execution import AnalysisClientLike, run_grounded_role


def execute_bounded_review(
    *,
    org_repo: str,
    candidate_text: str,
    product_facts: dict,
    visitor_contract: dict,
    plan: BoundedReviewPlanV1,
    coverage_ledger: CoverageLedgerV1,
    blind_client: AnalysisClientLike,
    factual_client: AnalysisClientLike,
    blind_prompt_id: str,
    factual_prompt_id: str,
    max_workers: int = 1,
    cache_dir: Path | None = None,
    cache_context: BoundedReviewCacheContextV1 | None = None,
) -> BoundedReviewExecutionV1:
    """Review every required packet, validate containment, and reduce fail closed."""

    if max_workers < 1 or max_workers > 4:
        raise ValueError("bounded review max_workers must be between 1 and 4")
    if (cache_dir is None) != (cache_context is None):
        raise ValueError("bounded review cache directory and context must be supplied together")
    if plan.unpacketizable:
        aggregate = aggregate_packet_results(plan, coverage_ledger, {})
        raise RuntimeError(
            f"bounded review is structurally blocked: {aggregate.blocking_record_ids}"
        )

    cache = BoundedReviewPacketCache(
        org_repo=org_repo,
        plan=plan,
        cache_dir=cache_dir,
        context=cache_context,
        blind_prompt_id=blind_prompt_id,
        factual_prompt_id=factual_prompt_id,
        record_cache_reuse=record_non_provider_call,
    )

    def review_visitor(packet):
        return execute_visitor_packet(
            org_repo=org_repo,
            candidate_text=candidate_text,
            visitor_contract=visitor_contract,
            plan=plan,
            packet=packet,
            client=blind_client,
            prompt_id=blind_prompt_id,
            cache=cache,
            build_messages=build_blind_quality_review_messages,
            run_role=run_grounded_role,
        )

    def review_factual(packet):
        return execute_factual_packet(
            org_repo=org_repo,
            product_facts=product_facts,
            plan=plan,
            packet=packet,
            client=factual_client,
            prompt_id=factual_prompt_id,
            cache=cache,
            build_messages=build_factual_plan_review_messages,
            run_role=run_grounded_role,
        )

    if max_workers == 1:
        completed = [review_visitor(packet) for packet in plan.visitor_packets]
        completed.extend(review_factual(packet) for packet in plan.factual_packets)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            visitor_futures = [
                executor.submit(copy_context().run, review_visitor, packet)
                for packet in plan.visitor_packets
            ]
            factual_futures = [
                executor.submit(copy_context().run, review_factual, packet)
                for packet in plan.factual_packets
            ]
            completed = [future.result() for future in visitor_futures]
            completed.extend(future.result() for future in factual_futures)

    packet_results = [result for result, _history in completed]
    history = [item for _result, attempts in completed for item in attempts]
    aggregate = aggregate_packet_results(
        plan,
        coverage_ledger,
        {result.packet_id: result for result in packet_results},
    )
    if aggregate.overall not in {"ACCEPT", "REJECTED"}:
        raise RuntimeError(f"bounded review did not converge: {aggregate.overall}")

    blind = project_bounded_role_result(
        [result for result in packet_results if result.facet == "visitor"],
        facet="visitor",
    )
    factual = project_bounded_role_result(
        [result for result in packet_results if result.facet == "factual"],
        facet="factual",
    )
    assert isinstance(blind, BlindQualityReviewResultV1)
    assert isinstance(factual, FactualPlanReviewResultV1)
    blind_grounding = validate_review_findings(
        candidate_text=candidate_text,
        product_facts=None,
        findings=blind.findings,
        visitor_contract=visitor_contract,
    )
    aggregate_product_facts = product_facts_with_packet_evidence_locations(
        product_facts,
        plan.factual_packets,
    )
    factual_grounding = validate_review_findings(
        candidate_text=candidate_text,
        product_facts=aggregate_product_facts,
        findings=factual.findings,
    )
    if not blind_grounding.valid or not factual_grounding.valid:
        raise RuntimeError(
            "bounded aggregate grounding failed: "
            f"blind={blind_grounding.errors}; factual={factual_grounding.errors}"
        )
    return BoundedReviewExecutionV1(
        plan=plan,
        coverage_ledger=coverage_ledger,
        packet_results=tuple(packet_results),
        aggregate=aggregate,
        blind_result=blind,
        factual_result=factual,
        blind_grounding=blind_grounding,
        factual_grounding=factual_grounding,
        grounding_history=tuple(history),
    )


__all__ = ["BoundedReviewExecutionV1", "execute_bounded_review"]
