"""Execute one factual bounded review packet."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from readme_agent.specialists.bounded_review_cache import BoundedReviewPacketCacheV1
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
from readme_agent.specialists.bounded_review_mechanical_facts import (
    MECHANICAL_FACTUAL_HEADING_CONTRACT_VERSION,
    mechanical_factual_heading_review,
)
from readme_agent.specialists.bounded_review_packets import (
    BoundedFactualPacketV1,
    BoundedPacketResultV1,
    BoundedReviewPlanV1,
    validate_packet_result,
)
from readme_agent.specialists.readme_review_roles import FactualPlanReviewResultV1
from readme_agent.specialists.review_factual_reconciliation import (
    FACTUAL_RECONCILIATION_CONTRACT_VERSION,
)
from readme_agent.specialists.review_finding_grounding import (
    BLIND_GROUNDING_CONTRACT_VERSION,
    GROUNDING_RETRY_CONTEXT_CONTRACT_VERSION,
    validate_review_findings,
)
from readme_agent.specialists.review_role_execution import AnalysisClientLike

BOUNDED_FACTUAL_GROUNDING_ATTEMPTS = 3


def product_facts_with_packet_evidence_locations(
    product_facts: dict,
    packets: Iterable[BoundedFactualPacketV1],
) -> dict:
    """Use each fact's checksum-bound packet location consistently across review stages."""

    locations_by_fact_id: dict[str, str] = {}
    for candidate_packet in packets:
        for fact in candidate_packet.facts:
            if not isinstance(fact, dict) or not fact.get("fact_id"):
                continue
            source = fact.get("source")
            location = source.get("location") if isinstance(source, dict) else None
            if not isinstance(location, str) or not location:
                continue
            fact_id = str(fact["fact_id"])
            prior = locations_by_fact_id.setdefault(fact_id, location)
            if prior != location:
                raise RuntimeError(
                    f"bounded factual packets disagree on evidence location for {fact_id}"
                )

    projected_facts = []
    for fact in product_facts.get("facts", []):
        if not isinstance(fact, dict):
            projected_facts.append(fact)
            continue
        location = locations_by_fact_id.get(str(fact.get("fact_id")))
        if location is None:
            projected_facts.append(fact)
            continue
        source = fact.get("source")
        projected_source = dict(source) if isinstance(source, dict) else {}
        projected_source["location"] = location
        projected_facts.append({**fact, "source": projected_source})
    return {**product_facts, "facts": projected_facts}


def execute_factual_packet(
    *,
    org_repo: str,
    product_facts: dict,
    plan: BoundedReviewPlanV1,
    packet: BoundedFactualPacketV1,
    client: AnalysisClientLike,
    prompt_id: str,
    cache: BoundedReviewPacketCache,
    build_messages: Callable[..., object],
    run_role: Callable[..., tuple],
) -> PacketExecution:
    """Execute or safely reuse one factual packet under fact-scoped authority."""

    packet_fact_ids = set(packet.accepted_fact_ids)
    packet_product_facts = product_facts_with_packet_evidence_locations(
        {
            **product_facts,
            "selected_fact_ids": {
                field: fact_id
                for field, fact_id in product_facts.get("selected_fact_ids", {}).items()
                if fact_id in packet_fact_ids
            },
            "facts": [
                fact
                for fact in product_facts.get("facts", [])
                if isinstance(fact, dict) and fact.get("fact_id") in packet_fact_ids
            ],
        },
        (packet,),
    )
    mechanical_result = mechanical_factual_heading_review(packet, packet_product_facts)
    descendant_section_paths = sorted(
        {
            candidate.section_path
            for candidate in plan.factual_packets
            if candidate.section_path.startswith(f"{packet.section_path}/")
        }
    )
    runtime_contract = {
        "finding_grounding_contract_version": BLIND_GROUNDING_CONTRACT_VERSION,
        "factual_reconciliation_contract_version": FACTUAL_RECONCILIATION_CONTRACT_VERSION,
        "mechanical_contract_version": (
            MECHANICAL_FACTUAL_HEADING_CONTRACT_VERSION if mechanical_result is not None else None
        ),
    }
    if descendant_section_paths:
        runtime_contract["included_descendant_sections_sha256"] = _canonical_hash(
            descendant_section_paths
        )
    runtime_contract_hash = _canonical_hash(runtime_contract)

    def cached_result_is_grounded(result: BoundedPacketResultV1) -> bool:
        projected = project_bounded_role_result([result], facet="factual")
        assert isinstance(projected, FactualPlanReviewResultV1)
        grounding = validate_review_findings(
            candidate_text=packet.unit_text,
            product_facts=packet_product_facts,
            findings=projected.findings,
        )
        return grounding.valid

    def cached_retry_context_is_current(cached: BoundedReviewPacketCacheV1) -> bool:
        if cached.result.verdict != "BLOCKED_MISSING_EVIDENCE":
            return True
        compact_retries = [
            item
            for item in cached.grounding_history
            if item.get("context_mode") == "compact_grounding_retry"
        ]
        return not compact_retries or all(
            item.get("grounding_retry_context_contract_version")
            == GROUNDING_RETRY_CONTEXT_CONTRACT_VERSION
            for item in compact_retries
        )

    cached = cache.load(
        packet,
        runtime_contract_hash=runtime_contract_hash,
        validate_result=cached_result_is_grounded,
        validate_cache_entry=cached_retry_context_is_current,
    )
    if cached is not None:
        return cached
    if mechanical_result is not None:
        grounding = validate_review_findings(
            candidate_text=packet.unit_text,
            product_facts=packet_product_facts,
            findings=mechanical_result.findings,
        )
        if not grounding.valid:
            raise RuntimeError(f"invalid mechanical factual heading: {grounding.errors}")
        bounded = build_bounded_packet_result(packet, mechanical_result)
        validation = validate_packet_result(plan, bounded)
        if not validation.valid:
            raise RuntimeError(f"invalid bounded mechanical factual result: {validation.errors}")
        mechanical_history = (
            {
                "role": "factual_plan",
                "attempt": 0,
                "context_mode": "deterministic_structural_heading_grounding",
                "valid": True,
                "errors": [],
                "packet_id": packet.packet_id,
                "contract_version": MECHANICAL_FACTUAL_HEADING_CONTRACT_VERSION,
                "fact_id": mechanical_result.findings[0].fact_id,
            },
        )
        cache.persist(
            packet,
            bounded,
            mechanical_history,
            runtime_contract_hash=runtime_contract_hash,
        )
        return bounded, mechanical_history

    fact_context = {
        "facts": list(packet.facts),
        "do_not_claim": list(packet.do_not_claim),
        "accepted_fact_ids": list(packet.accepted_fact_ids),
    }
    plan_context = {
        "section_path": packet.section_path,
        "claim_ids": list(packet.claim_ids),
        "provenance_ids": list(packet.provenance_ids),
        "included_descendant_section_paths": descendant_section_paths,
    }
    messages = build_messages(
        org_repo,
        packet.unit_text,
        canonical_review_json(fact_context),
        canonical_review_json(plan_context),
    )
    result, attempts, _grounding = run_role(
        role="factual_plan",
        prompt_id=prompt_id,
        client=client,
        messages=messages,
        candidate_text=packet.unit_text,
        product_facts=packet_product_facts,
        max_attempts_override=BOUNDED_FACTUAL_GROUNDING_ATTEMPTS,
        failure_context=packet.packet_id,
    )
    assert isinstance(result, FactualPlanReviewResultV1)
    bounded = build_bounded_packet_result(packet, result)
    validation = validate_packet_result(plan, bounded)
    if not validation.valid:
        raise RuntimeError(f"invalid bounded factual result: {validation.errors}")
    history = tuple({**item, "packet_id": packet.packet_id} for item in attempts)
    cache.persist(packet, bounded, history, runtime_contract_hash=runtime_contract_hash)
    return bounded, history


__all__ = [
    "BOUNDED_FACTUAL_GROUNDING_ATTEMPTS",
    "execute_factual_packet",
    "product_facts_with_packet_evidence_locations",
]
