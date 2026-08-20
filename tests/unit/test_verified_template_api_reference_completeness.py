"""Complete-coordinate API reference rendering regressions."""

from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.verified_template_api_reference import api_reference_markdown

ROOT = Path(__file__).resolve().parents[2]


def test_api_reference_uses_complete_catalog_without_dumping_every_member_row() -> None:
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
                                "implemented": True,
                            },
                            {
                                "name": "Open",
                                "kind": "method",
                                "surface": "Open(file_name, options=None)",
                                "return_annotation": "None",
                                "declared_by": "Scene",
                                "inherited": False,
                                "implemented": True,
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
    assert "Supports opening content" in markdown
    assert "| `FileFormat` | Enumerates file format values. |" in markdown
    assert "Scene.open" not in markdown
    assert "Scene.root_node" not in markdown
    assert "FileFormat.MS_ONE_NOTE" not in markdown
    assert "API reference under Documentation & Resources" in markdown


def test_api_reference_prefers_complete_catalog_exports_for_selected_namespace() -> None:
    """Q2 (2026-08-19): the bounded planning projection's export list for a
    namespace it already includes can itself be a strict subset of the
    complete evidence catalog's for that same namespace (real cells-python:
    48 vs. 63, silently dropping `Workbook`/`Worksheet`). This must not be
    confused with the classes-catalog fallback covered by the test above,
    which only reaches classes reachable via `complete.get("classes")`
    already keyed to a projected namespace -- here the complete catalog's
    own richer `modules[].exports` entry for the exact same namespace is
    the only source of the missing export at all."""

    facts = ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests/fixtures/readmes/verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )
    source = facts.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:complete-modules-exports-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.threed", "exports": ["Scene"]}],
            "classes": [
                {"module": "aspose.threed", "name": "Scene", "members": []},
            ],
            "package_namespaces": ["aspose", "aspose.threed"],
            "projection_truncated": True,
            "coordinate_catalog": {
                "modules": [
                    {"module": "aspose", "exports": ["threed"]},
                    {"module": "aspose.threed", "exports": ["Scene", "Node"]},
                ],
                "classes": [
                    {
                        "module": "aspose.threed",
                        "name": "Scene",
                        "bases": [],
                        "constructor": {"surface": "Scene(file_name=None)"},
                        "members": [],
                    },
                    {
                        "module": "aspose.threed",
                        "name": "Node",
                        "bases": [],
                        "constructor": {"surface": "Node(name=None)"},
                        "members": [],
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
    assert "The package documents 2 public types across 1 namespaces." in markdown
    assert "| `Node(name=None)` |" in markdown
    assert "| `Scene(file_name=None)` |" in markdown
