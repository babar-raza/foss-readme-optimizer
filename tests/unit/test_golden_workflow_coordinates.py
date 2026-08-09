"""Tests for exact golden-workflow source and candidate coordinates."""

from pathlib import Path

from readme_agent.facts.python_golden_workflow import python_golden_workflow_fact
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_golden_workflow import (
    golden_workflow_development,
)
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability_golden_workflow_coordinates import (
    golden_workflow_fact_coordinates,
)

_ROOT = Path(__file__).parents[2]
_NOTE = _ROOT / "runs" / "baseline" / "aspose-note-foss__Aspose.Note-FOSS-for-Python"
_REVISION = "6d97a522a9ed24708687911f1aabb76e2dea2da7"


def _fact():
    fact = python_golden_workflow_fact(_NOTE, source_revision=_REVISION)
    assert fact is not None
    return fact


def _coordinate_keys(document: str) -> set[tuple[str, str]]:
    fact = _fact()
    encoded = document.encode("utf-8")
    return {
        (coordinate.path, coordinate.value_sha256)
        for claim in assess_material_claims(document)
        for coordinate in golden_workflow_fact_coordinates(
            encoded[claim.source_byte_start : claim.source_byte_end].decode("utf-8"),
            fact.fact_id,
            fact.value,
        )
    }


def test_note_source_workflow_is_covered_by_the_canonical_renderer() -> None:
    source = (_NOTE / "README.md").read_text(encoding="utf-8")
    start = source.index("## PDF golden workflow")
    end = source.index("\n## ", start + 4)
    source_section = source[start:end]
    fact = _fact()
    facts = ProductFactsV2.model_construct(
        org_repo="aspose-note-foss/Aspose.Note-FOSS-for-Python",
        facts=[fact],
        selected_fact_ids={fact.field: fact.fact_id},
    )
    rendered = golden_workflow_development(facts)
    assert rendered is not None
    candidate_section = "\n".join(rendered[1])

    source_coordinates = _coordinate_keys(source_section)
    candidate_coordinates = _coordinate_keys(candidate_section)

    assert source_coordinates
    assert source_coordinates < candidate_coordinates
    assert any(path.endswith("/formatted_richtext") for path, _ in source_coordinates)
    assert any(path.endswith("/simple_table") for path, _ in source_coordinates)
    assert (
        "/failure_output_path",
        next(digest for path, digest in source_coordinates if path == "/failure_output_path"),
    ) in candidate_coordinates


def test_unknown_selected_case_command_has_no_fact_coordinate() -> None:
    fact = _fact()
    coordinates = golden_workflow_fact_coordinates(
        "```bash\npython tools/regenerate_pdf_goldens.py --case invented\n```",
        fact.fact_id,
        fact.value,
    )

    assert coordinates == []
