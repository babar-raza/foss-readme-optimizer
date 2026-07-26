"""Visitor-facing fact render views never expose internal fact representation."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2

_JAVA_FACTS = (
    Path("plans/investigations/evidence")
    / "level8-local-readme-assessment-composition-b2679e4"
    / "representatives"
    / "java"
    / "bundle"
    / "product-facts-v2.json"
)


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(json.loads(_JAVA_FACTS.read_text(encoding="utf-8")))


def test_identity_and_compatibility_have_explicit_visitor_phrases():
    facts = _facts()

    identity = visitor_fact_render_view(facts, "product.identity")
    compatibility = visitor_fact_render_view(facts, "product.compatibility")

    assert identity is not None
    assert identity.phrases == ["Aspose.Cells FOSS for Java"]
    assert compatibility is not None
    assert compatibility.phrases == ["Requires Java 17 or later."]


def test_internal_relationship_codes_are_not_eligible_prose():
    view = visitor_fact_render_view(_facts(), "relationship.commercial_foss")

    assert view is not None
    assert view.phrases == []
