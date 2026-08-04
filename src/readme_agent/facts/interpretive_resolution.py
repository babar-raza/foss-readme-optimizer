"""Reconcile interpretive citations against the final selected technical facts."""

from __future__ import annotations

from collections.abc import Mapping

from readme_agent.facts.interpretive_evidence import (
    InterpretiveClaimV1,
    groundedness_fact_candidate,
)
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)

_ACCEPTED_STATES = {"verified", "policy_approved"}
_EVIDENCE_BACKED_FIELDS = (
    "product.capabilities",
    "product.formats",
    "product.limitations",
)


def _accepted(fact: FactRecordV2) -> bool:
    return fact.verification_state in _ACCEPTED_STATES and not fact.has_unresolved_conflict


def retain_established_repository_limitations(
    field: str,
    candidate: FactRecordV2,
    established: FactRecordV2,
) -> bool:
    """Keep proved constraints when an interpretive repair contributes none."""

    repository_sources = {
        "mechanical_repository",
        "mechanical_manifest",
        "mechanical_test",
    }
    return (
        field == "product.limitations"
        and _accepted(candidate)
        and candidate.value == []
        and candidate.source.location == "repository://verified-empty"
        and established.source.source_type in repository_sources
        and isinstance(established.value, list)
        and bool(established.value)
        and _accepted(established)
        and candidate.source.source_revision == established.source.source_revision
    )


def replace_selected_for_regrounding(
    facts: ProductFactsV2,
    replacements: Mapping[str, FactRecordV2],
) -> ProductFactsV2:
    """Replace technical selections and invalidate stale interpretive dependents."""

    effective = dict(replacements)
    replaced_ids = {
        facts.selected_fact(field).fact_id
        for field, replacement in replacements.items()
        if field in facts.selected_fact_ids
        and facts.selected_fact(field).fact_id != replacement.fact_id
    }
    affected_fields = {
        field
        for field in facts.selected_fact_ids
        if field not in replacements
        and replaced_ids.intersection(facts.selected_fact(field).supporting_fact_ids)
    }
    unsupported = affected_fields - {"product.audience", "product.problems_solved"}
    if unsupported:
        raise ValueError(
            "technical fact replacement invalidates unsupported dependent fields: "
            f"{sorted(unsupported)}"
        )
    if affected_fields:
        replacement_source = next(iter(replacements.values())).source
        for field in sorted(affected_fields):
            previous = facts.selected_fact(field)
            effective[field] = FactRecordV2(
                fact_id=descriptive_fact_id(field, "pending-reground"),
                field=field,
                value=None,
                source=FactSourceV2(
                    source_type="mechanical_repository",
                    location="repository://pending-reground",
                    source_revision=replacement_source.source_revision,
                    retrieved_at=replacement_source.retrieved_at,
                ),
                verification_state="missing",
                authoritative_owner=previous.authoritative_owner,
                confidence=0.0,
                affected_surfaces=previous.affected_surfaces,
            )

    retained = [
        fact
        for fact in facts.facts
        if fact.field not in effective and not replaced_ids.intersection(fact.supporting_fact_ids)
    ]
    retained.extend(effective.values())
    selected = dict(facts.selected_fact_ids)
    selected.update({field: fact.fact_id for field, fact in effective.items()})
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
        if retain_established_repository_limitations(field, candidate, established):
            selected = established
        else:
            selected = candidate if _accepted(candidate) else established
        if not _accepted(selected):
            selected = candidate
        reconciled[field] = selected
        if _accepted(selected):
            accepted_technical[field] = selected

    grounding_facts = replace_selected_for_regrounding(facts_before_attempt, accepted_technical)
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
