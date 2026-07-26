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


def _facts(ecosystem: str = "java") -> ProductFactsV2:
    path = _JAVA_FACTS.parent.parent.parent / ecosystem / "bundle" / "product-facts-v2.json"
    return ProductFactsV2.model_validate(json.loads(path.read_text(encoding="utf-8")))


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


def test_identity_is_derived_from_product_fields_not_internal_manifest_names():
    view = visitor_fact_render_view(_facts("net"), "product.identity")

    assert view is not None
    assert view.phrases == ["Aspose.3D FOSS for .NET"]
    assert "Converter" not in view.phrases[0]


def test_compatibility_normalizes_repeated_language_and_plus_suffix():
    view = visitor_fact_render_view(_facts("go"), "product.compatibility")

    assert view is not None
    assert view.phrases == ["Requires Go 1.24 or later."]


def test_compatibility_uses_runtime_label_and_preserves_upper_bound():
    facts = _facts("net")
    compatibility = facts.selected_fact("product.compatibility")
    compatibility = compatibility.model_copy(
        update={
            "verification_state": "verified",
            "value": [
                {
                    "ecosystem": "typescript",
                    "runtime_label": "Node.js",
                    "minimum_runtime": ">=18,<22",
                    "manifest_path": "package.json",
                }
            ],
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [
                compatibility if fact.fact_id == compatibility.fact_id else fact
                for fact in facts.facts
            ]
        }
    )

    view = visitor_fact_render_view(facts, "product.compatibility")

    assert view is not None
    assert view.phrases == ["Requires Node.js >=18,<22."]


def test_dotnet_target_framework_has_a_visitor_facing_runtime_name():
    facts = _facts("net")
    compatibility = facts.selected_fact("product.compatibility")
    compatibility = compatibility.model_copy(
        update={
            "verification_state": "verified",
            "value": [
                {
                    "ecosystem": "net",
                    "runtime_label": ".NET",
                    "minimum_runtime": "netcoreapp3.1",
                    "manifest_path": "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj",
                }
            ],
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [
                compatibility if fact.fact_id == compatibility.fact_id else fact
                for fact in facts.facts
            ]
        }
    )

    view = visitor_fact_render_view(facts, "product.compatibility")

    assert view is not None
    assert view.phrases == ["Requires .NET Core 3.1 or later."]


def test_audience_normalizes_internal_ecosystem_token_without_mutating_fact():
    facts = _facts()
    audience = facts.selected_fact("product.audience")
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(
                    update={"value": ["Developers using net for Scene graph management."]}
                )
                if fact.fact_id == audience.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    view = visitor_fact_render_view(facts, "product.audience")

    assert view is not None
    assert view.phrases == ["Developers using .NET for Scene graph management."]
    assert facts.selected_fact("product.audience").value == [
        "Developers using net for Scene graph management."
    ]
