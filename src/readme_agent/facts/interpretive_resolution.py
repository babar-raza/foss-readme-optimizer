"""Reconcile interpretive citations against the final selected technical facts."""

from __future__ import annotations

from collections.abc import Mapping

from readme_agent.facts.interpretive_evidence import (
    InterpretiveClaimV1,
    groundedness_fact_candidate,
)
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_ACCEPTED_STATES = {"verified", "policy_approved"}
_EVIDENCE_BACKED_FIELDS = (
    "product.capabilities",
    "product.formats",
    "product.limitations",
)


def _accepted(fact: FactRecordV2) -> bool:
    return fact.verification_state in _ACCEPTED_STATES and not fact.has_unresolved_conflict


def _replace_selected(
    facts: ProductFactsV2,
    replacements: Mapping[str, FactRecordV2],
) -> ProductFactsV2:
    retained = [fact for fact in facts.facts if fact.field not in replacements]
    retained.extend(replacements.values())
    selected = dict(facts.selected_fact_ids)
    selected.update({field: fact.fact_id for field, fact in replacements.items()})
    return ProductFactsV2(
        org_repo=facts.org_repo,
        facts=retained,
        selected_fact_ids=selected,
        package_root_roles=facts.package_root_roles,
    )


def reconcile_final_interpretive_grounding(
    *,
    facts_before_attempt: ProductFactsV2,
    gated_facts: Mapping[str, FactRecordV2],
    audience_claims: list[InterpretiveClaimV1],
    problem_claims: list[InterpretiveClaimV1],
    source_revision: str | None,
    observed_at: str | None,
) -> dict[str, FactRecordV2]:
    """Retain proved technical facts and re-ground prose against the final graph.

    A repair attempt may improve an interpretive field while accidentally
    regressing a technical field that an earlier attempt already proved. The
    earlier immutable-revision proof remains valid, so retain it. Then re-run
    both interpretive gates against exactly the technical selections that will
    be returned; a citation can therefore never become stale between gating and
    ``ProductFactsV2`` construction.
    """

    reconciled = dict(gated_facts)
    accepted_technical: dict[str, FactRecordV2] = {}
    for field in _EVIDENCE_BACKED_FIELDS:
        candidate = reconciled.get(field)
        if candidate is None:
            continue
        established = facts_before_attempt.selected_fact(field)
        selected = candidate if _accepted(candidate) else established
        if not _accepted(selected):
            selected = candidate
        reconciled[field] = selected
        if _accepted(selected):
            accepted_technical[field] = selected

    grounding_facts = _replace_selected(facts_before_attempt, accepted_technical)
    reconciled["product.audience"] = groundedness_fact_candidate(
        "product.audience",
        audience_claims,
        grounding_facts,
        source_revision,
        observed_at,
    )
    reconciled["product.problems_solved"] = groundedness_fact_candidate(
        "product.problems_solved",
        problem_claims,
        grounding_facts,
        source_revision,
        observed_at,
        allow_partial=True,
    )
    return reconciled
