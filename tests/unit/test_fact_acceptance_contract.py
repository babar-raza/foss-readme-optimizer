"""Tests for the versioned cached-product-truth acceptance boundary."""

from readme_agent.facts.acceptance_contract import (
    README_TRUTH_FIELDS,
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


def _facts(*, missing_field: str | None = None) -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision="a" * 40,
    )
    renderable_values = {
        "product.audience": ["Developers using Java"],
        "product.problems_solved": ["Process widget files"],
        "product.capabilities": ["Create and inspect widgets"],
        "product.formats": ["WGT"],
    }
    records = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "contract-fixture"),
            field=field,
            value=(
                None if field == missing_field else renderable_values.get(field, {"field": field})
            ),
            source=source,
            verification_state="missing" if field == missing_field else "verified",
            authoritative_owner="repository-owner",
            confidence=0.0 if field == missing_field else 1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo="org/repo",
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def test_contract_hash_covers_every_named_acceptance_component():
    contract = current_fact_acceptance_contract()

    assert contract.required_fields == README_TRUTH_FIELDS
    assert set(contract.component_hashes) == {
        "classification_semantics",
        "fact_schema",
        "fact_eligibility",
        "evidence_polarity",
        "visitor_render_eligibility",
    }
    assert len(contract.canonical_hash()) == 64
    assert all(len(digest) == 64 for digest in contract.component_hashes.values())


def test_component_or_rule_change_changes_the_contract_hash():
    contract = current_fact_acceptance_contract()

    component_changed = contract.model_copy(
        update={
            "component_hashes": {
                **contract.component_hashes,
                "evidence_polarity": "0" * 64,
            }
        }
    )
    membership_changed = contract.model_copy(
        update={"required_fields": (*contract.required_fields, "product.limitations")}
    )

    assert component_changed.canonical_hash() != contract.canonical_hash()
    assert membership_changed.canonical_hash() != contract.canonical_hash()


def test_classification_uses_the_versioned_required_field_membership():
    facts = _facts(missing_field="product.limitations")
    contract = current_fact_acceptance_contract()

    assert classify_product_truth(facts, contract) == "FACTS_READY"
    stricter = contract.model_copy(
        update={"required_fields": (*contract.required_fields, "product.limitations")}
    )
    assert classify_product_truth(facts, stricter) == "BLOCKED_MISSING_EVIDENCE"
