"""Structured negative-fact grounding check for public README prose."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.capability_semantics import same_public_capability
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.document_structure import Heading
from readme_agent.readme.presentation_lint_text import visible_lines
from readme_agent.validation.public_quality_contracts import (
    PublicQualityFindingV1,
    _location,
    _make_finding,
)
from readme_agent.validation.public_quality_semantic_common import _NEGATIVE_CUE, _POSITIVE_CUE

# ---------------------------------------------------------------------------------------------
# Tier A -- claim grounding against explicit structured negative/unresolved facts
# ---------------------------------------------------------------------------------------------


def _fact_phrase(fact: FactRecordV2) -> str | None:
    value = fact.value
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        parts = [str(item) for item in value if str(item).strip()]
        return ", ".join(parts) if parts else None
    if isinstance(value, dict):
        parts = [str(item) for item in value.values() if isinstance(item, str) and item.strip()]
        return ", ".join(parts) if parts else None
    return None


def _check_claim_grounding_negative_fact(
    text: str,
    headings: list[Heading],
    facts: ProductFactsV2 | None,
    claim_accountability: ReadmeClaimAccountabilityMapV1 | None,
) -> list[PublicQualityFindingV1]:
    if facts is None:
        return []
    negative_facts = [
        fact
        for fact in facts.facts
        if fact.field == "product.limitations"
        or fact.verification_state in {"conflicting", "blocked", "missing"}
    ]
    if not negative_facts:
        return []
    findings: list[PublicQualityFindingV1] = []
    for line in visible_lines(text):
        if _NEGATIVE_CUE.search(line.text) or not _POSITIVE_CUE.search(line.text):
            continue
        accountable_fact_ids = None
        if claim_accountability is not None:
            accountable_fact_ids = {
                fact_id
                for claim in claim_accountability.claims
                if claim.stage == "candidate"
                and claim.currently_accountable
                and claim.source_byte_start < line.end
                and claim.source_byte_end > line.start
                for fact_id in claim.accepted_fact_ids
            }
        for fact in negative_facts:
            if accountable_fact_ids is not None and fact.fact_id not in accountable_fact_ids:
                continue
            fact_phrase = _fact_phrase(fact)
            if not fact_phrase or not same_public_capability(line.text, fact_phrase):
                continue
            location = _location(headings, text, line.start, line.end)
            findings.append(
                _make_finding(
                    "claim_grounding_negative_fact",
                    "claim_grounding",
                    "critical",
                    "structured_evidence",
                    True,
                    (location,),
                    subject=fact.field,
                    polarity="explicit_constraint",
                    conflicting_ids=(fact.fact_id,),
                    message=(
                        f"Public prose asserts a capability that fact {fact.fact_id!r} "
                        f"({fact.field}, verification_state={fact.verification_state!r}) records "
                        "as a limitation or unresolved."
                    ),
                    repair_target=f"{location.section_path}: reconcile with fact {fact.fact_id}",
                )
            )
    return findings
