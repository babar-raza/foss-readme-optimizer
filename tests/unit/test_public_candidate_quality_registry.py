"""Deterministic, non-LLM quality gate for public README candidate prose."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
)
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.validation.public_candidate_quality import (
    _CHECKS_SOURCE_HASH_AT_VERSION,
    _REUSED_LEAKAGE_RULE_IDS,
    _REUSED_MALFORMED_RULE_IDS,
    PUBLIC_QUALITY_CHECKS_VERSION,
    compute_checks_source_hash,
    evaluate_public_candidate_quality,
)


def _fact(field: str, value: object, verification_state: str = "verified") -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:primary",
        field=field,
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository", location="src/", retrieved_at="2026-08-22"
        ),
        verification_state=verification_state,
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.limitations"],
    )


def _facts(*records: FactRecordV2) -> ProductFactsV2:
    """Build a complete, valid ProductFactsV2: every REQUIRED_PRODUCT_FIELDS entry gets a trivial
    stub fact unless the caller supplied one, so tests only need to spell out the field(s) they
    actually care about (usually "product.limitations")."""

    by_field = {record.field: record for record in records}
    for field in REQUIRED_PRODUCT_FIELDS:
        if field not in by_field:
            by_field[field] = _fact(field, "n/a")
    return ProductFactsV2(
        org_repo="example-org/example-repo",
        facts=list(by_field.values()),
        selected_fact_ids={field: record.fact_id for field, record in by_field.items()},
    )


def _check_ids(report) -> set[str]:
    return {finding.check_id for finding in report.findings}


# --- required red tests -------------------------------------------------------------------


def test_claim_grounding_catches_two_different_phrasings_of_the_same_defect() -> None:
    facts = _facts(_fact("product.limitations", ["Encrypting documents at rest is not supported."]))
    first = evaluate_public_candidate_quality(
        "# Product\n\n## Key Capabilities\n\nSupports encrypting documents at rest.\n",
        facts=facts,
    )
    second = evaluate_public_candidate_quality(
        "# Product\n\n## Highlights\n\nThe toolkit provides encrypting documents at rest.\n",
        facts=facts,
    )

    assert any(f.check_id == "claim_grounding_negative_fact" for f in first.findings)
    assert any(f.check_id == "claim_grounding_negative_fact" for f in second.findings)


def test_symbol_contradiction_catches_two_different_phrasings_of_the_same_defect() -> None:
    first = evaluate_public_candidate_quality(
        "# P\n\n## API\n\n`Mesh.union` supports combining two meshes.\n\n"
        "## Limitations\n\n`Mesh.union` raises NotImplementedError.\n"
    )
    second = evaluate_public_candidate_quality(
        "# P\n\n## API\n\n`Mesh.union` provides mesh combination support.\n\n"
        "## Limitations\n\n`Mesh.union` is not implemented.\n"
    )

    assert any(f.check_id == "contradiction_capability_symbol" for f in first.findings)
    assert any(f.check_id == "contradiction_capability_symbol" for f in second.findings)


# --- regression controls -------------------------------------------------------------------


def test_reused_presentation_lint_rule_ids_still_exist() -> None:
    upstream_rule_ids = set(lint_readme_presentation("# X\n", None).rules_run)

    assert _REUSED_LEAKAGE_RULE_IDS <= upstream_rule_ids
    assert _REUSED_MALFORMED_RULE_IDS <= upstream_rule_ids


def test_checks_source_hash_matches_recorded_version() -> None:
    """A mismatch means detection logic changed without a conscious version-bump decision.

    If this fails after a deliberate heuristic edit: bump PUBLIC_QUALITY_CHECKS_VERSION, then
    update _CHECKS_SOURCE_HASH_AT_VERSION to compute_checks_source_hash()'s new value.
    """

    assert compute_checks_source_hash() == _CHECKS_SOURCE_HASH_AT_VERSION
    assert PUBLIC_QUALITY_CHECKS_VERSION == 5
