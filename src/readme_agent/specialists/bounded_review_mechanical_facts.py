"""Ground structural factual headings directly in accepted repository facts."""

from __future__ import annotations

import re

from readme_agent.readme.fact_grounding import fact_strings
from readme_agent.specialists.bounded_review_contracts import BoundedFactualPacketV1
from readme_agent.specialists.readme_review_roles import FactualPlanReviewResultV1
from readme_agent.specialists.review_finding_grounding import GroundedReviewFindingV1

MECHANICAL_FACTUAL_HEADING_CONTRACT_VERSION = "mechanical-factual-heading-v1"
_HEADING = re.compile(r"^#{1,6}[ \t]+(?P<title>[^\r\n]+)[ \t]*$")
_INLINE_CODE = re.compile(r"`([^`\r\n]+)`")


def mechanical_factual_heading_review(
    packet: BoundedFactualPacketV1,
    product_facts: dict,
) -> FactualPlanReviewResultV1 | None:
    """Accept a claim-free heading only when its code literal exactly matches a selected fact."""

    if packet.claim_ids:
        return None
    text = packet.unit_text.strip()
    if "\n" in text or _HEADING.fullmatch(text) is None:
        return None
    literals = tuple(dict.fromkeys(_INLINE_CODE.findall(text)))
    if not literals:
        return None

    accepted_ids = set(packet.accepted_fact_ids)
    selected_ids = set(product_facts.get("selected_fact_ids", {}).values())
    candidates: list[tuple[str, str, str]] = []
    for fact in product_facts.get("facts", []):
        if not isinstance(fact, dict):
            continue
        fact_id = str(fact.get("fact_id", ""))
        if fact_id not in accepted_ids or fact_id not in selected_ids:
            continue
        if fact.get("verification_state") not in {"verified", "policy_approved"}:
            continue
        if any(
            conflict.get("status") == "unresolved"
            for conflict in fact.get("conflicts", [])
            if isinstance(conflict, dict)
        ):
            continue
        source_location = str((fact.get("source") or {}).get("location", "")).strip()
        if not source_location:
            continue
        evidence = set(fact_strings(fact.get("value"))) | {
            str(item) for item in fact.get("protected_literals", []) if str(item).strip()
        }
        for literal in literals:
            if literal in evidence:
                candidates.append((fact_id, literal, source_location))

    if not candidates:
        return None
    fact_id, evidence_excerpt, evidence_location = sorted(candidates)[0]
    finding = GroundedReviewFindingV1(
        finding_id=f"mechanical.heading.{packet.packet_sha256[:16]}",
        kind="factual",
        criterion="structural_heading_fact_grounding",
        section=packet.section_path,
        claim=text,
        quoted_candidate_span=packet.unit_text,
        disposition="supports_acceptance",
        fact_id=fact_id,
        evidence_excerpt=evidence_excerpt,
        evidence_location=evidence_location,
        expected_polarity="positive_implementation",
        observed_polarity="positive_implementation",
        polarity_result="supports",
    )
    return FactualPlanReviewResultV1(
        verdict="ACCEPT",
        reasoning=(
            "The claim-free structural heading is bound by exact literal equality to an "
            "accepted repository fact; no prose judgment is required."
        ),
        findings=[finding],
    )
