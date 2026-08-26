"""A deep class hierarchy must not restate every base member on every subclass."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.verified_template_api_method_index import (
    api_method_index_markdown,
)

ROOT = Path(__file__).resolve().parents[2]


def _facts_with_classes(classes: list[dict]) -> ProductFactsV2:
    base = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests/fixtures/readmes/verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    api = FactRecordV2(
        fact_id="api.public_surface:inheritance-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.threed", "exports": [item["name"] for item in classes]}],
            "classes": [
                {"module": "aspose.threed", "name": item["name"], "members": []} for item in classes
            ],
            "coordinate_catalog": {
                "classes": [
                    {"module": "aspose.threed", "name": item["name"], "members": item["members"]}
                    for item in classes
                ],
                "presentation_exclusions": [],
            },
        },
        source=base.selected_fact("product.identity").source,
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


def _member(name: str, declared_by: str, *, inherited: bool) -> dict:
    return {
        "name": name,
        "kind": "method",
        "surface": f"{name}(node)",
        "return_annotation": "None",
        "declared_by": declared_by,
        "inherited": inherited,
        "implemented": True,
    }


def test_inherited_restatement_is_withheld_when_the_base_row_is_present() -> None:
    """The HTML Python canary emitted 1,197 of 1,349 rows as inherited restatements
    (189KB of a 206KB section), which pushed the candidate to 264KB and made a single
    table unit exceed the bounded-review packet budget."""

    facts = _facts_with_classes(
        [
            {"name": "Node", "members": [_member("append_child", "Node", inherited=False)]},
            {"name": "Attr", "members": [_member("append_child", "Node", inherited=True)]},
            {"name": "Comment", "members": [_member("append_child", "Node", inherited=True)]},
        ]
    )

    markdown = api_method_index_markdown(facts, "Use `append_child()` to add nodes.\n")

    assert markdown is not None
    # The declaring type keeps its row, so the member stays discoverable.
    assert "`Node.append_child(node) -> None`" in markdown
    # The subclass restatements are withheld -- they said nothing the base row does not.
    assert "`Attr.append_child" not in markdown
    assert "`Comment.append_child" not in markdown


def test_inherited_member_is_kept_when_its_declaring_type_has_no_row() -> None:
    """No information may be lost: if the base type is not itself in the index, the
    subclass row is the only place the member appears and must survive."""

    facts = _facts_with_classes(
        [{"name": "Attr", "members": [_member("append_child", "HiddenBase", inherited=True)]}]
    )

    markdown = api_method_index_markdown(facts, "Use `append_child()` to add nodes.\n")

    assert markdown is not None
    assert "`Attr.append_child" in markdown


def test_members_a_class_declares_itself_are_never_withheld() -> None:
    """Negative control: the rule targets restatement only."""

    facts = _facts_with_classes(
        [
            {"name": "Node", "members": [_member("append_child", "Node", inherited=False)]},
            {"name": "Attr", "members": [_member("append_child", "Attr", inherited=False)]},
        ]
    )

    markdown = api_method_index_markdown(facts, "Use `append_child()` to add nodes.\n")

    assert markdown is not None
    assert "`Node.append_child" in markdown
    assert "`Attr.append_child" in markdown
