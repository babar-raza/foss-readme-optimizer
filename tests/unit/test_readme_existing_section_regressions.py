"""Real and synthetic controls for reconciling existing README sections."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
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
