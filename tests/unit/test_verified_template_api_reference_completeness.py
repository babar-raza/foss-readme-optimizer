"""Complete-coordinate API reference rendering regressions."""

from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.verified_template_api_reference import api_reference_markdown

ROOT = Path(__file__).resolve().parents[2]


def test_api_reference_uses_complete_catalog_and_lists_every_member_row() -> None:
    facts = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests/fixtures/readmes/verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    source = facts.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:complete-table-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.threed", "exports": ["Scene"]}],
            "classes": [{"module": "aspose.threed", "name": "Scene", "members": []}],
            "package_namespaces": ["aspose", "aspose.threed"],
            "projection_truncated": True,
            "coordinate_catalog": {
                "modules": [
                    {"module": "aspose", "exports": ["threed"]},
                    {"module": "aspose.threed", "exports": ["FileFormat", "Scene"]},
                ],
                "classes": [
                    {
                        "module": "aspose.threed",
                        "name": "FileFormat",
                        "bases": ["Enum"],
                        "members": [
                            {
                                "name": "MS_ONE_NOTE",
                                "kind": "enum_member",
                                "surface": "MS_ONE_NOTE",
                                "declared_by": "FileFormat",
                                "inherited": False,
                            }
                        ],
                    },
                    {
                        "module": "aspose.threed",
                        "name": "Scene",
                        "bases": [],
                        "constructor": {"surface": "Scene(file_name=None)"},
                        "members": [
                            {
                                "name": "open",
                                "kind": "method",
                                "surface": "open(file_name, options=None)",
                                "return_annotation": "None",
                                "declared_by": "Scene",
                                "inherited": False,
                            },
                            {
                                "name": "Open",
                                "kind": "method",
                                "surface": "Open(file_name, options=None)",
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
                        ],
                    },
                ],
                "functions": [],
                "presentation_exclusions": [
                    {
                        "import_module": "aspose",
                        "name": "threed",
                        "reason": "package_module_alias_is_represented_by_its_namespace_table",
                    }
                ],
            },
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    facts = facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )

    markdown = api_reference_markdown(facts)

    assert markdown is not None
    assert markdown.count("| Type | Description |") == 1
    assert "### Aspose Namespace (`aspose`)" not in markdown
    assert "Provides the threed operation" not in markdown
    assert "| `Scene(file_name=None)` |" in markdown
    assert "| `Scene.open(file_name, options=None) -> None` |" in markdown
    assert "| `Scene.Open(file_name, options=None) -> None` |" in markdown
    assert "alongside `open` on `Scene`" in markdown
    assert "| `Scene.root_node: Node` |" in markdown
    assert "| `FileFormat.MS_ONE_NOTE` |" in markdown
    assert "additional member" not in markdown.casefold()
