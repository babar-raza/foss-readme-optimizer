"""Final interpretive grounding follows the exact returned technical facts."""

from __future__ import annotations

from readme_agent.facts.interpretive_evidence import InterpretiveClaimV1
from readme_agent.facts.interpretive_resolution import (
    reconcile_final_interpretive_grounding,
    replace_selected_for_regrounding,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


def _fact(
    field: str,
    value: object,
    qualifier: str,
    *,
    state: str = "verified",
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, qualifier),
        field=field,
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://acme/widget",
            source_revision="abc123",
        ),
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state == "verified" else 0.0,
        affected_surfaces=["readme"],
    )


def _facts() -> ProductFactsV2:
    identity = _fact(
        "product.identity",
        {"family": "widget", "ecosystem": "java"},
        "identity",
    )
    formats = _fact("product.formats", ["OBJ documents"], "proved-formats")
    records = [identity, formats]
    selected = {fact.field: fact.fact_id for fact in records}
    for field in REQUIRED_PRODUCT_FIELDS:
        if field in selected:
            continue
        missing = _fact(field, None, "missing", state="missing")
        records.append(missing)
        selected[field] = missing.fact_id
    return ProductFactsV2(
        org_repo="acme/widget",
        facts=records,
        selected_fact_ids=selected,
    )


def _audience_claim(facts: ProductFactsV2) -> InterpretiveClaimV1:
    return InterpretiveClaimV1(
        claim_id="audience",
        text="Developers using Java.",
        supporting_fact_ids=[facts.selected_fact("product.identity").fact_id],
    )


def test_prior_verified_technical_fact_survives_later_repair_regression():
    facts = _facts()
    formats = facts.selected_fact("product.formats")
    blocked_formats = formats.model_copy(
        update={
            "value": {"evidence_failures": ["later repair used a stale anchor"]},
            "verification_state": "blocked",
            "confidence": 0.0,
        }
    )
    problem_claim = InterpretiveClaimV1(
        claim_id="problem",
        text="OBJ documents",
        supporting_fact_ids=[formats.fact_id],
    )

    reconciled = reconcile_final_interpretive_grounding(
        facts_before_attempt=facts,
        gated_facts={"product.formats": blocked_formats},
        audience_claims=[_audience_claim(facts)],
        problem_claims=[problem_claim],
        source_revision="abc123",
        observed_at=None,
    )

    assert reconciled["product.formats"] == formats
    assert reconciled["product.problems_solved"].verification_state == "verified"
    assert reconciled["product.problems_solved"].supporting_fact_ids == [formats.fact_id]


def test_interpretive_claim_is_rechecked_when_final_technical_fact_changes():
    facts = _facts()
    old_formats = facts.selected_fact("product.formats")
    new_formats = _fact("product.formats", ["glTF documents"], "new-formats")
    problem_claim = InterpretiveClaimV1(
        claim_id="problem",
        text="OBJ documents",
        supporting_fact_ids=[old_formats.fact_id],
    )

    reconciled = reconcile_final_interpretive_grounding(
        facts_before_attempt=facts,
        gated_facts={"product.formats": new_formats},
        audience_claims=[_audience_claim(facts)],
        problem_claims=[problem_claim],
        source_revision="abc123",
        observed_at=None,
    )

    assert reconciled["product.formats"] == new_formats
    assert reconciled["product.problems_solved"].verification_state == "blocked"
    assert reconciled["product.problems_solved"].supporting_fact_ids == []


def test_technical_replacement_invalidates_dependent_until_atomic_regrounding():
    facts = _facts()
    old_capability = _fact("product.capabilities", ["Load OBJ documents."], "old-capability")
    old_problem = _fact("product.problems_solved", ["Load OBJ documents."], "old-problem")
    old_problem = old_problem.model_copy(update={"supporting_fact_ids": [old_capability.fact_id]})
    facts = ProductFactsV2(
        org_repo=facts.org_repo,
        facts=[
            fact
            for fact in facts.facts
            if fact.field not in {"product.capabilities", "product.problems_solved"}
        ]
        + [old_capability, old_problem],
        selected_fact_ids={
            **facts.selected_fact_ids,
            "product.capabilities": old_capability.fact_id,
            "product.problems_solved": old_problem.fact_id,
        },
    )
    new_capability = _fact("product.capabilities", ["Load glTF documents."], "new-capability")

    transitional = replace_selected_for_regrounding(facts, {"product.capabilities": new_capability})

    assert transitional.selected_fact("product.capabilities") == new_capability
    assert transitional.selected_fact("product.problems_solved").verification_state == "missing"
    assert old_problem.fact_id not in {fact.fact_id for fact in transitional.facts}

    new_problem = _fact("product.problems_solved", ["Load glTF documents."], "new-problem")
    new_problem = new_problem.model_copy(update={"supporting_fact_ids": [new_capability.fact_id]})
    final = replace_selected_for_regrounding(
        facts,
        {
            "product.capabilities": new_capability,
            "product.problems_solved": new_problem,
        },
    )

    assert final.selected_fact("product.problems_solved") == new_problem


def test_unselected_stale_dependent_is_removed_without_invalidating_current_selection():
    facts = _facts()
    old_capability = facts.selected_fact("product.capabilities")
    current_problem = facts.selected_fact("product.problems_solved")
    historical = _fact("product.problems_solved", ["Historical claim."], "historical-problem")
    historical = historical.model_copy(update={"supporting_fact_ids": [old_capability.fact_id]})
    facts = facts.model_copy(update={"facts": [*facts.facts, historical]})
    new_capability = _fact("product.capabilities", ["Load glTF documents."], "new-capability")

    replaced = replace_selected_for_regrounding(
        facts,
        {"product.capabilities": new_capability},
    )

    assert replaced.selected_fact("product.problems_solved") == current_problem
    assert historical not in replaced.facts
