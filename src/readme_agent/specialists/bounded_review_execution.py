"""Execute bounded README review packets through the existing grounded role clients."""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.llm.call_ledger import record_non_provider_call
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.specialists.bounded_review_cache import (
    BoundedReviewCacheContextV1,
    cache_key_for_packet,
    load_bounded_review_packet_cache,
    write_bounded_review_packet_cache,
)
from readme_agent.specialists.bounded_review_packets import (
    AggregateVerdictV1,
    BoundedFactualPacketV1,
    BoundedPacketResultV1,
    BoundedReviewPlanV1,
    BoundedVisitorPacketV1,
    CoverageLedgerV1,
    aggregate_packet_results,
    validate_packet_result,
)
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewResultV1,
    FactualPlanReviewResultV1,
)
from readme_agent.specialists.review_finding_grounding import (
    FindingGroundingResultV1,
    GroundedReviewFindingV1,
    validate_review_findings,
)
from readme_agent.specialists.review_role_execution import (
    AnalysisClientLike,
    normalize_redundant_role_fields,
    run_grounded_role,
)


class BoundedReviewExecutionV1(BaseModel):
    """Complete packet execution and its projection into the established role contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: BoundedReviewPlanV1
    coverage_ledger: CoverageLedgerV1
    packet_results: tuple[BoundedPacketResultV1, ...]
    aggregate: AggregateVerdictV1
    blind_result: BlindQualityReviewResultV1
    factual_result: FactualPlanReviewResultV1
    blind_grounding: FindingGroundingResultV1
    factual_grounding: FindingGroundingResultV1
    grounding_history: tuple[dict, ...] = ()


def _normalized_findings(
    packet_id: str,
    section_path: str,
    findings: Sequence[GroundedReviewFindingV1],
) -> list[GroundedReviewFindingV1]:
    prefix = packet_id.replace("-", ".")
    return [
        finding.model_copy(
            update={
                "finding_id": f"{prefix}.{finding.finding_id}",
                "section": section_path,
                "candidate_anchor_id": None,
            }
        )
        for finding in findings
    ]


def _bounded_result(
    packet: BoundedFactualPacketV1 | BoundedVisitorPacketV1,
    result: BlindQualityReviewResultV1 | FactualPlanReviewResultV1,
) -> BoundedPacketResultV1:
    findings = _normalized_findings(packet.packet_id, packet.section_path, result.findings)
    bounded = BoundedPacketResultV1(
        packet_id=packet.packet_id,
        facet=packet.facet,
        candidate_sha256=packet.candidate_sha256,
        packet_sha256=packet.packet_sha256,
        prompt_contract_hash=packet.prompt_contract_hash,
        input_contract_hash=packet.input_contract_hash,
        verdict=result.verdict,
        reasoning=result.reasoning,
        failed_criteria=tuple(result.failed_criteria),
        required_repair=result.required_repair,
        findings=tuple(findings),
    )
    return bounded


def _winning_verdict(
    results: Sequence[BoundedPacketResultV1],
    *,
    facet: Literal["visitor", "factual"],
) -> str:
    precedence = (
        "SYSTEM_FAILURE",
        "BLOCKED_FACT_CONFLICT",
        "BLOCKED_MISSING_EVIDENCE",
        "REJECT_REPAIRABLE",
        "ACCEPT",
    )
    allowed = {"SYSTEM_FAILURE", "REJECT_REPAIRABLE", "ACCEPT"}
    verdicts = {result.verdict for result in results}
    verdict = next(item for item in precedence if item in verdicts)
    if facet == "visitor" and verdict not in allowed:
        return "SYSTEM_FAILURE"
    return verdict


def _project_role_result(
    results: Sequence[BoundedPacketResultV1],
    *,
    facet: Literal["visitor", "factual"],
) -> BlindQualityReviewResultV1 | FactualPlanReviewResultV1:
    verdict = _winning_verdict(results, facet=facet)
    selected = [result for result in results if result.verdict == verdict]
    findings = [finding for result in selected for finding in result.findings]
    payload = normalize_redundant_role_fields(
        "blind_quality" if facet == "visitor" else "factual_plan",
        {
            "verdict": verdict,
            "reasoning": (
                f"Bounded {facet} review reduced {len(results)} packet result(s): "
                + "; ".join(result.reasoning for result in selected)
            ),
            "failed_criteria": [
                criterion for result in selected for criterion in result.failed_criteria
            ],
            "sections_affected": [finding.section for finding in findings],
            "required_repair": " ".join(
                result.required_repair for result in selected if result.required_repair.strip()
            ),
            "findings": [finding.model_dump(mode="json") for finding in findings],
        },
    )
    if facet == "visitor":
        return BlindQualityReviewResultV1.model_validate(payload)
    return FactualPlanReviewResultV1.model_validate(payload)


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

    def load_cached(packet):
        if cache_dir is None or cache_context is None:
            return None
        cache_key = cache_key_for_packet(packet, cache_context)
        cached = load_bounded_review_packet_cache(
            cache_dir,
            cache_key=cache_key,
            org_repo=org_repo,
            context=cache_context,
            packet=packet,
            plan=plan,
        )
        if cached is None:
            return None
        model, _schema_hash, _sampling = cache_context.identity_for(packet)
        prompt_id = blind_prompt_id if packet.facet == "visitor" else factual_prompt_id
        record_non_provider_call(
            job=prompt_id,
            prompt_id=prompt_id,
            prompt_sha256=packet.prompt_contract_hash,
            model=model,
            disposition="cache_reuse",
            request={"cache_key": cache_key, "packet_id": packet.packet_id},
        )
        history = (
            *cached.grounding_history,
            {
                "role": "blind_quality" if packet.facet == "visitor" else "factual_plan",
                "attempt": 0,
                "context_mode": "bounded_packet_cache_reuse",
                "valid": True,
                "errors": [],
                "packet_id": packet.packet_id,
                "cache_key": cache_key,
            },
        )
        return cached.result, history

    def persist(packet, result, history):
        if cache_dir is None or cache_context is None:
            return
        write_bounded_review_packet_cache(
            cache_dir,
            cache_key=cache_key_for_packet(packet, cache_context),
            org_repo=org_repo,
            context=cache_context,
            packet=packet,
            result=result,
            grounding_history=history,
        )

    def review_visitor(visitor_packet: BoundedVisitorPacketV1):
        cached = load_cached(visitor_packet)
        if cached is not None:
            return cached
        bounded_scope = {
            "mode": "target_section_only",
            "target_section_path": visitor_packet.section_path,
            "finding_evidence_scope": "target_section_anchors_only",
            "neighbor_context_before": visitor_packet.neighbor_context_before,
            "neighbor_context_after": visitor_packet.neighbor_context_after,
        }
        messages = build_blind_quality_review_messages(
            org_repo,
            "",
            visitor_packet.section_text,
            _canonical_json(visitor_contract),
            _canonical_json(bounded_scope),
        )
        result, attempts, _grounding = run_grounded_role(
            role="blind_quality",
            prompt_id=blind_prompt_id,
            client=blind_client,
            messages=messages,
            candidate_text=visitor_packet.section_text,
            product_facts=None,
            visitor_contract=visitor_contract,
        )
        assert isinstance(result, BlindQualityReviewResultV1)
        bounded = _bounded_result(visitor_packet, result)
        validation = validate_packet_result(plan, bounded)
        if not validation.valid:
            raise RuntimeError(f"invalid bounded visitor result: {validation.errors}")
        history = tuple({**item, "packet_id": visitor_packet.packet_id} for item in attempts)
        persist(visitor_packet, bounded, history)
        return bounded, history

    def review_factual(factual_packet: BoundedFactualPacketV1):
        cached = load_cached(factual_packet)
        if cached is not None:
            return cached
        fact_context = {
            "facts": list(factual_packet.facts),
            "do_not_claim": list(factual_packet.do_not_claim),
            "accepted_fact_ids": list(factual_packet.accepted_fact_ids),
        }
        plan_context = {
            "section_path": factual_packet.section_path,
            "claim_ids": list(factual_packet.claim_ids),
            "provenance_ids": list(factual_packet.provenance_ids),
        }
        messages = build_factual_plan_review_messages(
            org_repo,
            factual_packet.unit_text,
            _canonical_json(fact_context),
            _canonical_json(plan_context),
        )
        result, attempts, _grounding = run_grounded_role(
            role="factual_plan",
            prompt_id=factual_prompt_id,
            client=factual_client,
            messages=messages,
            candidate_text=factual_packet.unit_text,
            product_facts=product_facts,
        )
        assert isinstance(result, FactualPlanReviewResultV1)
        bounded = _bounded_result(factual_packet, result)
        validation = validate_packet_result(plan, bounded)
        if not validation.valid:
            raise RuntimeError(f"invalid bounded factual result: {validation.errors}")
        history = tuple({**item, "packet_id": factual_packet.packet_id} for item in attempts)
        persist(factual_packet, bounded, history)
        return bounded, history

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

    by_id = {result.packet_id: result for result in packet_results}
    aggregate = aggregate_packet_results(plan, coverage_ledger, by_id)
    if aggregate.overall not in {"ACCEPT", "REJECTED"}:
        raise RuntimeError(f"bounded review did not converge: {aggregate.overall}")

    visitor_results = [result for result in packet_results if result.facet == "visitor"]
    factual_results = [result for result in packet_results if result.facet == "factual"]
    blind = _project_role_result(visitor_results, facet="visitor")
    factual = _project_role_result(factual_results, facet="factual")
    assert isinstance(blind, BlindQualityReviewResultV1)
    assert isinstance(factual, FactualPlanReviewResultV1)
    blind_grounding = validate_review_findings(
        candidate_text=candidate_text,
        product_facts=None,
        findings=blind.findings,
        visitor_contract=visitor_contract,
    )
    factual_grounding = validate_review_findings(
        candidate_text=candidate_text,
        product_facts=product_facts,
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


def _canonical_json(value: dict) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


__all__ = ["BoundedReviewExecutionV1", "execute_bounded_review"]
