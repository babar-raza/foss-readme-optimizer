"""Complete README document-plan, adoption, correction, and idempotency tests."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.markers import find_presentation_span, render_presentation_span

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Corrected 2026-07-24: repointed from level8-local-immutable-snapshot-and-facts-2026-07-24/,
# captured before the Maven resolver fix (search.maven.org never indexed the org.aspose group,
# so it falsely reported every Java pilot's package NOT_PUBLISHED). See
# plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/.
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts(org_repo: str) -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == org_repo)
    return (
        ProductFactsV2.model_validate(pilot["product_facts_v2"]),
        pilot["snapshot"]["source_revision"],
    )


def _force_source_build_acquisition(facts: ProductFactsV2) -> ProductFactsV2:
    """Return a copy of ``facts`` with the acquisition fact forced to a genuinely-
    unpublished (source_build) outcome -- a synthetic override proving the renderer's
    fallback path still works for a package that really isn't published, independent of
    real current registry state (see ecosystems/foss_coordinate.py's own "when no FOSS
    package exists, source_build is the correct outcome" rule)."""
    acquisition = facts.selected_fact("installation.verified_acquisition")
    forced = acquisition.model_copy(
        update={
            "value": {
                "method": "source_build",
                "outcome": "SOURCE_BUILD_VERIFIED",
                "detail": "synthetic: forced unpublished for this test",
            }
        }
    )
    other_facts = [fact for fact in facts.facts if fact.fact_id != acquisition.fact_id]
    return facts.model_copy(update={"facts": [*other_facts, forced]})


def test_presentation_span_preserves_inner_bytes_without_final_newline():
    source = "# Product\n\nExact bytes"
    candidate = render_presentation_span(source, "a" * 64)

    span = find_presentation_span(candidate)

    assert span is not None
    assert span.content.encode("utf-8") == source.encode("utf-8")
    assert span.content_bytes == source.encode("utf-8")


def test_missing_usage_section_gets_the_verified_minimal_example():
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = "# Aspose.Cells FOSS for Java\n\nSpreadsheet library for Java developers.\n"

    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert "## Quick Start" in candidate
    assert facts.selected_fact("example.minimal").value["code"].rstrip() in candidate
    assert any(
        operation.operation_id == "readme.overview-navigation-and-acquisition"
        and facts.selected_fact("example.minimal").fact_id in operation.fact_ids
        for operation in plan.operations
    )


def test_cells_keeps_verified_maven_install_and_adds_verified_example():
    """Corrected 2026-07-24: org.aspose:aspose-cells-foss IS published on Maven
    Central (the prior resolver queried the wrong endpoint) -- the renderer must
    KEEP a correct install claim, not strip it. See test_genuinely_unpublished_
    package_still_replaces_install_with_source_build below for the fallback path."""
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    assert facts.selected_fact("installation.verified_acquisition").value["method"] == (
        "maven_central"
    )
    source = """# Aspose.Cells FOSS for Java

Spreadsheet library for Java developers.

## Installation

```xml
<dependency>
  <groupId>org.aspose</groupId>
  <artifactId>aspose-cells-foss</artifactId>
  <version>1.0.0</version>
</dependency>
```

## Quick Start

Existing guidance.

## Known Limits

Only XLSX is supported.
"""

    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert "<artifactId>aspose-cells-foss</artifactId>" in candidate
    assert "mvn clean install" not in candidate
    assert facts.selected_fact("example.minimal").value["code"].rstrip() in candidate
    assert not any(
        operation.operation_id == "readme.installation.verified-source-replacement"
        for operation in plan.operations
    )


def test_genuinely_unpublished_package_still_replaces_install_with_source_build():
    """The fallback path this session's fix preserves: a package that really
    is NOT published still gets its install claim corrected to source-build."""
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    facts = _force_source_build_acquisition(facts)
    source = """# Aspose.Cells FOSS for Java

Spreadsheet library for Java developers.

## Installation

```xml
<dependency>
  <groupId>org.aspose</groupId>
  <artifactId>aspose-cells-foss</artifactId>
  <version>1.0.0</version>
</dependency>
```

## Quick Start

Existing guidance.
"""

    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert "<artifactId>aspose-cells-foss</artifactId>" not in candidate
    assert "mvn clean install" in candidate
    assert any(
        operation.operation_id == "readme.installation.verified-source-replacement"
        and operation.protected_content_treatment == "authoritative_fact_correction"
        for operation in plan.operations
    )


def test_pdf_keeps_verified_registry_badge_and_corrects_manifest_version():
    """Corrected 2026-07-24: org.aspose:aspose-pdf-foss IS published -- the
    Maven Central badge is a correct claim and must be kept. The manifest-
    version correction op is independent of acquisition method and unaffected."""
    org_repo = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = """# Aspose.PDF FOSS for Java

[![Maven Central](https://img.shields.io/maven-central/v/org.aspose/aspose-pdf.svg)](https://search.maven.org/artifact/org.aspose/aspose-pdf)

PDF processing for Java.

## Status

**Version 26.7** is current.

## Installation

```xml
<dependency>
  <groupId>org.aspose</groupId>
  <artifactId>aspose-pdf</artifactId>
</dependency>
```

## Quick Start

Existing guidance.
"""

    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert "maven-central" in candidate.lower()
    assert "**Version 26.6.0**" in candidate
    assert "**Version 26.7**" not in candidate


def test_promotional_callout_is_removed_but_relationship_section_preserved():
    """Uses cells-java facts (not 3D): this test is about the promotional-callout
    op, orthogonal to which pilot's facts are used, and cells' example.minimal is
    locally verified in this environment while 3D's needs a Java 21 toolchain this
    session's environment lacks (FACT-014, unrelated pre-existing gap)."""
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = """# Aspose.Cells FOSS for Java

Open-source spreadsheet processing for Java.

> FOSS is on https://products.aspose.org/cells/java/ and commercial is on https://products.aspose.com/cells/java/.

## About

The FOSS edition is open source; the commercial edition has broader format support.

## Usage

Existing guidance.
"""

    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    span = find_presentation_span(candidate)
    assert span is not None
    assert not any(line.startswith(">") for line in span.content.splitlines())
    assert "commercial edition has broader format support" in span.content


def test_identical_candidate_rerender_has_no_document_operations():
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = "# Cells\n\nJava spreadsheets.\n\n## Quick Start\n\nExisting guidance.\n"
    candidate, _ = build_readme_document_candidate(org_repo, source, facts, base_revision=revision)

    rerendered, rerun_plan = build_readme_document_candidate(
        org_repo, candidate, facts, base_revision=revision
    )

    assert rerendered == candidate
    assert rerun_plan.adoption.already_adopted is True
    assert rerun_plan.operations == []


def test_tampered_candidate_fails_independent_reconstruction():
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = "# Cells\n\nJava spreadsheets.\n\n## Quick Start\n\nExisting guidance.\n"
    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )

    decision = validate_readme_document_candidate(
        source,
        candidate.replace("Java spreadsheets.", "Unsupported claim."),
        plan,
        facts,
    )

    assert decision.valid is False
    assert decision.checks["candidate_hash_matches"] is False
    assert decision.checks["document_reconstruction"] is False
