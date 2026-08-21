"""Canonical fact collection consumes repository-native format evidence."""

from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.repository_format_extraction import RepositoryFormatExtractionV1
from readme_agent.facts.repository_format_facts import repository_format_fact_candidate
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2
from readme_agent.registry.models import EvidenceBackedProductFact


def _fact(field: str, value, *, state: str = "verified") -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:fixture",
        field=field,
        value=value,
        source=FactSourceV2(
            source_type="mechanical_test",
            location=f"fixture://{field}",
            source_revision="a" * 40,
        ),
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state == "verified" else 0.0,
        affected_surfaces=["readme.capabilities"],
    )


def test_repository_native_format_evidence_fills_an_unresolved_fact(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "readme_agent.facts.repository_format_facts.extract_repository_format_directions",
        lambda *_args, **_kwargs: RepositoryFormatExtractionV1(
            status="available",
            formats=[
                AsposeOrgFormatEvidenceV1(
                    format="Pptx",
                    direction="both",
                    file="src/presentation.cpp",
                    line=42,
                    functional=True,
                )
            ],
            detail="current source proof",
        ),
    )

    result = repository_format_fact_candidate(
        tmp_path,
        source_revision="a" * 40,
        family="slides",
        platform="cpp",
        specifications=[],
        candidates=[_fact("example.minimal", {"compiled_consumer": {"accepted": True}})],
    )

    assert result is not None
    assert result.verification_state == "verified"
    assert result.value == ["Input format: PPTX", "Output format: PPTX"]


def test_compiled_example_literals_fill_formats_when_native_extraction_is_unavailable(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "readme_agent.facts.repository_format_facts.extract_repository_format_directions",
        lambda *_args, **_kwargs: RepositoryFormatExtractionV1(
            status="unavailable", detail="no native directions"
        ),
    )
    example = _fact(
        "example.minimal",
        {
            "compiled_consumer": {"accepted": True},
            "code": 'Document document("input.pdf");\nstd::ofstream output("page.png");\n',
        },
    )

    result = repository_format_fact_candidate(
        tmp_path,
        source_revision="a" * 40,
        family="pdf",
        platform="cpp",
        specifications=[
            EvidenceBackedProductFact(value="PDF", evidence_paths=["src/pdf.cpp"]),
            EvidenceBackedProductFact(value="PNG", evidence_paths=["src/png.cpp"]),
        ],
        candidates=[example],
    )

    assert result is not None
    assert result.value == ["Input format: PDF", "Output format: PNG"]


def test_existing_verified_format_fact_prevents_reextraction(monkeypatch, tmp_path: Path) -> None:
    def unexpected(*_args, **_kwargs):
        raise AssertionError("native extraction must not run")

    monkeypatch.setattr(
        "readme_agent.facts.repository_format_facts.extract_repository_format_directions",
        unexpected,
    )

    result = repository_format_fact_candidate(
        tmp_path,
        source_revision="a" * 40,
        family="cells",
        platform="go",
        specifications=[],
        candidates=[
            _fact("product.formats", ["Output format: XLSX"]),
            _fact("example.minimal", {"compiled_consumer": {"accepted": True}}),
        ],
    )

    assert result is None
