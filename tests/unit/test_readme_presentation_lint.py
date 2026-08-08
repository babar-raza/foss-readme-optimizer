"""Deterministic pre-review README presentation lint qualification."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.evidence_polarity import EvidencePolarityAssessmentV1
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.presentation_lint import lint_readme_presentation
from readme_agent.readme.public_text import (
    canonical_abbreviations_from_facts,
    canonicalize_public_markdown,
    title_case_heading,
    visitor_capability_phrase,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = PROJECT_ROOT / "tests/fixtures/presentation_defects/corpus.json"
FACTS_PROOF = (
    PROJECT_ROOT
    / "plans/investigations/evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts(org_repo: str) -> ProductFactsV2:
    proof = json.loads(FACTS_PROOF.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == org_repo)
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


def _facts_for_case(case: dict) -> ProductFactsV2 | None:
    if case["origin"] == "synthetic_positive":
        return None
    if "cells" in case["repository"].casefold():
        return _facts("aspose-cells-foss/Aspose.Cells-FOSS-for-Java")
    return _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")


def test_complete_corpus_has_expected_verdicts_rules_and_exact_spans() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    for case in corpus["cases"]:
        candidate = (PROJECT_ROOT / case["source_path"]).read_text(encoding="utf-8")
        result = lint_readme_presentation(candidate, _facts_for_case(case))

        assert result.valid is (case["expected_verdict"] == "ACCEPT"), case["case_id"]
        for expectation in case["findings"]:
            actual_spans = {
                span.text
                for finding in result.findings
                if finding.rule_id == expectation["rule_id"]
                for span in finding.spans
            }
            assert set(expectation["exact_spans"]) <= actual_spans, expectation["finding_id"]


def test_finding_ids_and_spans_are_stable_across_identical_runs() -> None:
    case = next(
        item
        for item in json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["cases"]
        if item["case_id"] == "real.cells-java.visitor-defects"
    )
    candidate = (PROJECT_ROOT / case["source_path"]).read_text(encoding="utf-8")
    facts = _facts_for_case(case)

    first = lint_readme_presentation(candidate, facts)
    second = lint_readme_presentation(candidate, facts)

    assert first == second
    assert len({finding.finding_id for finding in first.findings}) == len(first.findings)
    assert all(
        candidate[span.start : span.end] == span.text
        for finding in first.findings
        for span in finding.spans
    )


def test_visitor_capability_phrase_removes_enum_implementation_suffix() -> None:
    assert visitor_capability_phrase("PDF export via SaveFormat.Pdf") == "PDF export"
    assert visitor_capability_phrase("XPS to PDF conversion") == "XPS to PDF conversion"


def test_code_tokens_and_a_product_specific_strong_readme_are_not_template_gated() -> None:
    candidate = """# Mesh Toolkit

Mesh Toolkit is a Rust library for validating meshes and exporting geometry to OBJ files.

## Example

```rust
let internal_value = Mesh::triangle();
```

## License

MIT
"""
    result = lint_readme_presentation(candidate, None)

    assert result.valid
    assert not result.findings


def test_explained_option_tokens_and_same_bullet_in_distinct_sections_are_allowed() -> None:
    candidate = """# Mesh Toolkit

## Capabilities

- Hyperlinks
- **Flip coordinate system** (`flip_coordinate_system`) — swap Y and Z coordinates

## Test Coverage

- hyperlinks
"""

    result = lint_readme_presentation(candidate, None)

    assert result.valid
    assert not result.findings


def test_duplicate_bullets_inside_one_reader_section_remain_a_failure() -> None:
    candidate = """# Mesh Toolkit

## Supported Formats

### Import

- More formats coming soon...

### Export

- More formats coming soon...
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert [finding.rule_id for finding in result.findings] == ["semantic_duplicate"]


def test_repeated_api_signatures_in_distinct_class_sections_are_not_duplicate_prose() -> None:
    candidate = """# Aspose.Note FOSS for Python

## API Reference

### RichText

- `Text: str`
- `Tags: list[NoteTag]`

### Title

- `Text: str`
- `Tags: list[NoteTag]`

### AttachedFile

- `FileName: str | None`, `Bytes: bytes`

### Image

- `FileName: str | None`, `Bytes: bytes`
"""

    result = lint_readme_presentation(candidate, None)

    assert result.valid
    assert not [finding for finding in result.findings if finding.rule_id == "semantic_duplicate"]


def test_emoji_decoration_fails_outside_code_but_not_inside_code() -> None:
    candidate = """# 📦 Product

```text
✅ preserved in code
```

Inline code is protected: `✅`.
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert [finding.rule_id for finding in result.findings] == ["emoji_decoration"]
    assert [span.text for span in result.findings[0].spans] == ["📦 "]


def test_snake_case_api_name_inside_explanatory_bullet_is_not_an_internal_label() -> None:
    candidate = """# PDF Toolkit

## Capabilities

- **Linearization:** qpdf validates the result with its strict `check_linearization` check.
"""

    result = lint_readme_presentation(candidate, None)

    assert result.valid
    assert not [finding for finding in result.findings if finding.rule_id == "raw_internal_token"]


def test_snake_case_token_used_as_bullet_label_remains_a_failure() -> None:
    candidate = """# Mesh Toolkit

## Options

- `flip_coordinate_system` - Swap Y and Z coordinates
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert [finding.rule_id for finding in result.findings] == ["raw_internal_token"]


def test_repository_verified_public_tool_name_is_allowed_as_code_only_bullet() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    capability = facts.selected_fact("product.capabilities")
    source_revision = capability.source.source_revision
    assert source_revision is not None
    assessment = EvidencePolarityAssessmentV1(
        fact_id=capability.fact_id,
        claim_text="MCP conversion tools",
        expected_polarity="positive_implementation",
        observed_polarity="positive_implementation",
        source_path="src/product/mcp/server.py",
        source_revision=source_revision,
        line_number=1,
        anchor="create_server",
        exact_excerpt="def create_server() -> object:",
        context_excerpt="from .handlers import ps_to_pdf\nserver.tool(ps_to_pdf)",
        accepted=True,
        reason="the server registers the public tool",
    )
    verified_capability = capability.model_copy(update={"evidence_assessments": [assessment]})
    facts = facts.model_copy(
        update={
            "facts": [
                verified_capability if fact.fact_id == capability.fact_id else fact
                for fact in facts.facts
            ]
        }
    )
    candidate = """# Conversion Toolkit

## MCP Tools

- `ps_to_pdf`
"""

    result = lint_readme_presentation(candidate, facts)

    assert result.valid
    assert not [finding for finding in result.findings if finding.rule_id == "raw_internal_token"]


def test_mechanically_verified_public_export_is_allowed_as_code_only_bullet() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    identity = facts.selected_fact("product.identity")
    public_surface = identity.model_copy(
        update={
            "fact_id": "api.public_surface:python-exports",
            "field": "api.public_surface",
            "value": {
                "modules": [
                    {
                        "module": "aspose.page.ps",
                        "exports": ["convert_image_to_eps"],
                    }
                ],
                "classes": [],
            },
            "verification_state": "verified",
        }
    )
    facts = facts.model_copy(update={"facts": [*facts.facts, public_surface]})
    candidate = """# Conversion Toolkit

## Public API

- `convert_image_to_eps`
"""

    result = lint_readme_presentation(candidate, facts)

    assert result.valid
    assert not [finding for finding in result.findings if finding.rule_id == "raw_internal_token"]


def test_rule_inventory_is_complete_and_deterministically_ordered() -> None:
    candidate = PROJECT_ROOT / "tests/fixtures/presentation_defects/strong-existing-content.md"
    result = lint_readme_presentation(candidate.read_text(encoding="utf-8"), None)

    assert result.rules_run == [
        "api_identifier_not_fact_exact",
        "capability_description_repeats_title",
        "competing_primary_examples",
        "cross_product_leakage",
        "emoji_decoration",
        "generic_preservation_heading",
        "heading_not_title_case",
        "internal_assurance_commentary",
        "invalid_third_party_notices",
        "malformed_navigation",
        "noncanonical_technical_abbreviation",
        "promotional_imbalance",
        "promotional_opening",
        "prompt_injection_residue",
        "raw_internal_token",
        "redundant_quick_links",
        "semantic_duplicate",
        "uncollapsed_secondary_detail",
        "unnatural_enterprise_link",
        "visitor_fragment",
    ]


def test_public_contract_rejects_noncanonical_abbreviations_and_sentence_case_headings() -> None:
    candidate = """# Page Converter

## API reference

Convert Ps, eps, xPs, and html files to PdF.

```python
format_name = "Pdf"
```
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert {finding.rule_id for finding in result.findings} == {
        "heading_not_title_case",
        "noncanonical_technical_abbreviation",
    }
    abbreviation_spans = [
        span.text
        for finding in result.findings
        if finding.rule_id == "noncanonical_technical_abbreviation"
        for span in finding.spans
    ]
    assert abbreviation_spans == ["Ps", "eps", "xPs", "html", "PdF"]


def test_public_contract_canonicalizes_api_names_and_rejects_repeated_capability_copy() -> None:
    rendered = canonicalize_public_markdown(
        "### Aspose.PDF.Cgm Namespace (`aspose_pdf.cgm`)\n\n"
        "### Aspose.PDF.Engine.Cms Namespace (`aspose_pdf.engine.cms`)\n\n"
        "### Aspose.PDF.Engine.Sfnt Namespace (`aspose_pdf.engine.sfnt`)\n\n"
        "### Aspose.PDF.Predefined Cmaps Namespace (`aspose_pdf.engine.predefined_cmaps`)\n",
        canonical_abbreviations_from_facts(None),
    )

    assert "Aspose.PDF.CGM Namespace (`aspose_pdf.cgm`)" in rendered
    assert "Aspose.PDF.Engine.CMS Namespace (`aspose_pdf.engine.cms`)" in rendered
    assert "Aspose.PDF.Engine.SFNT Namespace (`aspose_pdf.engine.sfnt`)" in rendered
    assert (
        "Aspose.PDF.Predefined CMaps Namespace (`aspose_pdf.engine.predefined_cmaps`)" in rendered
    )

    candidate = (
        "# PDF Toolkit\n\n## Key Capabilities\n\n"
        "- **Edit text and images in PDF documents** - "
        "Edit text and images in PDF documents.\n"
    )
    result = lint_readme_presentation(candidate, None)

    assert any(
        finding.rule_id == "capability_description_repeats_title" for finding in result.findings
    )


def test_public_contract_rejects_internal_assurance_and_generic_preservation_prose() -> None:
    candidate = """# Page Converter

## Installation

The package was exercised from this exact source revision in an isolated,
network-disabled verification environment. The matching PyPI receipt was empty.

## Preserved Repository Details

Useful source information.
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert {finding.rule_id for finding in result.findings} == {
        "generic_preservation_heading",
        "internal_assurance_commentary",
    }


def test_public_contract_requires_natural_enterprise_edition_anchor() -> None:
    weak = (
        "# Page Converter\n\n## Scope and Limitations\n\n"
        "See [Aspose.Page Enterprise Edition](https://products.aspose.com/page/).\n"
    )
    natural = (
        "# Page Converter\n\n## Scope and Limitations\n\n"
        "For broader requirements, explore the "
        "[full-featured Aspose.Page Enterprise Edition](https://products.aspose.com/page/).\n"
    )

    assert any(
        finding.rule_id == "unnatural_enterprise_link"
        for finding in lint_readme_presentation(weak, None).findings
    )
    assert not any(
        finding.rule_id == "unnatural_enterprise_link"
        for finding in lint_readme_presentation(natural, None).findings
    )


def test_public_contract_learns_repository_abbreviations_from_accepted_facts() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    formats = facts.selected_fact("product.formats")
    values = list(formats.value) if isinstance(formats.value, list) else []
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": [*values, "HEIC export"]})
                if fact.fact_id == formats.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    candidate = "# Image Toolkit\n\n## Key Capabilities\n\nConvert heic files.\n"

    result = lint_readme_presentation(candidate, facts)

    assert any(
        finding.rule_id == "noncanonical_technical_abbreviation"
        and [span.text for span in finding.spans] == ["heic"]
        for finding in result.findings
    )


def test_public_contract_does_not_promote_emphasized_common_words_to_acronyms() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    formats = facts.selected_fact("product.formats")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": ["HEIC export is NOT implemented"]})
                if fact.fact_id == formats.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    candidate = "# Image Toolkit\n\n## Scope and Limitations\n\nHEIC export is not implemented.\n"

    result = lint_readme_presentation(candidate, facts)

    assert not any(
        finding.rule_id == "noncanonical_technical_abbreviation"
        and "not" in [span.text.casefold() for span in finding.spans]
        for finding in result.findings
    )


def test_capability_inventory_cannot_repeat_across_competing_sections() -> None:
    candidate = """# Aspose.Page FOSS for Python

## Why Aspose.Page for Python

- Convert PS/EPS to PDF in Python
- Convert XPS to PNG and JPEG in Python

## Currently Available Features

- PS/EPS to PDF conversion
- XPS to PNG/JPEG conversion
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert any(finding.rule_id == "semantic_duplicate" for finding in result.findings)


def test_capability_inventory_cannot_repeat_inside_collapsed_detail() -> None:
    candidate = """# Aspose.Page FOSS for Python

## Key Capabilities

- **Use PS/EPS to PDF conversion with Aspose.Page for Python** - Supports PS/EPS to PDF conversion.

<details>
<summary>View Detailed Capabilities</summary>

- Convert PS/EPS to PDF in Python

</details>
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert any(finding.rule_id == "semantic_duplicate" for finding in result.findings)


def test_internal_api_assurance_narration_is_not_public_content() -> None:
    candidate = """# Aspose.Page FOSS for Python

## API Reference

The package declares 12 public exports across 3 verified export namespaces.

| Type | Description |
| --- | --- |
| `PsDocument` | Includes 4 additional verified members. |
"""

    result = lint_readme_presentation(candidate, None)

    assert not result.valid
    assert any(finding.rule_id == "internal_assurance_commentary" for finding in result.findings)


def test_real_note_failure_pattern_is_rejected_by_shared_contract() -> None:
    candidate = (
        PROJECT_ROOT / "tests/fixtures/readmes/real_audit_2026-07-17/note-python.md"
    ).read_text(encoding="utf-8")

    result = lint_readme_presentation(candidate, None)
    rule_ids = {finding.rule_id for finding in result.findings}

    assert result.valid is False
    assert {
        "promotional_opening",
        "redundant_quick_links",
        "uncollapsed_secondary_detail",
        "invalid_third_party_notices",
    } <= rule_ids


def test_product_neutral_contract_shape_passes_new_presentation_rules() -> None:
    detail = "\n".join(f"- Verified method {index}" for index in range(1, 14))
    candidate = f"""# Acme Document Toolkit for Python

[![Package](https://img.shields.io/badge/package-current-blue)](https://example.test/package)

Acme Document Toolkit for Python reads document files and exposes their verified structure.

## Navigation

- [API reference](#api-reference)
- [Third-party notices](#third-party-notices)
- [License](#license)

## API Reference

<details>
<summary>Show API reference</summary>

{detail}

</details>

## Third-Party Notices

Dependency terms are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

This project uses the [MIT License](LICENSE), which permits use and modification.
"""

    result = lint_readme_presentation(candidate, None)

    assert result.valid is True
    assert result.findings == []


def test_heading_title_case_normalizes_slash_separated_words() -> None:
    assert (
        title_case_heading("Work with Tables in an MS OneNote Document (Rows/cells)")
        == "Work with Tables in an MS OneNote Document (Rows/Cells)"
    )


def test_dynamic_acronyms_cannot_uppercase_product_identity_words() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    identity = facts.selected_fact("product.identity")
    capabilities = facts.selected_fact("product.capabilities")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "value": {
                            **identity.value,
                            "product_name": "Aspose.Page FOSS for Python",
                            "family": "Page",
                        }
                    }
                )
                if fact.fact_id == identity.fact_id
                else fact.model_copy(update={"value": ["PAGE export"]})
                if fact.fact_id == capabilities.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    rendered = canonicalize_public_markdown(
        'PRODUCT["Aspose.Page FOSS for Python"]\nPDF and eps output.\n',
        canonical_abbreviations_from_facts(facts),
    )

    assert "Aspose.Page FOSS for Python" in rendered
    assert "Aspose.PAGE" not in rendered
    assert "PDF and EPS output" in rendered


def test_api_constant_names_do_not_become_public_abbreviations() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    identity = facts.selected_fact("product.identity")
    api = FactRecordV2(
        fact_id="api.public_surface:vocabulary-test",
        field="api.public_surface",
        value={"modules": [{"module": "aspose.page", "exports": ["DOCUMENT"]}]},
        source=identity.source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )

    rendered = canonicalize_public_markdown(
        "Document conversion with pdf output.",
        canonical_abbreviations_from_facts(facts),
    )

    assert rendered == "Document conversion with PDF output."


def test_public_contract_requires_exact_fact_derived_api_identifier_casing() -> None:
    facts = _facts("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    identity = facts.selected_fact("product.identity")
    api = FactRecordV2(
        fact_id="api.public_surface:identifier-case-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose_pdf.cgm", "exports": ["CgmLoadOptions"]}],
            "classes": [{"module": "aspose_pdf.cgm", "name": "CgmLoadOptions"}],
        },
        source=identity.source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )
    exact = "# PDF Toolkit\n\n## API Reference\n\n### Aspose.PDF.CGM Namespace (`aspose_pdf.cgm`)\n"
    mutated = exact.replace("`aspose_pdf.cgm`", "`aspose_pdf.CGM`")

    assert not any(
        finding.rule_id == "api_identifier_not_fact_exact"
        for finding in lint_readme_presentation(exact, facts).findings
    )
    assert any(
        finding.rule_id == "api_identifier_not_fact_exact"
        and [span.text for span in finding.spans] == ["aspose_pdf.CGM"]
        for finding in lint_readme_presentation(mutated, facts).findings
    )
