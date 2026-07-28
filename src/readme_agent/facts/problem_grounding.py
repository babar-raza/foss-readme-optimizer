"""Derives safe problem statements from already-verified repository capabilities."""

from __future__ import annotations

from readme_agent.facts.interpretive_evidence import (
    InterpretiveClaimV1,
    groundedness_fact_candidate,
)
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_MAX_PROBLEM_STATEMENTS = 4


def derive_grounded_problem_fallback(
    facts: ProductFactsV2,
    source_revision: str | None,
    observed_at: str | None,
) -> tuple[list[InterpretiveClaimV1], FactRecordV2] | None:
    """Reuse verified capability text when an interpretive problem draft is ungrounded.

    The capability values have already passed repository-evidence validation. Reusing their
    exact text avoids inventing synonyms that the cited evidence cannot support and avoids
    spending another model call asking for a mechanically constrained rewrite.
    """

    capability = facts.selected_fact("product.capabilities")
    if capability.verification_state not in {"verified", "policy_approved"}:
        return None
    if capability.has_unresolved_conflict:
        return None

    values = capability.value if isinstance(capability.value, list) else [capability.value]
    statements = list(
        dict.fromkeys(
            text for value in values if isinstance(value, str) and (text := value.strip())
        )
    )[:_MAX_PROBLEM_STATEMENTS]
    if not statements:
        return None

    claims = [
        InterpretiveClaimV1(
            claim_id=f"capability-derived-problem-{index}",
            text=statement,
            supporting_fact_ids=[capability.fact_id],
        )
        for index, statement in enumerate(statements, start=1)
    ]
    candidate = groundedness_fact_candidate(
        "product.problems_solved",
        claims,
        facts,
        source_revision,
        observed_at,
        allow_partial=True,
    )
    if candidate.verification_state != "verified":
        return None
    return claims, candidate
