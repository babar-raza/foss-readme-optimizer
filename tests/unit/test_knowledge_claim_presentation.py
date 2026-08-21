"""Verified imported-knowledge rendering and exact-coordinate contracts."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.presentation.verified_template_capabilities import (
    build_capability_presentation_plan,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_coordinates import structured_fact_coordinates
from readme_agent.readme.knowledge_claim_presentation import (
    knowledge_capability_items,
    knowledge_installation_items,
    knowledge_limitation_items,
    knowledge_troubleshooting_items,
)

_SOURCE = FactSourceV2(
    source_type="mechanical_repository",
    location="repository://org/repo",
    source_revision="a" * 40,
)
_KNOWLEDGE_SOURCE = FactSourceV2(
    source_type="approved_documentation",
    location="data/imported:pdf/python",
    source_revision="a" * 40,
)
_BASE_VALUES = {
    "product.identity": {
        "product_name": "Aspose.PDF",
        "family": "pdf",
        "platform": "python",
        "repository": "org/repo",
    },
    "product.audience": ["Developers using Python"],
    "product.problems_solved": ["Process PDF files"],
    "product.capabilities": ["Create and inspect PDF documents"],
    "product.formats": ["Input format: PDF", "Output format: PDF"],
}


def _record(field: str, value: object, *, state: str = "verified") -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, "test"),
        field=field,
        value=value,
        source=_KNOWLEDGE_SOURCE if field.startswith("aspose.") else _SOURCE,
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state == "verified" else 0.5,
        affected_surfaces=["readme"],
    )


def _facts(*extra: FactRecordV2) -> ProductFactsV2:
    records = [
        _record(
            field,
            _BASE_VALUES.get(field),
            state="verified" if field in _BASE_VALUES else "missing",
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    extra_fields = {fact.field for fact in extra}
    records = [fact for fact in records if fact.field not in extra_fields]
    records.extend(extra)
    return ProductFactsV2(
        org_repo="org/repo",
        facts=records,
        selected_fact_ids={fact.field: fact.fact_id for fact in records},
    )


def _item(claim_id: str, kind: str, text: str) -> dict[str, object]:
    return {"claim_id": claim_id, "kind": kind, "text": text, "confidence": 1.0}


def test_format_and_limitation_claims_become_public_content_without_internal_paths():
    facts = _facts(
        _record(
            "aspose.format_support_claims",
            [
                _item(
                    "pdf/python/format-1",
                    "format_support",
                    "export support for Pdf via PdfSaveOptions",
                )
            ],
        ),
        _record(
            "aspose.limitation_claims",
            [
                _item(
                    "pdf/python/limit-1",
                    "limitation",
                    "Not implemented: Renderer.execute in src/aspose/pdf/Renderer.py:32",
                )
            ],
        ),
    )

    capabilities = knowledge_capability_items(facts)
    limitations = knowledge_limitation_items(facts)

    assert capabilities[0].markdown == (
        "- **Export to PDF** - Handle PDF output with `PdfSaveOptions`."
    )
    assert limitations[0].markdown == (
        "- `Renderer.execute` is not implemented in this FOSS package."
    )
    assert "src/" not in limitations[0].markdown
    assert ":32" not in limitations[0].markdown


def test_unverified_and_internal_assurance_claims_never_render():
    facts = _facts(
        _record(
            "aspose.feature_claims",
            [_item("pdf/python/feature-1", "feature", "Render PDF using the public API")],
            state="unverified",
        ),
        _record(
            "aspose.troubleshoot_claims",
            [
                _item(
                    "pdf/python/trouble-1",
                    "troubleshoot",
                    "Run the verification fixture from this source revision",
                )
            ],
        ),
    )

    assert knowledge_capability_items(facts) == ()
    assert knowledge_troubleshooting_items(facts) == ()


def test_install_claims_require_exact_verified_coordinate_agreement():
    facts = _facts(
        _record(
            "installation.coordinates",
            [{"name": "aspose-pdf-foss", "version": "1.2.3"}],
        ),
        _record(
            "installation.verified_acquisition",
            {"coordinate": {"name": "aspose-pdf-foss"}, "truth_eligible": True},
        ),
        _record(
            "aspose.install_claims",
            [
                _item("pdf/python/install-1", "install", "Package name is aspose-pdf-foss"),
                _item("pdf/python/install-2", "install", "Current version is 1.2.3"),
                _item("pdf/python/install-3", "install", "Current version is 9.9.9"),
            ],
        ),
    )

    assert [item.markdown for item in knowledge_installation_items(facts)] == [
        "- Package: `aspose-pdf-foss`",
        "- Version: `1.2.3`",
    ]


def test_capability_plan_carries_the_exact_imported_item_coordinate():
    item = _item(
        "pdf/python/format-1",
        "format_support",
        "export support for Pdf via PdfSaveOptions",
    )
    fact = _record("aspose.format_support_claims", [item])
    plan = build_capability_presentation_plan(_facts(fact))
    row = next(row for row in plan.rows if "Export to PDF" in row[0])

    assert row[1] == (fact.fact_id,)
    assert len(row[2]) == 1
    assert row[2][0].fact_id == fact.fact_id
    assert row[2][0].field == fact.field


def test_transformed_limitation_line_reconstructs_its_exact_item_coordinate():
    item = _item(
        "pdf/python/limit-1",
        "limitation",
        "Not implemented: Renderer.execute in src/aspose/pdf/Renderer.py:32",
    )
    fact = _record("aspose.limitation_claims", [item])
    facts = _facts(fact)
    document = knowledge_limitation_items(facts)[0].markdown
    claim = assess_material_claims(document)[0]

    coordinates = structured_fact_coordinates(document, claim, facts, [fact.fact_id])

    assert len(coordinates) == 1
    assert coordinates[0].fact_id == fact.fact_id
    assert coordinates[0].field == fact.field
