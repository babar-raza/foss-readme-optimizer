"""Document-format role recognition regressions."""

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
)
from readme_agent.readme.format_role_truth import (
    explicit_format_roles,
    mentioned_document_formats,
)


def test_ordinary_lowercase_one_is_not_a_onenote_format() -> None:
    assert mentioned_document_formats("Export workbooks into one cloneable value") == set()


def test_explicit_one_format_forms_remain_recognized() -> None:
    assert mentioned_document_formats("Read ONE files and save a .one document") == {"ONE"}


_SOURCE = FactSourceV2(
    source_type="mechanical_repository",
    location="repository://org/repo",
    source_revision="a" * 40,
)


def _record(field: str, value: object) -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:test",
        field=field,
        value=value,
        source=_SOURCE,
        verification_state="verified" if value is not None else "missing",
        authoritative_owner="repository-source",
        confidence=1.0 if value is not None else 0.5,
        affected_surfaces=["readme"],
    )


def _facts_with(formats: list[str] | None, api_type_names: list[str]) -> ProductFactsV2:
    overrides: dict[str, object] = {
        "api.public_surface": {
            "classes": [{"module": "pkg", "name": name, "members": []} for name in api_type_names]
        }
    }
    if formats is not None:
        overrides["product.formats"] = formats
    records = [
        _record(field, overrides.get(field)) for field in {*REQUIRED_PRODUCT_FIELDS, *overrides}
    ]
    return ProductFactsV2(
        org_repo="org/repo",
        facts=records,
        selected_fact_ids={record.field: record.fact_id for record in records},
    )


def test_public_save_options_type_authorizes_the_output_role() -> None:
    """PF05-FORMAT-ROLE-001: Aspose.Note declares only an input format while shipping
    `examples/export_pdf.py`, `%PDF` output assertions, PDF golden files, and
    `list(SaveFormat) == [SaveFormat.Pdf]`. Scoring roles from `product.formats`
    alone made the presentation lint contradict the repository itself -- the single
    largest blocker in the 2026-08-26 fleet pass."""

    facts = _facts_with(["Input format: Microsoft OneNote (.one)"], ["PdfSaveOptions"])

    roles = explicit_format_roles(facts)

    assert roles["PDF"] == frozenset({"output"})
    # The declared input format keeps its own role and gains no output authority.
    assert "output" not in roles.get("ONENOTE", frozenset())


def test_importer_and_exporter_types_authorize_both_directions() -> None:
    facts = _facts_with(None, ["GltfImporter", "GltfExporter", "FbxLoadOptions"])

    roles = explicit_format_roles(facts)

    assert roles["GLTF"] == frozenset({"input", "output"})
    assert roles["FBX"] == frozenset({"input"})


def test_api_evidence_never_invents_a_role_for_an_unknown_format() -> None:
    """Negative control: a type whose prefix is not a governed document format grants
    nothing, so a role cannot be conjured from an arbitrary class name."""

    facts = _facts_with(None, ["WidgetSaveOptions", "ImageSaveOptions", "SaveOptions"])

    assert explicit_format_roles(facts) == {}


def test_declared_formats_still_win_when_no_api_evidence_exists() -> None:
    facts = _facts_with(["Load and save STL"], [])

    assert explicit_format_roles(facts)["STL"] == frozenset({"input", "output"})
