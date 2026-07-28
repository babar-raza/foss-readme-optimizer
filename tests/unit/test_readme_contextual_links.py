"""Prove contextual links and Enterprise terminology through the README document seam."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.catalog import load_aspose_link_catalogs
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


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(json.loads(FACTS_PATH.read_text(encoding="utf-8")))


def test_document_adds_verified_article_and_canonical_enterprise_link_then_noops() -> None:
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
    assert len(plan.contextual_links.bindings) == 1
    binding = plan.contextual_links.bindings[0]
    assert binding.target_url == ("https://kb.aspose.org/3d/python/how-to-get-started-3d-python/")
    assert candidate.count(binding.target_url) == 1
    assert (
        "[Aspose.3D for Python Enterprise Edition](https://products.aspose.com/3d/python-net/)"
    ) in candidate
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
    assert rerun_plan.contextual_links.bindings == []
    assert rerun_plan.contextual_links.omission_reason == "target_already_present"
