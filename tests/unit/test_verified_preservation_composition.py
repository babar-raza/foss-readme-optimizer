"""Verify zero-provider composition for strong repository-verified READMEs."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from readme_agent.errors import LLMError
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
)
from readme_agent.readme.agentic_composition_assessment import planning_sections
from readme_agent.readme.agentic_composition_validation import (
    validate_readme_composition_plan,
)
from readme_agent.readme.assessment import assess_readme_document
from readme_agent.readme.capability_semantics import normalize_capability_phrases
from readme_agent.readme.presentation_lint_structure import lint_structure
from readme_agent.readme.presentation_report import product_explanation_offset
from readme_agent.readme.verified_preservation_composition import (
    build_verified_preservation_composition_plan,
)
from readme_agent.state.domain_state import DomainStateV1

ORG_REPO = "example-foss/Aspose.Example-FOSS-for-Python"
REVISION = "a" * 40


def _source_readme(product: str) -> str:
    return f"""# {product} FOSS for Python

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

{product} FOSS for Python helps Python developers process verified product data.

## Navigation

- [At a glance](#at-a-glance)
- [Key capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Development](#development)
- [License](#license)

## At a glance

```mermaid
flowchart LR
  input_1["Verified product data"] --- product["{product} FOSS for Python"]
  product --- capability_1["Repository-verified operations"]
  capability_1 --- output_1["Deterministic output"]
```

## Key capabilities

- Repository-verified format handling.
- Repository-verified product operations.
- Deterministic output suitable for automated workflows.

## Installation

Install from the repository source with `pip install .`.

## Quick Start

```python
from example import Product

result = Product().run("input")
print(result)
```

## Development

Run the repository tests before contributing changes. The maintained source tree includes
public modules, package metadata, examples, and automated tests for the supported behavior.

## License

This project is available under the MIT License. See [LICENSE](LICENSE) for its terms.
"""


def _facts(*, converter: bool) -> ProductFactsV2:
    product = "Aspose.3D" if converter else "Aspose.BarCode"
    values: dict[str, object] = {
        "product.identity": {
            "product_name": product,
            "family": "3d" if converter else "barcode",
            "ecosystem": "python",
        },
        "product.audience": [f"Python developers building {product} applications"],
        "product.problems_solved": [
            (
                "Convert verified 3D assets between supported formats"
                if converter
                else "Generate standards-compliant barcodes from application data"
            )
        ],
        "product.capabilities": (
            [
                "Scene conversion",
                "Mesh inspection",
                "Material processing",
                "Geometry transformation",
                "Scene graph traversal",
                "3D asset serialization",
            ]
            if converter
            else [
                "Barcode generation",
                "Code 128 generation",
                "Code 39 generation",
                "EAN barcode generation",
                "UPC barcode generation",
                "QR Code generation",
            ]
        ),
        "product.formats": (
            [
                "Input formats: OBJ, STL, glTF, 3MF",
                "Output formats: OBJ, STL, glTF, 3MF",
            ]
            if converter
            else [
                "Input formats: text, numeric data, URLs",
                "Output formats: SVG, PNG",
            ]
        ),
        "product.platforms": ["Python"],
        "installation.coordinates": [{"name": "example", "manifest_path": "pyproject.toml"}],
        "installation.verified_acquisition": {
            "method": "source_build",
            "coordinate": {"name": "example"},
        },
        "example.minimal": {
            "language": "python",
            "code": 'from example import Product\nProduct().run("input")',
            "verification_outcome": "verified",
        },
        "documentation.links": ["docs/index.md"],
        "release.state": "maintained",
        "product.limitations": ["Only repository-verified formats are supported."],
        "product.compatibility": [
            {
                "ecosystem": "python",
                "runtime_label": "python",
                "minimum_runtime": ">=3.9",
            }
        ],
        "product.license": "MIT",
        "support.routes": ["GitHub issues"],
        "relationship.commercial_foss": "independent FOSS package",
    }
    records = []
    selected = {}
    for field in REQUIRED_PRODUCT_FIELDS:
        fact_id = f"{field}:primary"
        selected[field] = fact_id
        records.append(
            FactRecordV2(
                fact_id=fact_id,
                field=field,
                value=values[field],
                source=FactSourceV2(
                    source_type="mechanical_repository",
                    location=f"evidence/{field}.json",
                    source_revision=REVISION,
                ),
                verification_state="verified",
                authoritative_owner="repository",
                confidence=1.0,
                affected_surfaces=["readme"],
            )
        )
    return ProductFactsV2(org_repo=ORG_REPO, facts=records, selected_fact_ids=selected)


def _with_fact_values(facts: ProductFactsV2, values: dict[str, object]) -> ProductFactsV2:
    return facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": values[fact.field]})
                if fact.field in values
                else fact
                for fact in facts.facts
            ]
        }
    )


@pytest.mark.parametrize("converter", [False, True], ids=["output-generator", "converter"])
def test_strong_verified_readme_builds_valid_fact_bound_plan(converter):
    facts = _facts(converter=converter)
    source = _source_readme("Aspose.3D" if converter else "Aspose.BarCode")
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)

    plan = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )

    assert plan is not None
    assert plan.model == "deterministic-verified-preservation-v1"
    assert plan.attempt_count == 1
    assert plan.opening_summary is not None
    assert product_explanation_offset(plan.opening_summary.text) == 0
    assert [(item.section_id, item.disposition) for item in plan.section_decisions] == [
        (item.section_id, item.disposition) for item in planning_sections(assessment)
    ]
    assert {item.role for item in plan.diagram.nodes} == {"input", "capability", "output"}
    capability_labels = [item.label for item in plan.diagram.nodes if item.role == "capability"]
    assert capability_labels == normalize_capability_phrases(
        facts.selected_fact("product.capabilities").value
    )
    assert (
        validate_readme_composition_plan(
            plan.model_dump(mode="json"),
            org_repo=ORG_REPO,
            source_text=source,
            facts=facts,
            assessment=assessment,
        )
        == plan
    )


def test_runtime_route_defers_noncompliant_source_shell_to_agentic_composition():
    facts = _facts(converter=True)
    source = _source_readme("Aspose.3D").replace("## At a glance", "## Architecture overview")
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)

    plan = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
        require_presentation_shell=True,
    )

    assert plan is None


@pytest.mark.parametrize(
    ("product_name", "audience", "purpose", "expected"),
    [
        (
            "Aspose.Page",
            "Developers using Python.",
            "PS/EPS to PDF conversion.",
            (
                "Aspose.Page FOSS for Python provides PS/EPS to PDF conversion for "
                "developers using Python."
            ),
        ),
        (
            "Aspose.3D",
            "Python developers building 3D applications",
            "Convert verified 3D assets between supported formats",
            (
                "Aspose.3D FOSS for Python provides Python developers building 3D applications "
                "a way to convert verified 3D assets between supported formats."
            ),
        ),
        (
            "Aspose.BarCode",
            "Barcode teams using Python",
            "Generate standards-compliant barcodes from application data",
            (
                "Aspose.BarCode FOSS for Python provides barcode teams using Python a way to "
                "generate standards-compliant barcodes from application data."
            ),
        ),
    ],
)
def test_opening_is_full_name_fact_cited_natural_product_explanation(
    product_name, audience, purpose, expected
):
    facts = _with_fact_values(
        _facts(converter=product_name == "Aspose.3D"),
        {
            "product.identity": {
                "product_name": product_name,
                "family": product_name.removeprefix("Aspose.").casefold(),
                "ecosystem": "python",
            },
            "product.audience": [audience],
            "product.problems_solved": [purpose],
        },
    )
    source = _source_readme(product_name)
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)

    plan = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )

    assert plan is not None and plan.opening_summary is not None
    assert plan.opening_summary.text == expected
    assert plan.opening_summary.supporting_fact_ids == [
        facts.selected_fact_ids["product.identity"],
        facts.selected_fact_ids["product.audience"],
        facts.selected_fact_ids["product.problems_solved"],
    ]
    assert product_explanation_offset(plan.opening_summary.text) == 0
    assert "http" not in plan.opening_summary.text.casefold()
    assert "enterprise edition" not in plan.opening_summary.text.casefold()


def test_taxonomy_purpose_uses_verified_directional_formats_for_natural_opening():
    facts = _with_fact_values(
        _facts(converter=False),
        {
            "product.identity": {
                "product_name": "Aspose.Note",
                "family": "note",
                "ecosystem": "python",
            },
            "product.audience": ["Developers using Python."],
            "product.problems_solved": ["Document and traversal"],
            "product.formats": [
                "Input format: Microsoft OneNote (.one)",
                "Output format: PDF",
            ],
        },
    )
    problem = facts.selected_fact("product.problems_solved")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={
                        "source": fact.source.model_copy(
                            update={"source_type": "mechanical_repository"}
                        )
                    }
                )
                if fact.fact_id == problem.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )
    source = _source_readme("Aspose.Note")
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)

    plan = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )

    assert plan is not None and plan.opening_summary is not None
    assert plan.opening_summary.text == (
        "Aspose.Note FOSS for Python is an open-source library for developers using Python. "
        "It reads Microsoft OneNote (.one) files and writes PDF files."
    )


def test_page_opening_keeps_later_contextual_enterprise_link_balanced():
    facts = _with_fact_values(
        _facts(converter=False),
        {
            "product.identity": {
                "product_name": "Aspose.Page",
                "family": "page",
                "ecosystem": "python",
            },
            "product.audience": ["Developers using Python."],
            "product.problems_solved": ["PS/EPS to PDF conversion."],
        },
    )
    source = _source_readme("Aspose.Page")
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)
    plan = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )

    assert plan is not None and plan.opening_summary is not None
    contextual = (
        "For additional workflows, see Aspose.Page "
        "[Enterprise Edition](https://products.aspose.com/page/python-net/)."
    )
    candidate = f"# Aspose.Page FOSS for Python\n\n{plan.opening_summary.text}\n\n{contextual}\n"
    findings = lint_structure(candidate)

    assert product_explanation_offset(candidate) is not None
    assert contextual in candidate
    assert "promotional_imbalance" not in {finding.rule_id for finding in findings}


def test_pdf_opening_preserves_action_punctuation_and_bounds_scope():
    capabilities = [
        "Create, load, save, merge, and inspect PDF documents",
        "Add and edit text and images",
        "Extract text and attachments",
        "Render PDF pages to images",
        "PDF/A validation",
    ]
    facts = _with_fact_values(
        _facts(converter=False),
        {
            "product.identity": {
                "product_name": "Aspose.PDF",
                "family": "pdf",
                "ecosystem": "python",
            },
            "product.audience": ["Developers using Python."],
            "product.problems_solved": [capabilities[0]],
            "product.capabilities": capabilities,
        },
    )
    source = _source_readme("Aspose.PDF")
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)

    plan = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )

    assert plan is not None and plan.opening_summary is not None
    summary = plan.opening_summary.text
    assert "create, load, save" in summary
    assert "create load, save" not in summary
    assert "also includes add and edit text and images, and extract text and attachments" in summary
    assert "Render PDF pages" not in summary
    assert "PDF/A validation" not in summary
    diagram_labels = {node.label for node in plan.diagram.nodes if node.role == "capability"}
    assert set(capabilities) <= diagram_labels


def test_weak_readme_and_non_ready_facts_keep_live_composition_path():
    facts = _facts(converter=False)
    weak = "# Aspose.BarCode FOSS for Python\n\nSmall README.\n"
    assessment = assess_readme_document(ORG_REPO, weak, facts, base_revision=REVISION)

    assert (
        build_verified_preservation_composition_plan(
            ORG_REPO,
            weak,
            facts,
            assessment,
            lifecycle_status="FACTS_READY",
        )
        is None
    )
    strong = _source_readme("Aspose.BarCode")
    strong_assessment = assess_readme_document(ORG_REPO, strong, facts, base_revision=REVISION)
    assert (
        build_verified_preservation_composition_plan(
            ORG_REPO,
            strong,
            facts,
            strong_assessment,
            lifecycle_status="FACTS_COLLECTING",
        )
        is None
    )


def test_plan_is_exactly_reusable_and_source_binding_invalidates_it():
    facts = _facts(converter=True)
    source = _source_readme("Aspose.3D")
    assessment = assess_readme_document(ORG_REPO, source, facts, base_revision=REVISION)
    first = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )
    second = build_verified_preservation_composition_plan(
        ORG_REPO,
        source,
        facts,
        assessment,
        lifecycle_status="FACTS_READY",
    )

    assert first is not None and second is not None
    assert first.canonical_hash() == second.canonical_hash()
    with pytest.raises(LLMError, match="binding mismatch"):
        validate_readme_composition_plan(
            first.model_dump(mode="json"),
            org_repo=ORG_REPO,
            source_text=source + "\n",
            facts=facts,
            assessment=assessment,
        )


def test_specialist_uses_zero_provider_plan_before_live_composition(tmp_path, monkeypatch):
    from readme_agent.specialists import readme_presentation

    facts = _facts(converter=False)
    source = _source_readme("Aspose.BarCode")
    readme_path = tmp_path / "README.md"
    readme_path.write_text(source, encoding="utf-8")
    snapshot = SimpleNamespace(
        root_path=tmp_path,
        readme_path="README.md",
        source_revision=REVISION,
    )
    prepared = SimpleNamespace(facts=facts, lifecycle_status="FACTS_READY")
    calls = []

    def dispatch(tool_call, *_args, **kwargs):
        function = tool_call["function"]["name"]
        calls.append(function)
        assert function != "plan_readme_composition"
        plan = kwargs["extra_kwargs"]["agentic_composition_plan"]
        return SimpleNamespace(
            outcome="executed",
            error=None,
            result={
                "needs_write": True,
                "llm_called": True,
                "llm_calls": [{"job": "plan_readme_composition"}],
                "agentic_composition_plan": plan,
            },
        )

    monkeypatch.setattr(readme_presentation, "proposal_only_active", lambda: True)
    monkeypatch.setattr(readme_presentation, "current_repository_snapshot", lambda _repo: snapshot)
    monkeypatch.setattr(
        readme_presentation,
        "load_prepared_product_truth",
        lambda *_args, **_kwargs: prepared,
    )
    monkeypatch.setattr(readme_presentation, "dispatch_tool_call", dispatch)

    result = readme_presentation._render_node(
        DomainStateV1(domain="readme_presentation"),
        {
            "configurable": {
                "org_repo": ORG_REPO,
                "backend": object(),
                "current_revision": REVISION,
            }
        },
    )

    render_result = result["details"]["render_result"]
    assert calls == ["render_readme_candidate"]
    assert render_result["llm_called"] is False
    assert render_result["llm_calls"] == []
    assert render_result["composition_provider_calls"] == 0
    assert render_result["composition_strategy"] == "deterministic_verified_preservation"
