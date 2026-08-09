"""Tests for visitor-facing rendering of typed golden-workflow evidence."""

from pathlib import Path

from readme_agent.facts.python_golden_workflow import python_golden_workflow_fact
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_golden_workflow import (
    golden_workflow_development,
)

_ROOT = Path(__file__).parents[2]
_NOTE = _ROOT / "runs" / "baseline" / "aspose-note-foss__Aspose.Note-FOSS-for-Python"
_REVISION = "6d97a522a9ed24708687911f1aabb76e2dea2da7"


def test_renders_complete_public_note_workflow_without_placeholders() -> None:
    fact = python_golden_workflow_fact(_NOTE, source_revision=_REVISION)
    assert fact is not None
    facts = ProductFactsV2.model_construct(
        org_repo="aspose-note-foss/Aspose.Note-FOSS-for-Python",
        facts=[fact],
        selected_fact_ids={fact.field: fact.fact_id},
    )

    rendered = golden_workflow_development(facts)

    assert rendered is not None
    label, lines = rendered
    markdown = "\n".join(lines)
    assert label == "1 repository-native golden workflow"
    assert "13 golden artifacts" in markdown
    assert "semantic manifest" in markdown
    assert "python tools/regenerate_pdf_goldens.py" in markdown
    assert "--case formatted_richtext --case simple_table" in markdown
    assert "python -m unittest tests.test_aspose_note_pdf_goldens -v" in markdown
    assert "tests/out/pdf_golden_failures" in markdown
    assert "require Pillow and use PyMuPDF with fallback to pdftoppm" in markdown
    assert "ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS=1" in markdown
    assert "unless text requires Unicode coverage" in markdown
    assert "<case-id>" not in markdown
