"""Source-claim obligation field alternatives."""

from readme_agent.readme.source_claim_obligations import (
    obligation_any_fact_fields,
    obligation_required_fact_fields,
)


def test_scope_accepts_repository_or_imported_verified_limitations() -> None:
    assert obligation_required_fact_fields("scope_and_limitations") == frozenset()
    assert obligation_any_fact_fields("scope_and_limitations") == frozenset(
        {"product.limitations", "aspose.limitation_claims"}
    )
