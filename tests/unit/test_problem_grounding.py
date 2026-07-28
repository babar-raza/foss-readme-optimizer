"""Tests deterministic problem-statement fallback from verified capabilities."""

from readme_agent.facts.problem_grounding import derive_grounded_problem_fallback
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


def _facts(capability_state: str = "verified") -> ProductFactsV2:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://acme/widget",
        source_revision="abc123",
    )
    capability = FactRecordV2(
        fact_id=descriptive_fact_id("product.capabilities", "repository-evidence"),
        field="product.capabilities",
        value=["Create widgets", "Convert widgets", "Create widgets"],
        source=source,
        verification_state=capability_state,
        authoritative_owner="repository-owner",
        confidence=1.0 if capability_state == "verified" else 0.0,
        affected_surfaces=["readme.capabilities"],
    )
    records = [capability]
    for field_name in REQUIRED_PRODUCT_FIELDS:
        if field_name == capability.field:
            continue
        records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field_name, "missing"),
                field=field_name,
                value=None,
                source=source,
                verification_state="missing",
                authoritative_owner="repository-owner",
                confidence=0.0,
                affected_surfaces=["readme"],
            )
        )
    return ProductFactsV2(
        org_repo="acme/widget",
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def test_verified_capabilities_become_exact_grounded_problem_statements():
    result = derive_grounded_problem_fallback(_facts(), "abc123", None)

    assert result is not None
    claims, fact = result
    assert [claim.text for claim in claims] == ["Create widgets", "Convert widgets"]
    assert fact.verification_state == "verified"
    assert fact.value == ["Create widgets", "Convert widgets"]
    assert fact.supporting_fact_ids == ["product.capabilities:repository-evidence"]


def test_unverified_capabilities_cannot_become_problem_statements():
    assert derive_grounded_problem_fallback(_facts("blocked"), "abc123", None) is None
