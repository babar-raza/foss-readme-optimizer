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


def test_collada_internal_exporter_implemented_vs_public_route_unavailable_is_not_flagged() -> None:
    candidate = """# Mesh Toolkit

## Implementation Notes

The COLLADA exporter is implemented and covered by tests.

## Scope and Limitations

COLLADA export through the public API is not currently reachable.
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)
    assert "contradiction_capability_symbol" not in _check_ids(report)


def test_scope_qualified_negative_with_shared_discriminator_is_not_flagged() -> None:
    candidate = """# Mesh Toolkit

## Key Capabilities

Exports the model to COLLADA format.

## Scope and Limitations

COLLADA export is unsupported in this build.
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)


def test_discriminator_mismatch_is_not_flagged_as_a_contradiction() -> None:
    candidate = """# Mesh Toolkit

## Key Capabilities

Converts PDF documents to images.

## Scope and Limitations

TIFF export is not supported.
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)


def test_exception_clause_exempts_a_named_format_from_a_broader_limitation() -> None:
    """Regression test for a real false positive found via a pilot rerun against a real
    committed candidate: "Saving formats other than PDF ... are not implemented" was matched
    against every unrelated PDF-positive claim in the document, because PDF is merely mentioned
    inside the negative sentence's own exception clause -- it is explicitly exempted, not
    limited. Reconstructing the pre-fix code and running this exact fixture against it produces
    8 contradiction_capability_phrase findings; this asserts there are none."""

    candidate = (
        "# Format Toolkit\n\n"
        "## Features\n\n"
        "- PDF export via `Document.Save(..., SaveFormat.Pdf)`\n\n"
        "## Quick Start\n\n"
        "PDF export requires an extra dependency: install it first.\n\n"
        "## Golden Workflow\n\n"
        "Golden PDFs are stored under `tests/goldens/pdf/` for regression coverage.\n\n"
        "## Current Limitations\n\n"
        "- Saving formats other than PDF (HTML/images/legacy) are declared for compatibility "
        "but not implemented.\n"
    )
    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)


def test_conditional_dependency_prose_is_not_a_firm_capability_claim() -> None:
    """Regression test for a real false positive found via the same pilot rerun: "If `X` is
    installed, ... / If `X` is unavailable but `Y` is available, ..." describes an optional
    runtime fallback, not a firm claim that `X` is both available and unavailable. Reconstructing
    the pre-fix code and running this exact fixture against it produces a blocking
    contradiction_capability_symbol finding; this asserts there is none."""

    candidate = """# Format Toolkit

## Golden Workflow

If `PyMuPDF` is installed, the test suite also renders pages to PNG for visual diffing.
If `PyMuPDF` is unavailable but `pdftoppm` is available on `PATH`, the tests fall back to it.
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_symbol" not in _check_ids(report)


def test_phrase_contradiction_without_shared_discriminator_is_advisory_not_blocking() -> None:
    candidate = """# Mesh Toolkit

## Key Capabilities

Supports converting documents between formats.

## Scope and Limitations

Document conversion between formats is not currently available.
"""
    report = evaluate_public_candidate_quality(candidate)

    matches = [f for f in report.findings if f.check_id == "contradiction_capability_phrase"]
    assert matches, report.findings
    assert matches[0].blocking is False
    assert matches[0].severity == "warning"
    assert matches[0].confidence == "phrase_generic"


def test_product_acronym_alone_does_not_make_distinct_capabilities_contradict() -> None:
    candidate = """# Aspose.3D FOSS for Java

## Overview

Create, load, inspect, transform, and save 3D scenes with an open-source Java API.

## Scope and Limitations

Rendering and full commercial-API parity remain incomplete.
"""

    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)


def test_non_format_scope_does_not_contradict_positive_format_capability() -> None:
    candidate = """# Aspose.PDF FOSS for Java

## Key Capabilities

Create, open, modify, and save PDF documents.

## Scope and Limitations

OCR, non-PDF conversion, XFA rendering, 3D annotations, and PDF/X are out of scope.
"""

    report = evaluate_public_candidate_quality(candidate)

    assert "contradiction_capability_phrase" not in _check_ids(report)


def test_legitimate_phrase_repeated_across_sections_is_not_flagged() -> None:
    candidate = """# Product

## Overview

The library focuses on document lifecycle management for structured files.

## Key Capabilities

Document lifecycle management is available for every supported format.
"""
    report = evaluate_public_candidate_quality(candidate)

    assert "process_leakage" not in _check_ids(report)
    assert "malformed_duplicate_language" not in _check_ids(report)
