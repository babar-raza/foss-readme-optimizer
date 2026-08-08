"""Format facts retain the direction needed by visitor-facing diagrams."""

import hashlib
import json

from readme_agent.facts.aspose_org_format_adapter import (
    AsposeOrgFormatEvidenceV1,
    AsposeOrgFormatExtractionV1,
)
from readme_agent.facts.format_direction import (
    block_directionless_format_fact,
    directional_format_fact_from_verified_evidence,
    format_direction_failures,
)
from readme_agent.facts.repository_format_extraction import RepositoryFormatExtractionV1
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2
from readme_agent.registry.models import EvidenceBackedProductFact


def _spec(value: str) -> EvidenceBackedProductFact:
    return EvidenceBackedProductFact(
        value=value,
        evidence_paths=["src/product.py"],
        required_symbols=["Product"],
    )


def test_format_direction_accepts_explicit_input_and_output_claims() -> None:
    assert (
        format_direction_failures(
            [_spec("Input format: Microsoft OneNote (.one)"), _spec("Output format: PDF")]
        )
        == []
    )


def test_format_direction_rejects_a_bare_format_name() -> None:
    failures = format_direction_failures([_spec("Microsoft OneNote (.one)")])

    assert failures == [
        "format direction missing: prefix the claim with 'Input format:', "
        "'Output format:', or both as separate evidence-backed claims"
    ]


def test_directionless_verified_fact_fails_closed_with_repair_detail() -> None:
    fact = FactRecordV2(
        fact_id="product.formats:repository-evidence",
        field="product.formats",
        value=["Microsoft OneNote (.one)"],
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://src",
            source_revision="abc1234",
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.capabilities"],
    )

    blocked = block_directionless_format_fact(fact, [_spec("Microsoft OneNote (.one)")])

    assert blocked.verification_state == "blocked"
    assert blocked.confidence == 0.0
    assert blocked.value["assertions"] == ["Microsoft OneNote (.one)"]
    assert blocked.value["evidence_failures"]


def _verified_example() -> FactRecordV2:
    return FactRecordV2(
        fact_id="example.minimal:verified",
        field="example.minimal",
        value={
            "input_fixture_bindings": [
                {"source_path": "testfiles/input.one", "target_path": "input.one"}
            ]
        },
        source=FactSourceV2(
            source_type="mechanical_test",
            location="local-verifier://example.minimal",
            source_revision="abc1234",
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.example"],
    )


def _native_extraction(
    formats: list[AsposeOrgFormatEvidenceV1],
) -> AsposeOrgFormatExtractionV1:
    dependency_files = {
        "scripts/pipeline/extraction/formats.py": "e" * 64,
        "scripts/pipeline/extraction/tree_helpers.py": "d" * 64,
    }
    payload = json.dumps(
        dependency_files,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return AsposeOrgFormatExtractionV1(
        status="available",
        formats=formats,
        extractor_revision="f" * 40,
        extractor_sha256="e" * 64,
        dependency_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        dependency_files=dependency_files,
        detail="accepted",
    )


def test_directional_fact_combines_consumer_input_and_native_export() -> None:
    extraction = _native_extraction(
        [
            AsposeOrgFormatEvidenceV1(
                format="Pdf",
                direction="export",
                file="src/product.py",
                line=10,
                functional=True,
            ),
            AsposeOrgFormatEvidenceV1(
                format="OneNote2010",
                direction="detect",
                file="src/product.py",
                line=20,
            ),
        ],
    )

    result = directional_format_fact_from_verified_evidence(
        source_revision="abc1234",
        specifications=[_spec("Microsoft OneNote (.one)"), _spec("PDF")],
        example_fact=_verified_example(),
        native_extraction=extraction,
    )

    assert result.verification_state == "verified"
    assert result.value == [
        "Input format: Microsoft OneNote (.one)",
        "Output format: PDF",
    ]
    assert "extractor_sha256=" + "e" * 64 in result.source.location
    assert "dependency_sha256=" in result.source.location
    assert "receipt_sha256=" in result.source.location


def test_directional_fact_fails_closed_without_native_or_consumer_evidence() -> None:
    result = directional_format_fact_from_verified_evidence(
        source_revision="abc1234",
        specifications=[_spec("PDF")],
        example_fact=_verified_example().model_copy(update={"value": {}}),
        native_extraction=AsposeOrgFormatExtractionV1(
            status="unavailable", detail="extractor unavailable"
        ),
    )

    assert result.verification_state == "blocked"
    assert result.value["evidence_failures"]
    assert "aspose-org-extractor" not in result.source.location


def test_directional_fact_expands_native_bidirectional_evidence() -> None:
    result = directional_format_fact_from_verified_evidence(
        source_revision="abc1234",
        specifications=[_spec("XLSX")],
        example_fact=_verified_example().model_copy(update={"value": {}}),
        native_extraction=_native_extraction(
            [
                AsposeOrgFormatEvidenceV1(
                    format="Xlsx",
                    direction="both",
                    file="src/product.py",
                    line=30,
                    functional=True,
                )
            ],
        ),
    )

    assert result.verification_state == "verified"
    assert result.value == ["Input format: XLSX", "Output format: XLSX"]


def test_repository_native_format_evidence_never_claims_sibling_provenance() -> None:
    result = directional_format_fact_from_verified_evidence(
        source_revision="abc1234",
        specifications=[_spec("GLTF")],
        example_fact=_verified_example().model_copy(update={"value": {}}),
        native_extraction=RepositoryFormatExtractionV1(
            status="available",
            formats=[
                AsposeOrgFormatEvidenceV1(
                    format="Gltf",
                    direction="export",
                    file="aspose/threed/formats/gltf/GltfExporter.py",
                    line=23,
                    functional=True,
                )
            ],
            detail="repository-native source and test corroboration",
        ),
    )

    assert result.verification_state == "verified"
    assert result.value == ["Output format: GLTF"]
    assert result.source.location == ("repository://aspose/threed/formats/gltf/GltfExporter.py#L23")
    assert "aspose-org" not in result.source.location


def test_directional_fact_uses_human_3mf_label_for_threemf_source_symbol() -> None:
    result = directional_format_fact_from_verified_evidence(
        source_revision="abc1234",
        specifications=[_spec("3MF - 3D Manufacturing Format")],
        example_fact=_verified_example().model_copy(update={"value": {}}),
        native_extraction=_native_extraction(
            [
                AsposeOrgFormatEvidenceV1(
                    format="ThreeMf",
                    direction="both",
                    file="src/product.py",
                    line=30,
                    functional=True,
                )
            ],
        ),
    )

    assert result.value == [
        "Input format: 3MF - 3D Manufacturing Format",
        "Output format: 3MF - 3D Manufacturing Format",
    ]


def test_directional_fact_rejects_null_functional_native_direction() -> None:
    result = directional_format_fact_from_verified_evidence(
        source_revision="abc1234",
        specifications=[_spec("PDF")],
        example_fact=_verified_example().model_copy(update={"value": {}}),
        native_extraction=_native_extraction(
            [
                AsposeOrgFormatEvidenceV1(
                    format="Pdf",
                    direction="export",
                    file="src/product.py",
                    line=10,
                    functional=None,
                )
            ]
        ),
    )

    assert result.verification_state == "blocked"
    assert result.value["assertions"] == []
