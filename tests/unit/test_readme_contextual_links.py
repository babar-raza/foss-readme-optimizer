"""Prove contextual links and Enterprise terminology through the README document seam."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.catalog import load_aspose_link_catalogs
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.registry.models import LinkAllocationPolicyV1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTS_PATH = (
    PROJECT_ROOT
    / "plans/investigations/evidence/level8-readme-header-visual-contract"
    / "representatives/python/product-facts-v2.json"
)
ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REPRESENTATIVE_ROOT = (
    PROJECT_ROOT
    / "plans/investigations/evidence/level8-readme-header-visual-contract/representatives"
)


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(json.loads(FACTS_PATH.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def catalogs() -> AsposeLinkCatalogSetV1:
    return load_aspose_link_catalogs()


def test_document_prioritizes_verified_product_relationship_then_noops() -> None:
    facts = _facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    source = """# Aspose.3D FOSS for Python

Maintainer introduction.

## Quick start

Run the minimal example below.

## Editions

For a broader feature set, see the [commercial On-Premise edition](https://products.aspose.com/3d/python-net/).
"""
    catalogs = load_aspose_link_catalogs()
    policy = LinkAllocationPolicyV1()

    candidate, plan = build_readme_document_candidate(
        ORG_REPO,
        source,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )

    assert validation.valid, validation.errors
    assert plan.contextual_links is not None
    assert len(plan.contextual_links.bindings) == 2
    assert {binding.context_kind for binding in plan.contextual_links.bindings} == {"relationship"}
    assert {binding.target_url for binding in plan.contextual_links.bindings} == {
        "https://products.aspose.org/3d/python/",
        "https://products.aspose.com/3d/python-net/",
    }
    assert "[Aspose.3D Enterprise Edition](https://products.aspose.com/3d/python-net/)" in candidate
    assert "Aspose.3D FOSS for Python" in candidate
    assert "## Scope and limitations" in candidate
    assert candidate.count("products.aspose.org") == 1
    assert candidate.count("products.aspose.com") == 1
    assert "https://kb.aspose.org/3d/python/how-to-get-started-3d-python/" not in candidate
    assert "commercial On-Premise edition" not in candidate

    rerendered, rerun_plan = build_readme_document_candidate(
        ORG_REPO,
        candidate,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )

    assert rerendered == candidate
    assert rerun_plan.contextual_links is not None
    assert rerun_plan.contextual_links.omission_reason in {"none", "budget_exhausted"}
    assert rerun_plan.operations == []


def test_configured_single_link_slot_prefers_enterprise_product_context() -> None:
    facts = _facts()
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None
    policy = LinkAllocationPolicyV1.model_validate(
        {
            "mode": "configured",
            "max_total": 1,
            "domain_maxima": {"aspose.org": 1, "aspose.com": 1},
            "surface_maxima": {
                "products": 1,
                "docs": 0,
                "kb": 0,
                "blog": 0,
                "reference": 0,
            },
        }
    )
    candidate, plan = build_readme_document_candidate(
        ORG_REPO,
        "# Aspose.3D FOSS for Python\n\n## Quick start\n\nExisting guidance.\n",
        facts,
        base_revision=revision,
        link_catalogs=load_aspose_link_catalogs(),
        link_allocation_policy=policy,
    )

    assert plan.contextual_links is not None
    assert len(plan.contextual_links.bindings) == 1
    binding = plan.contextual_links.bindings[0]
    assert binding.context_kind == "relationship"
    assert binding.parent_domain == "aspose.com"
    assert candidate.count("products.aspose.com") == 1
    assert "products.aspose.org" not in candidate


@pytest.mark.parametrize("platform", ["python", "net", "java", "cpp", "typescript", "rust", "go"])
@pytest.mark.parametrize(
    "policy",
    [
        LinkAllocationPolicyV1(),
        LinkAllocationPolicyV1.model_validate(
            {
                "mode": "configured",
                "max_total": 6,
                "domain_maxima": {"aspose.org": 3, "aspose.com": 4},
                "surface_maxima": {
                    "products": 2,
                    "docs": 2,
                    "kb": 2,
                    "blog": 1,
                    "reference": 2,
                },
            }
        ),
    ],
    ids=["auto", "configured"],
)
def test_seven_real_representatives_validate_and_noop_under_both_allocation_modes(
    platform: str,
    policy: LinkAllocationPolicyV1,
    catalogs: AsposeLinkCatalogSetV1,
) -> None:
    root = REPRESENTATIVE_ROOT / platform
    facts = ProductFactsV2.model_validate(
        json.loads((root / "product-facts-v2.json").read_text(encoding="utf-8"))
    )
    source = (root / "original-readme.md").read_text(encoding="utf-8")
    revision = facts.selected_fact("product.identity").source.source_revision
    assert revision is not None

    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    validation = validate_readme_document_candidate(
        source,
        candidate,
        plan,
        facts,
        link_catalogs=catalogs,
    )

    assert validation.valid, validation.errors
    assert plan.contextual_links is not None
    assert plan.contextual_links.bindings or plan.contextual_links.omission_reason != "none"

    rerendered, rerun_plan = build_readme_document_candidate(
        facts.org_repo,
        candidate,
        facts,
        base_revision=revision,
        link_catalogs=catalogs,
        link_allocation_policy=policy,
    )
    assert rerendered == candidate
    assert rerun_plan.contextual_links is not None
    assert rerun_plan.operations == []
