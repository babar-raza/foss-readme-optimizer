"""RDM-030 (case-only collision): two real classes whose names differ only by
letter case must not render byte-identical (post-casefold) API descriptions."""

from pathlib import Path

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.verified_template_api_reference import api_reference_markdown

ROOT = Path(__file__).resolve().parents[2]


def _base_facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate_json(
        (
            ROOT
            / "tests/fixtures/readmes/verified_source_assurance"
            / "aspose-3d-python-facts-ab1a2267.json"
        ).read_text(encoding="utf-8")
    )


def _with_api_fact(facts: ProductFactsV2, value: dict) -> ProductFactsV2:
    source = facts.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:case-collision-test",
        field="api.public_surface",
        value=value,
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    return facts.model_copy(
        update={
            "facts": [*facts.facts, api],
            "selected_fact_ids": {**facts.selected_fact_ids, api.field: api.fact_id},
        }
    )


def test_case_only_class_name_collision_gets_distinct_descriptions() -> None:
    """Real example from aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET: `ID` and `Id`
    are two genuinely distinct, differently-documented classes declared in the
    same "Core API" module. Neither name matches any `_ROLE_SUFFIXES` entry, so
    both hit `role_sentence()`'s generic fallback, and the presentation
    template's structural validator casefolds descriptions before comparing --
    so even though the rendered text already preserves each type's own casing
    ("Represents an ID..." vs "Represents an Id..."), it still counted as a
    duplicate and broke `presentation_template.py`'s completeness check."""

    facts = _with_api_fact(
        _base_facts(),
        {
            "modules": [{"module": "Core API", "exports": ["ID", "Id"]}],
            "classes": [
                {
                    "module": "Core API",
                    "name": "ID",
                    "members": [
                        {
                            "name": "ToPdf",
                            "kind": "method",
                            "surface": "ToPdf()",
                            "declared_by": "ID",
                            "inherited": False,
                        }
                    ],
                },
                {
                    "module": "Core API",
                    "name": "Id",
                    "members": [
                        {
                            "name": "Original",
                            "kind": "property",
                            "surface": "Original: string",
                            "declared_by": "Id",
                            "inherited": False,
                        }
                    ],
                },
            ],
            "package_namespaces": ["Core API"],
        },
    )

    markdown = api_reference_markdown(facts)

    assert markdown is not None
    rows = [
        line
        for line in markdown.splitlines()
        if line.startswith("| `ID`") or line.startswith("| `Id`")
    ]
    assert len(rows) == 2
    id_row = next(row for row in rows if row.startswith("| `ID`"))
    lower_id_row = next(row for row in rows if row.startswith("| `Id`"))
    assert id_row != lower_id_row
    assert " ".join(id_row.split()).casefold() != " ".join(lower_id_row.split()).casefold()
    assert "`ToPdf`" in id_row
    assert "`Original`" in lower_id_row


def test_non_colliding_descriptions_are_left_unmodified() -> None:
    """Negative control: when descriptions genuinely differ, nothing about the
    disambiguation pass should touch them."""

    facts = _with_api_fact(
        _base_facts(),
        {
            "modules": [{"module": "aspose.threed", "exports": ["Scene"]}],
            "classes": [
                {
                    "module": "aspose.threed",
                    "name": "Scene",
                    "constructor": {"surface": "Scene(file_name=None)"},
                    "members": [],
                }
            ],
            "package_namespaces": ["aspose.threed"],
        },
    )

    markdown = api_reference_markdown(facts)

    assert markdown is not None
    assert "Declares `" not in markdown
    assert "sharing this description" not in markdown
