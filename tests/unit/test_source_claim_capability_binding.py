"""Prove fail-closed feature-detail matching at the public dispatcher seam."""

from __future__ import annotations

from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.source_claim_structured_matching import (
    structured_source_claim_fact_ids,
)
from tests.unit.test_source_claim_structured_matching_exact import _facts


def _ids(source: str, capability: str) -> set[str]:
    facts = _facts([capability])
    claim = assess_material_claims(source)[0]
    text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    return structured_source_claim_fact_ids(source, claim, text, facts)


def test_feature_detail_rejects_near_semantic_capability() -> None:
    source = "# Product\n\n## Features\n\n- Render imaginary widgets\n"

    assert _ids(source, "Render verified widgets") == set()


def test_feature_detail_rejects_unknown_technical_identifier() -> None:
    source = "# Product\n\n## Features\n\n- Render with `UnknownWidget`\n"

    assert _ids(source, "Render with Widget") == set()
