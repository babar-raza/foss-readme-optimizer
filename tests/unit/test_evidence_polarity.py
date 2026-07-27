"""Revision-bound polarity controls for repository claim evidence."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent.facts.evidence_polarity import assess_evidence_polarity
from readme_agent.facts.policy_evidence import evidence_fact_candidate, limitation_fact_candidate
from readme_agent.facts.schema_v2 import FactRecordV2
from readme_agent.registry.models import EvidenceBackedProductFact


def _spec(value: str, anchor: str, path: str = "src/Scene.cs") -> EvidenceBackedProductFact:
    return EvidenceBackedProductFact(
        value=value,
        evidence_paths=[path],
        required_symbols=[anchor],
    )


@pytest.mark.parametrize("anchor", ["not supported", "incomplete", "only", "out of scope"])
def test_under_specific_constraint_vocabulary_cannot_prove_limitation(
    tmp_path: Path,
    anchor: str,
):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    source.write_text(
        f'public string Status => "Rendering is {anchor}.";\n',
        encoding="utf-8",
    )

    fact = limitation_fact_candidate(
        tmp_path,
        "abc123",
        None,
        [_spec(f"Rendering is {anchor}.", anchor)],
    )

    assert fact.verification_state == "blocked"
    assert "does not identify the claimed subject" in str(fact.value)
    assert fact.evidence_assessments[0].fact_id == fact.fact_id
    assert fact.evidence_assessments[0].accepted is False


def test_positive_symbol_near_explicit_stub_cannot_prove_capability(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    source.write_text(
        "public void Render()\n"
        "{\n"
        '    throw new NotImplementedException("Rendering is not implemented.");\n'
        "}\n",
        encoding="utf-8",
    )

    fact = evidence_fact_candidate(
        tmp_path,
        "abc123",
        None,
        "product.capabilities",
        [_spec("Render scenes.", "Render")],
    )

    assert fact.verification_state == "blocked"
    assert "explicit_constraint contradicts expected positive_implementation" in str(fact.value)
    assert fact.evidence_assessments[0].source_revision == "abc123"
    assert fact.evidence_assessments[0].exact_excerpt == "public void Render()"


def test_full_constraint_excerpt_binds_claim_subject(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    anchor = "Rendering is not supported."
    source.write_text(anchor + "\n", encoding="utf-8")

    fact = limitation_fact_candidate(
        tmp_path,
        "abc123",
        None,
        [_spec(anchor, anchor)],
    )

    assert fact.verification_state == "verified"
    assert fact.value == [anchor]
    assert fact.evidence_assessments[0].accepted is True
    assert fact.evidence_assessments[0].expected_polarity == "explicit_constraint"


def test_deictic_constraint_binds_to_subject_in_bounded_context(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    anchor = "This feature is not available in the FOSS version."
    source.write_text(
        f'public void Render()\n{{\n    throw new NotImplementedException("{anchor}");\n}}\n',
        encoding="utf-8",
    )

    assessment = assess_evidence_polarity(
        root=tmp_path,
        evidence_paths=["src/Scene.cs"],
        anchor=anchor,
        fact_id="product.limitations:repository-evidence",
        claim_text="Rendering functionality is not available.",
        expected_polarity="explicit_constraint",
        source_revision="abc123",
        observed_at=None,
    )

    assert assessment is not None
    assert assessment.accepted is True
    assert assessment.source_revision == "abc123"
    assert assessment.line_number == 3
    assert "public void Render()" in assessment.context_excerpt
    assert assessment.exact_excerpt.endswith(anchor + '");')


def test_opposite_polarity_control_rejects_constraint_as_capability(tmp_path: Path):
    source = tmp_path / "LIMITATIONS.md"
    anchor = "Spreadsheet export is not supported."
    source.write_text(anchor + "\n", encoding="utf-8")

    assessment = assess_evidence_polarity(
        root=tmp_path,
        evidence_paths=["LIMITATIONS.md"],
        anchor=anchor,
        fact_id="product.capabilities:repository-evidence",
        claim_text="Export spreadsheets.",
        expected_polarity="positive_implementation",
        source_revision="abc123",
        observed_at=None,
    )

    assert assessment is not None
    assert assessment.accepted is False
    assert assessment.observed_polarity == "explicit_constraint"


def test_comment_occurrence_cannot_prove_positive_implementation(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    source.write_text("// public Render support is planned.\n", encoding="utf-8")

    assessment = assess_evidence_polarity(
        root=tmp_path,
        evidence_paths=["src/Scene.cs"],
        anchor="Render",
        fact_id="product.capabilities:repository-evidence",
        claim_text="Render scenes.",
        expected_polarity="positive_implementation",
        source_revision="abc123",
        observed_at=None,
    )

    assert assessment is not None
    assert assessment.accepted is False
    assert assessment.observed_polarity == "ambiguous_occurrence"


def test_format_anchor_keeps_its_separate_directional_truth_contract(tmp_path: Path):
    source = tmp_path / "src" / "FileFormat.java"
    source.parent.mkdir()
    source.write_text(
        'public static final String GLTF = "glTF";\n',
        encoding="utf-8",
    )

    fact = evidence_fact_candidate(
        tmp_path,
        "abc123",
        None,
        "product.formats",
        [_spec("Import and export glTF scenes.", '"glTF"', "src/FileFormat.java")],
    )

    assert fact.verification_state == "verified"
    assert fact.evidence_assessments is None


def test_later_implementation_can_supersede_ambiguous_occurrence(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    source.write_text(
        "// Render behavior.\npublic void Render()\n{\n    WriteFrame();\n}\n",
        encoding="utf-8",
    )

    assessment = assess_evidence_polarity(
        root=tmp_path,
        evidence_paths=["src/Scene.cs"],
        anchor="Render",
        fact_id="product.capabilities:repository-evidence",
        claim_text="Render scenes.",
        expected_polarity="positive_implementation",
        source_revision="abc123",
        observed_at=None,
    )

    assert assessment is not None
    assert assessment.accepted is True
    assert assessment.line_number == 2
    assert assessment.observed_polarity == "positive_implementation"


def test_agentic_partial_selection_keeps_only_fully_proved_capabilities(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    source.write_text(
        "public void SaveScene()\n{\n    WriteScene();\n}\n",
        encoding="utf-8",
    )

    fact = evidence_fact_candidate(
        tmp_path,
        "abc123",
        None,
        "product.capabilities",
        [
            _spec("SaveScene output.", "SaveScene"),
            _spec("Render scenes.", "MissingRender"),
        ],
        allow_partial=True,
    )

    assert fact.verification_state == "verified"
    assert fact.value == ["SaveScene output."]
    assert [assessment.anchor for assessment in fact.evidence_assessments] == ["SaveScene"]
    assert all(assessment.accepted for assessment in fact.evidence_assessments)


def test_human_policy_remains_all_or_nothing_when_one_capability_fails(tmp_path: Path):
    source = tmp_path / "src" / "Scene.cs"
    source.parent.mkdir()
    source.write_text("public void SaveScene() {}\n", encoding="utf-8")

    fact = evidence_fact_candidate(
        tmp_path,
        "abc123",
        None,
        "product.capabilities",
        [
            _spec("SaveScene output.", "SaveScene"),
            _spec("Render scenes.", "MissingRender"),
        ],
    )

    assert fact.verification_state == "blocked"
    assert "MissingRender" in str(fact.value)


def test_agentic_partial_selection_does_not_hide_unsupported_limitations(tmp_path: Path):
    source = tmp_path / "LIMITATIONS.md"
    source.write_text("This feature is not supported.\n", encoding="utf-8")

    fact = limitation_fact_candidate(
        tmp_path,
        "abc123",
        None,
        [_spec("Rendering is not supported.", "not supported", "LIMITATIONS.md")],
        allow_partial=True,
    )

    assert fact.verification_state == "blocked"
    assert "does not identify the claimed subject" in str(fact.value)


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"fact_id": "product.formats:wrong"}, "fact ID"),
        ({"expected_polarity": "positive_implementation"}, "polarity"),
        ({"source_revision": "wrong"}, "revision"),
    ],
)
def test_fact_record_rejects_unbound_directional_evidence(tmp_path: Path, update, message):
    source = tmp_path / "LIMITATIONS.md"
    anchor = "Spreadsheet export is not supported."
    source.write_text(anchor + "\n", encoding="utf-8")
    fact = limitation_fact_candidate(
        tmp_path,
        "abc123",
        None,
        [_spec(anchor, anchor, "LIMITATIONS.md")],
    )
    assessment = fact.evidence_assessments[0].model_copy(update=update)

    with pytest.raises(ValidationError, match=message):
        FactRecordV2.model_validate(
            {
                **fact.model_dump(mode="json"),
                "evidence_assessments": [assessment.model_dump(mode="json")],
            }
        )
