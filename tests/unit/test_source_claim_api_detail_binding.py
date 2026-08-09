"""Prove API-detail matching rejects unknown identifiers and qualifiers."""

from __future__ import annotations

from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.source_claim_structured_matching import (
    structured_source_claim_fact_ids,
)
from tests.unit.test_source_claim_structured_matching_exact import _facts


def _nested_ids(detail: str) -> set[str]:
    source = f"# Product\n\n## Public API\n\n- `Widget`\n  - {detail}\n"
    facts = _facts(["Render verified widgets"])
    claim = assess_material_claims(source)[1]
    text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    return structured_source_claim_fact_ids(source, claim, text, facts)


def test_api_detail_rejects_unknown_member() -> None:
    assert _nested_ids("`erase(target)`") == set()


def test_api_detail_rejects_unproved_qualifier() -> None:
    assert _nested_ids("`render(target)` — deletes all data") == set()
