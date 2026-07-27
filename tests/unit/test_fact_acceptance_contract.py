"""Tests for the versioned cached-product-truth acceptance boundary."""

from readme_agent.facts.acceptance_contract import (
    README_TRUTH_FIELDS,
    _component_hash,
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactConflictV2,
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
        "acquisition_truth",
        "classification_semantics",
        "conflict_semantics",
        "fact_schema",
        "fact_eligibility",
        "evidence_polarity",
        "root_role_selection",
        "visitor_render_eligibility",
    }
    assert contract.recollect_on_component_change == (
        "fact_schema",
        "fact_eligibility",
        "acquisition_truth",
        "evidence_polarity",
        "root_role_selection",
    )
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


def test_classification_honors_the_contract_verification_states():
    facts = _facts()
    contract = current_fact_acceptance_contract().model_copy(
        update={"accepted_verification_states": ("policy_approved",)}
    )

    assert classify_product_truth(facts, contract) == "BLOCKED_MISSING_EVIDENCE"


def test_component_hash_is_checkout_line_ending_invariant(tmp_path):
    lf_root = tmp_path / "lf"
    crlf_root = tmp_path / "crlf"
    lf_root.mkdir()
    crlf_root.mkdir()
    lf = lf_root / "component.py"
    crlf = crlf_root / "component.py"
    lf.write_bytes(b"first = 1\nsecond = 2\n")
    crlf.write_bytes(b"first = 1\r\nsecond = 2\r\n")

    assert _component_hash(lf_root, ("component.py",)) == _component_hash(
        crlf_root, ("component.py",)
    )


def test_classification_uses_the_versioned_required_field_membership():
    facts = _facts(missing_field="product.limitations")
    contract = current_fact_acceptance_contract()

    assert classify_product_truth(facts, contract) == "FACTS_READY"
    stricter = contract.model_copy(
        update={"required_fields": (*contract.required_fields, "product.limitations")}
    )
    assert classify_product_truth(facts, stricter) == "BLOCKED_MISSING_EVIDENCE"


def test_missing_contract_field_fails_closed_instead_of_raising():
    facts = _facts()
    contract = current_fact_acceptance_contract().model_copy(
        update={"required_fields": (*README_TRUTH_FIELDS, "product.not_yet_defined")}
    )

    assert classify_product_truth(facts, contract) == "BLOCKED_MISSING_EVIDENCE"


def test_classification_uses_fact_eligibility_and_conflict_semantics():
    facts = _facts()
    audience = facts.selected_fact("product.audience")
    blocked_audience = audience.model_copy(update={"verification_state": "blocked"})
    blocked = facts.model_copy(
        update={
            "facts": [
                blocked_audience if fact.fact_id == audience.fact_id else fact
                for fact in facts.facts
            ]
        }
    )
    conflicting_audience = audience.model_copy(
        update={
            "verification_state": "conflicting",
            "conflicts": [
                FactConflictV2(
                    conflicting_fact_id=descriptive_fact_id(
                        "product.audience", "conflicting-fixture"
                    ),
                    conflicting_value=["Operators using Python"],
                    conflicting_source=audience.source,
                    status="unresolved",
                    reason="controlled conflict",
                    authoritative_owner="repository-owner",
                    affected_surfaces=["readme"],
                )
            ],
        }
    )
    conflicting = facts.model_copy(
        update={
            "facts": [
                conflicting_audience if fact.fact_id == audience.fact_id else fact
                for fact in facts.facts
            ]
        }
    )

    assert classify_product_truth(blocked) == "BLOCKED_MISSING_EVIDENCE"
    assert classify_product_truth(conflicting) == "BLOCKED_FACT_CONFLICT"


def test_verified_but_non_renderable_visitor_fact_is_not_accepted():
    facts = _facts()
    audience = facts.selected_fact("product.audience")
    non_renderable = audience.model_copy(update={"value": {"internal": "audience-code"}})
    altered = facts.model_copy(
        update={
            "facts": [
                non_renderable if fact.fact_id == audience.fact_id else fact for fact in facts.facts
            ]
        }
    )

    assert classify_product_truth(altered) == "BLOCKED_MISSING_EVIDENCE"
