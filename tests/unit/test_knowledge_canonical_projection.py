"""Tests for conservative imported-knowledge projection into canonical facts."""

from readme_agent.facts.knowledge_canonical_projection import (
    augment_canonical_formats_with_knowledge,
    project_knowledge_into_canonical_facts,
)
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2


def _source() -> FactSourceV2:
    return FactSourceV2(
        source_type="approved_documentation",
        location="data/imported:3d/net",
        source_revision="abc123",
    )


def _knowledge(field: str, values: list[str], *, state: str = "verified") -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:aspose-knowledge",
        field=field,
        value=[
            {"claim_id": f"3d/net/claim-{index}", "text": text, "confidence": 0.9}
            for index, text in enumerate(values)
        ],
        source=_source(),
        verification_state=state,
        authoritative_owner="aspose.org",
        confidence=0.9,
        affected_surfaces=["readme.capabilities"],
    )


def _canonical(field: str, value, *, state: str = "verified") -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:repository",
        field=field,
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://acme/widget",
            source_revision="abc123",
        ),
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state == "verified" else 0.0,
        affected_surfaces=["readme.capabilities"],
    )


def test_verified_knowledge_projects_into_missing_canonical_fields():
    sources = [
        _knowledge("aspose.feature_claims", ["Transform 3D scenes"]),
        _knowledge(
            "aspose.format_support_claims",
            ["import support for gltf via GltfReader", "export support for pdf via PdfWriter"],
        ),
        _knowledge(
            "aspose.limitation_claims",
            ["Not implemented: Scene.Render() in src/Aspose/Scene.cs:500"],
        ),
    ]

    projected = project_knowledge_into_canonical_facts(sources)

    assert {fact.field for fact in projected} == {
        "product.capabilities",
        "product.formats",
        "product.limitations",
    }
    by_field = {fact.field: fact for fact in projected}
    assert by_field["product.capabilities"].value == ["Transform 3D scenes."]
    assert by_field["product.formats"].value == [
        "Input format: GLTF",
        "Output format: PDF",
    ]
    assert by_field["product.limitations"].value == ["`Scene.Render()` is not implemented."]
    assert all(fact.supporting_fact_ids for fact in projected)


def test_projection_never_overwrites_accepted_canonical_truth():
    source = _knowledge("aspose.feature_claims", ["Transform 3D scenes"])
    canonical = _canonical("product.capabilities", ["Repository capability"])

    assert project_knowledge_into_canonical_facts([source, canonical]) == []


def test_verified_format_knowledge_augments_one_canonical_format_fact():
    source = _knowledge(
        "aspose.format_support_claims",
        [
            "import support for Pdf via Document constructor",
            "export support for SVG format (method name: WriteSVG)",
            "export support for xlsx via XlsxSaveOptions",
        ],
    )
    canonical = _canonical("product.formats", ["Input format: PDF", "Output format: PDF"])

    augmented = augment_canonical_formats_with_knowledge([source, canonical])
    selected = next(fact for fact in augmented if fact.field == "product.formats")

    assert selected.fact_id == canonical.fact_id
    assert selected.source == canonical.source
    assert selected.value == [
        "Input format: PDF",
        "Output format: PDF",
        "Output format: SVG",
        "Output format: XLSX",
    ]
    assert selected.supporting_fact_ids == [source.fact_id]


def test_format_augmentation_fails_closed_for_multiple_canonical_candidates():
    source = _knowledge(
        "aspose.format_support_claims",
        ["export support for SVG format (method name: WriteSVG)"],
    )
    first = _canonical("product.formats", ["Input format: PDF"])
    second = first.model_copy(update={"fact_id": "product.formats:second"})

    candidates = [source, first, second]

    assert augment_canonical_formats_with_knowledge(candidates) == candidates


def test_unverified_knowledge_is_not_promoted():
    source = _knowledge(
        "aspose.limitation_claims",
        ["Not implemented: Scene.Render in src/Aspose/Scene.cs:500"],
        state="unverified",
    )

    assert project_knowledge_into_canonical_facts([source]) == []


def test_unqualified_method_limitation_cannot_override_blocked_mechanical_truth():
    source = _knowledge(
        "aspose.limitation_claims",
        ["Not implemented: Scene.Render in src/Aspose/Scene.cs:500"],
    )
    blocked = _canonical(
        "product.limitations", {"reason": "extractor unavailable"}, state="blocked"
    )
    projected = project_knowledge_into_canonical_facts([source, blocked])

    assert projected == []

    facts = resolve_product_facts(
        "acme/widget",
        [source, blocked, *projected],
        missing_source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://acme/widget",
            source_revision="abc123",
        ),
    )

    selected = facts.selected_fact("product.limitations")
    assert selected.fact_id == "product.limitations:repository"
    assert selected.verification_state == "blocked"
    assert facts.selected_fact(source.field).fact_id == source.fact_id


def test_projection_is_deterministic_and_rejects_internal_assurance_prose():
    source = _knowledge(
        "aspose.feature_claims",
        [
            "Inventoried at the source revision; not executed",
            "Render document pages",
            "Render document pages",
        ],
    )

    first = project_knowledge_into_canonical_facts([source])
    second = project_knowledge_into_canonical_facts([source])

    assert first == second
    assert first[0].value == ["Render document pages."]


def test_format_projection_supports_via_and_method_claims_without_false_formats():
    source = _knowledge(
        "aspose.format_support_claims",
        [
            "import support for Pdf via Document constructor",
            "export support for Xlsx format (method name: SaveXlsx)",
            "export support for SVG format (method name: SaveSvg)",
            "import support for Auto via LoadFormat",
            "import support for hint via hintReader",
            "export support for insert via InsertVisitor",
            "export support for PdfV0 via InternalVersion",
            "export support for xlsx via XlsxSaveOptions",
        ],
    )

    projected = project_knowledge_into_canonical_facts([source])

    assert projected[0].value == [
        "Input format: PDF",
        "Output format: XLSX",
        "Output format: SVG",
    ]


def test_format_projection_normalizes_repository_identifier_aliases():
    source = _knowledge(
        "aspose.format_support_claims",
        [
            "import support for ThreeMf via ThreeMfReader",
            "export support for Microsoft3MF via ThreeMfWriter",
            "export support for Type1 via Type1Writer",
        ],
    )

    projected = project_knowledge_into_canonical_facts([source])

    assert projected[0].value == [
        "Input format: 3MF",
        "Output format: 3MF",
        "Output format: TYPE1",
    ]
