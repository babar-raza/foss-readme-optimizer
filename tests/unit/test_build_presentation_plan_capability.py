"""Revision-binding tests for the presentation-plan capability."""

import pytest

from readme_agent.capabilities import build_presentation_plan
from readme_agent.errors import ValidationFailure
from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.registry.surface_ownership import default_surface_ownership_map


def test_render_snapshot_revision_must_match_independently_observed_facts(monkeypatch):
    facts = migrate_product_facts_v1(
        ProductFactsV1(
            org_repo="acme/widget",
            family="widget",
            platform="java",
            ecosystem="java",
        ),
        source_revision="new-revision",
    )
    monkeypatch.setattr(
        build_presentation_plan,
        "collect_product_facts",
        lambda org_repo: {
            "product_facts_v2": facts.model_dump(mode="json"),
            "surface_ownership": default_surface_ownership_map().model_dump(mode="json"),
        },
    )

    with pytest.raises(ValidationFailure, match="render snapshot revision"):
        build_presentation_plan.execute(
            "acme/widget",
            original_text="# Widget\n",
            candidate_text="# Widget\n",
            source_revision="old-revision",
        )
