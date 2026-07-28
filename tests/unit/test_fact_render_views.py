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
    assert identity.citation_fact_ids == [identity.fact_id]
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


def test_unknown_product_family_has_a_generic_visitor_identity():
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    value = dict(identity.value)
    value["family"] = "mesh-toolkit"
    identity = identity.model_copy(update={"value": value})
    facts = facts.model_copy(
        update={
            "facts": [
                identity if fact.fact_id == identity.fact_id else fact for fact in facts.facts
            ]
        }
    )

    view = visitor_fact_render_view(facts, "product.identity")

    assert view is not None
    assert view.phrases == ["Mesh Toolkit FOSS for Java"]


def test_compatibility_normalizes_repeated_language_and_plus_suffix():
    view = visitor_fact_render_view(_facts("go"), "product.compatibility")

    assert view is not None
    assert view.phrases == ["Requires Go 1.24 or later."]


def test_manifest_format_enums_are_rendered_as_visitor_prose():
    facts = _facts()
    formats = facts.selected_fact("product.formats")
    formats = formats.model_copy(
        update={
            "verification_state": "verified",
            "value": [
                "Load formats: AUTO, XLSX",
                "Save format: XLSX",
                "Supported formats: XLSX, XLSB",
            ],
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [formats if fact.fact_id == formats.fact_id else fact for fact in facts.facts]
        }
    )

    view = visitor_fact_render_view(facts, "product.formats")

    assert view is not None
    assert view.phrases == [
        "Reads XLSX files",
        "Writes XLSX files",
        "Supports XLSX and XLSB files",
    ]


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


def test_typescript_compiler_target_is_not_presented_as_a_runtime_minimum():
    facts = _facts("net")
    compatibility = facts.selected_fact("product.compatibility")
    compatibility = compatibility.model_copy(
        update={
            "verification_state": "verified",
            "value": [
                {
                    "ecosystem": "typescript",
                    "runtime_label": "ECMAScript",
                    "minimum_runtime": "ES2020",
                    "compatibility_kind": "compiler_target",
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
    assert view.phrases == ["Targets ECMAScript ES2020."]


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


def test_compatibility_is_scoped_to_the_package_users_acquire():
    facts = _facts("net")
    compatibility = facts.selected_fact("product.compatibility")
    compatibility = compatibility.model_copy(
        update={
            "verification_state": "verified",
            "value": [
                {
                    "ecosystem": "net",
                    "runtime_label": ".NET",
                    "minimum_runtime": "net10.0",
                    "manifest_path": "src/converter/Converter.csproj",
                },
                {
                    "ecosystem": "net",
                    "runtime_label": ".NET",
                    "minimum_runtime": "netcoreapp3.1",
                    "manifest_path": "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj",
                },
                {
                    "ecosystem": "net",
                    "runtime_label": ".NET",
                    "minimum_runtime": "net10.0",
                    "manifest_path": "src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj",
                },
            ],
        }
    )
    coordinates = facts.selected_fact("installation.coordinates")
    coordinates = coordinates.model_copy(
        update={
            "value": [
                {
                    "name": "Aspose.3D.Converter",
                    "manifest_path": "src/converter/Converter.csproj",
                },
                {
                    "name": "Aspose.3D.FOSS",
                    "manifest_path": "src/main/Aspose.ThreeD/Aspose.ThreeD.csproj",
                },
                {
                    "name": "Aspose.3D.Tests",
                    "manifest_path": "src/test/Aspose.ThreeD.Tests/Aspose.ThreeD.Tests.csproj",
                },
            ]
        }
    )
    acquisition = facts.selected_fact("installation.verified_acquisition")
    acquisition = acquisition.model_copy(
        update={
            "verification_state": "verified",
            "value": {
                "method": "nuget",
                "outcome": "REGISTRY_VERIFIED",
                "coordinate": {"name": "Aspose.3D.FOSS"},
            },
        }
    )
    replacements = {
        compatibility.fact_id: compatibility,
        coordinates.fact_id: coordinates,
        acquisition.fact_id: acquisition,
    }
    facts = facts.model_copy(
        update={"facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts]}
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


def test_verified_natural_lowercase_problem_phrase_is_preserved():
    facts = _facts()
    problem = facts.selected_fact("product.problems_solved")
    natural_phrase = "creating, reading, and modifying document files"
    facts = facts.model_copy(
        update={
            "facts": [
                fact.model_copy(update={"value": [natural_phrase]})
                if fact.fact_id == problem.fact_id
                else fact
                for fact in facts.facts
            ]
        }
    )

    view = visitor_fact_render_view(facts, "product.problems_solved")

    assert view is not None
    assert view.phrases == [natural_phrase]


def test_agent_drafted_audience_requires_persisted_grounding_citations():
    facts = _facts()
    identity = facts.selected_fact("product.identity")
    audience = facts.selected_fact("product.audience")
    without_citations = audience.model_copy(
        update={
            "source": audience.source.model_copy(update={"source_type": "agent_drafted"}),
            "value": ["Developers using Java."],
            "supporting_fact_ids": [],
        }
    )
    blocked = facts.model_copy(
        update={
            "facts": [
                without_citations if fact.fact_id == audience.fact_id else fact
                for fact in facts.facts
            ]
        }
    )

    assert visitor_fact_render_view(blocked, "product.audience") is None

    grounded = without_citations.model_copy(update={"supporting_fact_ids": [identity.fact_id]})
    accepted = blocked.model_copy(
        update={
            "facts": [
                grounded if fact.fact_id == audience.fact_id else fact for fact in blocked.facts
            ]
        }
    )
    view = visitor_fact_render_view(accepted, "product.audience")

    assert view is not None
    assert view.phrases == ["Developers using Java."]
    assert view.citation_fact_ids == [audience.fact_id, identity.fact_id]


def test_internal_tokens_and_arbitrary_nested_values_have_no_render_view():
    facts = _facts()
    capabilities = facts.selected_fact("product.capabilities")
    problems = facts.selected_fact("product.problems_solved")
    replacements = {
        capabilities.fact_id: capabilities.model_copy(update={"value": ["scene_graph"]}),
        problems.fact_id: problems.model_copy(update={"value": {"manifest_key": "internal_value"}}),
    }
    unsafe = facts.model_copy(
        update={"facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts]}
    )

    assert visitor_fact_render_view(unsafe, "product.capabilities") is None
    assert visitor_fact_render_view(unsafe, "product.problems_solved") is None
