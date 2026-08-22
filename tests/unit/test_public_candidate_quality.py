"""Deterministic, non-LLM quality gate for public README candidate prose."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
)
from readme_agent.validation.public_candidate_quality import (
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


def test_collada_export_positive_vs_unqualified_negative_is_blocking() -> None:
    candidate = """# Mesh Toolkit

## Key Capabilities

Exports the current scene to COLLADA, OBJ, and STL files for use in other applications.

## Scope and Limitations

COLLADA export is not supported.
"""
    report = evaluate_public_candidate_quality(candidate)

    matches = [f for f in report.findings if f.check_id == "contradiction_capability_phrase"]
    assert matches, report.findings
    assert matches[0].blocking is True
    assert matches[0].confidence == "phrase_discriminator"


def test_import_support_vs_export_limitation_is_not_a_contradiction() -> None:
    candidate = """# Mesh Toolkit

## Key Capabilities

Imports COLLADA files into the scene.

## Scope and Limitations

COLLADA export is not currently supported.
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)
    assert "contradiction_capability_symbol" not in _check_ids(report)


def test_symbol_available_vs_not_implemented_is_blocking() -> None:
    candidate = """# Mesh Toolkit

## API Reference

`NurbsSurface.to_mesh` converts a NURBS surface into a triangulated mesh.

## Scope and Limitations

`NurbsSurface.to_mesh` raises NotImplementedError.
"""
    report = evaluate_public_candidate_quality(candidate)

    matches = [f for f in report.findings if f.check_id == "contradiction_capability_symbol"]
    assert matches, report.findings
    assert matches[0].blocking is True
    assert matches[0].subject == "NurbsSurface.to_mesh"


def test_internal_assurance_narration_is_blocking_process_leakage() -> None:
    candidate = """# Mesh Toolkit

## Installation

The package was exercised from this exact source revision in an isolated,
network-disabled verification environment. The matching PyPI receipt was empty.
"""
    report = evaluate_public_candidate_quality(candidate)

    matches = [f for f in report.findings if f.check_id == "process_leakage"]
    assert matches, report.findings
    assert matches[0].blocking is True


def test_internal_assurance_phrase_inside_code_block_is_not_leakage() -> None:
    candidate = """# Mesh Toolkit

## Installation

```text
The package was exercised from this exact source revision in an isolated,
network-disabled verification environment.
```
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "process_leakage" not in _check_ids(report)


def test_supports_supportsing_is_malformed_duplicate_language() -> None:
    candidate = """# Mesh Toolkit

## Key Capabilities

The API supports supportsing multiple mesh formats.
"""
    report = evaluate_public_candidate_quality(candidate)

    matches = [f for f in report.findings if f.check_id == "malformed_duplicate_language"]
    assert matches, report.findings
    assert matches[0].blocking is True


def test_repeated_legitimate_identifier_across_sections_is_not_a_false_positive() -> None:
    candidate = """# Note Toolkit

## API Reference

### RichText

- `Text: str`
- `Tags: list[NoteTag]`

### Title

- `Text: str`
- `Tags: list[NoteTag]`
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "malformed_duplicate_language" not in _check_ids(report)
    assert "contradiction_capability_symbol" not in _check_ids(report)


def test_duplicate_headings_under_different_parents_get_distinct_section_paths() -> None:
    candidate = """# Product

## Python

### Roadmap

Coming soon.

## Java

### Roadmap

Coming soon.
"""
    report = evaluate_public_candidate_quality(candidate)

    matches = [f for f in report.findings if f.check_id == "empty_or_placeholder_section"]
    section_paths = {finding.locations[0].section_path for finding in matches}
    assert section_paths == {"Product > Python > Roadmap", "Product > Java > Roadmap"}


def test_claim_grounding_check_is_omitted_not_run_with_zero_findings_when_facts_absent() -> None:
    candidate = "# Product\n\n## Key Capabilities\n\nDoes something useful.\n"

    report = evaluate_public_candidate_quality(candidate)

    assert "claim_grounding_negative_fact" not in report.checks_run


def test_claim_grounding_check_runs_and_finds_nothing_when_facts_supplied_and_consistent() -> None:
    candidate = "# Product\n\n## Key Capabilities\n\nDoes something useful.\n"
    facts = _facts(_fact("product.limitations", ["Does not support remote file systems."]))

    report = evaluate_public_candidate_quality(candidate, facts=facts)

    assert "claim_grounding_negative_fact" in report.checks_run
    assert not [f for f in report.findings if f.check_id == "claim_grounding_negative_fact"]


def test_claim_grounding_flags_prose_contradicting_a_limitation_fact() -> None:
    candidate = "# Product\n\n## Key Capabilities\n\nSupports encrypting documents at rest.\n"
    facts = _facts(_fact("product.limitations", ["Encrypting documents at rest is not supported."]))

    report = evaluate_public_candidate_quality(candidate, facts=facts)

    matches = [f for f in report.findings if f.check_id == "claim_grounding_negative_fact"]
    assert matches, report.findings
    assert matches[0].blocking is True
    assert matches[0].confidence == "structured_evidence"
    assert matches[0].conflicting_ids == ("product.limitations:primary",)


def test_claim_grounding_does_not_treat_a_limited_to_statement_as_positive() -> None:
    candidate = (
        "# Workbook Toolkit\n\n"
        "## Scope and Limitations\n\n"
        "The verified load and save surface is limited to XLSX workbooks.\n"
    )
    facts = _facts(
        _fact(
            "product.limitations",
            ["The verified load and save surface is limited to XLSX workbooks."],
        )
    )

    report = evaluate_public_candidate_quality(candidate, facts=facts)

    assert "claim_grounding_negative_fact" not in _check_ids(report)


def test_same_input_twice_produces_a_byte_identical_report() -> None:
    candidate = """# Product

## Key Capabilities

The API supports supportsing multiple mesh formats.
"""
    first = evaluate_public_candidate_quality(candidate)
    second = evaluate_public_candidate_quality(candidate)

    assert first == second
    assert first.report_hash == second.report_hash
    assert first.model_dump_json() == second.model_dump_json()


def test_editing_one_section_does_not_change_finding_ids_anchored_elsewhere() -> None:
    base = """# Product

## Key Capabilities

The API supports supportsing multiple mesh formats.

## Notes

Nothing notable yet.
"""
    edited = base.replace("Nothing notable yet.", "A second sentence added here for good measure.")

    first = evaluate_public_candidate_quality(base)
    second = evaluate_public_candidate_quality(edited)

    def duplicate_finding_id(report):
        matches = [f for f in report.findings if f.check_id == "malformed_duplicate_language"]
        assert matches
        return matches[0].finding_id

    assert duplicate_finding_id(first) == duplicate_finding_id(second)
