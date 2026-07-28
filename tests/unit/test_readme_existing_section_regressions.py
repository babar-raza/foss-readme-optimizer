"""Real and synthetic controls for reconciling existing README sections."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NET_EVIDENCE = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-contextual-linking"
    / "representatives"
    / "net"
)
NET_REVISION = "6a209e8fc3dfc305df39a417037e32a4d4c7b2be"


def _net_facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate_json(
        (NET_EVIDENCE / "product-facts-v2.json").read_text(encoding="utf-8")
    )


def _block_fields(facts: ProductFactsV2, fields: set[str]) -> ProductFactsV2:
    replacements = {
        facts.selected_fact(field).fact_id: facts.selected_fact(field).model_copy(
            update={"verification_state": "blocked", "confidence": 0.0}
        )
        for field in fields
    }
    return facts.model_copy(
        update={"facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts]}
    )


def test_real_net_partial_sections_preserve_maintainer_content_without_fact_duplication():
    facts = _net_facts()
    source = (NET_EVIDENCE / "original-readme.md").read_text(encoding="utf-8")
    limitation = facts.selected_fact("product.limitations")
    example = facts.selected_fact("example.minimal")

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=NET_REVISION,
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert candidate.count("## At a glance") == 1
    assert candidate.count("## Limitations") == 1
    assert candidate.count(limitation.value[0]) == 1
    assert candidate.count(example.value["code"]) == 1
    assert candidate.count("dotnet add package Aspose.3D.FOSS") == 1
    assert "Some advanced features are not available in this FOSS version:" in candidate
    assert "Currently implementing core functionality:" in candidate
    limitation_operation = next(
        operation
        for operation in plan.operations
        if operation.operation_id == "readme.limitations.complete-verified"
    )
    assert limitation_operation.operation == "insert_before"
    assert limitation_operation.fact_ids == [limitation.fact_id]


def test_exact_existing_constraint_and_example_are_not_added_again():
    facts = _net_facts()
    limitation = facts.selected_fact("product.limitations")
    example = facts.selected_fact("example.minimal")
    source = f"""# Aspose.3D FOSS for .NET

Maintainer-authored product explanation.

## Limitations

- {limitation.value[0]}

## Installation

```bash
dotnet add package Aspose.3D.FOSS
```

## Quick Start

```{example.value["language"]}
{example.value["code"]}
```
"""

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=NET_REVISION,
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert candidate.count(limitation.value[0]) == 1
    assert candidate.count(example.value["code"]) == 1
    assert "Maintainer-authored product explanation." in candidate
    assert all(
        not operation.operation_id.startswith(("readme.limitations.", "readme.example."))
        for operation in plan.operations
    )


def test_unresolved_installation_and_example_are_withheld_with_exact_source_traceability():
    facts = _block_fields(
        _net_facts(),
        {"installation.verified_acquisition", "example.minimal"},
    )
    source = """# Aspose.3D FOSS for .NET

Maintainer-authored product explanation.

## Installation

```bash
dotnet add package Unverified.Package
```

## Quick Start

```csharp
var unverified = Product.Create();
```

## Support

Open an issue with a reproducible case.
"""
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision=NET_REVISION,
    )

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=NET_REVISION,
    )
    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid, decision.errors
    assert "Unverified.Package" not in candidate
    assert "Product.Create()" not in candidate
    assert "Open an issue with a reproducible case." in candidate
    investigated = {
        section.heading: section
        for section in assessment.sections
        if section.disposition == "investigate"
    }
    assert set(investigated) >= {"Installation", "Quick Start"}
    withheld = [
        operation
        for operation in plan.operations
        if operation.operation_id.startswith("readme.unresolved.withhold:")
    ]
    assert len(withheld) == 2
    source_bytes = source.encode("utf-8")
    withheld_bytes = {
        source_bytes[operation.source_byte_start : operation.source_byte_end].decode("utf-8")
        for operation in withheld
    }
    assert any(text.startswith("## Installation") for text in withheld_bytes)
    assert any(text.startswith("## Quick Start") for text in withheld_bytes)
    assert all(
        operation.protected_content_treatment == "presentation_policy_correction"
        and not operation.fact_ids
        for operation in withheld
    )
