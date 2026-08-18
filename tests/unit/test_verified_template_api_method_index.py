"""T5-R1: the method/property-tier API presentation grounds verified public
methods and properties the source README already named in inline code,
without touching the class-level API Reference table's own deliberate
conciseness contract."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.verified_template_api_method_index import (
    api_method_index_markdown,
)

ROOT = Path(__file__).resolve().parents[2]

_MEMBERS = [
    {
        "name": "open",
        "kind": "method",
        "surface": "open(file_name, options=None)",
        "return_annotation": "None",
        "declared_by": "Scene",
        "inherited": False,
    },
    {
        "name": "close",
        "kind": "method",
        "surface": "close()",
        "return_annotation": "None",
        "declared_by": "Scene",
        "inherited": False,
    },
    {
        "name": "root_node",
        "kind": "property",
        "surface": "root_node: Node",
        "declared_by": "Scene",
        "inherited": False,
    },
]


def _facts_with_api(members: list[dict], *, exclusions: list[dict] | None = None) -> ProductFactsV2:
    base = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests/fixtures/readmes/verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    source = base.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:method-index-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.threed", "exports": ["Scene"]}],
            "classes": [{"module": "aspose.threed", "name": "Scene", "members": []}],
            "coordinate_catalog": {
                "classes": [
                    {
                        "module": "aspose.threed",
                        "name": "Scene",
                        "members": members,
                    }
                ],
                "presentation_exclusions": exclusions or [],
            },
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_method_index"],
    )
    return base.model_copy(
        update={
            "facts": [*base.facts, api],
            "selected_fact_ids": {**base.selected_fact_ids, api.field: api.fact_id},
        }
    )


def test_grounds_a_method_the_source_already_named_bare():
    facts = _facts_with_api(_MEMBERS)
    source_text = "Call `open()` to load a document.\n"

    markdown = api_method_index_markdown(facts, source_text)

    assert markdown is not None
    assert "| `Scene.open(file_name, options=None) -> None` |" in markdown
    assert "<details>" in markdown
    assert "<summary>View documented public members</summary>" in markdown


def test_grounds_a_method_the_source_named_qualified():
    facts = _facts_with_api(_MEMBERS)
    source_text = "Call `Scene.close()` when finished.\n"

    markdown = api_method_index_markdown(facts, source_text)

    assert markdown is not None
    assert "| `Scene.close() -> None` |" in markdown


def test_omits_slot_when_no_source_terms_are_mentioned():
    facts = _facts_with_api(_MEMBERS)

    markdown = api_method_index_markdown(facts, "No inline code mentions here.\n")

    assert markdown is None


def test_omits_slot_when_mentioned_terms_do_not_match_any_verified_member():
    facts = _facts_with_api(_MEMBERS)

    markdown = api_method_index_markdown(facts, "Call `frobnicate()` first.\n")

    assert markdown is None


def test_never_includes_an_unverified_or_unmentioned_member():
    facts = _facts_with_api(_MEMBERS)
    source_text = "Call `open()` to load a document.\n"

    markdown = api_method_index_markdown(facts, source_text)

    assert markdown is not None
    assert "close" not in markdown
    assert "root_node" not in markdown


def test_admits_a_mentioned_property_with_property_appropriate_phrasing():
    facts = _facts_with_api(_MEMBERS)
    source_text = "The `root_node` property exposes the scene graph root.\n"

    markdown = api_method_index_markdown(facts, source_text)

    assert markdown is not None
    assert "| `Scene.root_node: Node` |" in markdown
    assert "Gets the `root_node` property on `Scene`." in markdown
    # No parens on a property identifier, unlike a method's callable form.
    assert "root_node(" not in markdown


def _facts_with_presentation_master_theme() -> ProductFactsV2:
    base = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests/fixtures/readmes/verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    source = base.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:method-index-property-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.slides", "exports": ["Presentation"]}],
            "classes": [{"module": "aspose.slides", "name": "Presentation", "members": []}],
            "coordinate_catalog": {
                "classes": [
                    {
                        "module": "aspose.slides",
                        "name": "Presentation",
                        "members": [
                            {
                                "name": "master_theme",
                                "kind": "property",
                                "surface": "master_theme: Theme",
                                "declared_by": "Presentation",
                                "inherited": False,
                            }
                        ],
                    }
                ],
                "presentation_exclusions": [],
            },
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_method_index"],
    )
    return base.model_copy(
        update={
            "facts": [*base.facts, api],
            "selected_fact_ids": {**base.selected_fact_ids, api.field: api.fact_id},
        }
    )


def test_admits_master_theme_property_mentioned_via_a_bare_attribute_access():
    """Regression for slides' protected-terminology loss: `prs.master_theme`'s
    bare inline-code name is a real property, so it must land in the slot."""

    facts = _facts_with_presentation_master_theme()
    source_text = "Access the master theme through `prs.master_theme`.\n"

    markdown = api_method_index_markdown(facts, source_text)

    assert markdown is not None
    assert "| `Presentation.master_theme: Theme` |" in markdown
    assert "Gets the `master_theme` property on `Presentation`." in markdown


def test_excluded_classes_never_surface_their_members():
    facts = _facts_with_api(
        _MEMBERS,
        exclusions=[
            {
                "import_module": "aspose.threed",
                "name": "Scene",
                "reason": "package_module_alias_is_represented_by_its_namespace_table",
            }
        ],
    )
    source_text = "Call `open()` to load a document.\n"

    markdown = api_method_index_markdown(facts, source_text)

    assert markdown is None


def test_deterministic_ordering_across_repeated_calls():
    members = [
        {
            "name": "zeta",
            "kind": "method",
            "surface": "zeta()",
            "declared_by": "Scene",
            "inherited": False,
        },
        {
            "name": "alpha",
            "kind": "method",
            "surface": "alpha()",
            "declared_by": "Scene",
            "inherited": False,
        },
    ]
    facts = _facts_with_api(members)
    source_text = "Call `alpha()` then `zeta()`.\n"

    first = api_method_index_markdown(facts, source_text)
    second = api_method_index_markdown(facts, source_text)

    assert first == second
    assert first is not None
    assert first.index("Scene.alpha") < first.index("Scene.zeta")


def test_does_not_alter_the_class_level_api_reference_output():
    """The class-level table's own conciseness contract
    (test_api_reference_uses_complete_catalog_without_dumping_every_member_row)
    must remain untouched by this module's existence."""

    from readme_agent.presentation.verified_template_api_reference import (
        api_reference_markdown,
    )

    facts = _facts_with_api(_MEMBERS)

    reference_markdown = api_reference_markdown(facts)

    assert reference_markdown is not None
    assert "Scene.open" not in reference_markdown
    assert "Scene.close" not in reference_markdown
