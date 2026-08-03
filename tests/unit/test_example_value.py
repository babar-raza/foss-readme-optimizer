"""Unit tests for deterministic minimal-example value ranking."""

from readme_agent.facts.example_value import (
    ExampleValueSignalsV1,
    VerifiedExampleCandidateV1,
    assess_minimal_example_value,
    rank_verified_minimal_examples,
)

PAGE_OPEN_ONLY = """\
from aspose.page.ps.document import PsDocument

ps = PsDocument.from_file("input.ps")
"""

PAGE_PS_TO_PDF = """\
from pathlib import Path
from aspose.page.ps.document import PsDocument

ps = PsDocument.from_file("input.ps")
Path("output.pdf").write_bytes(ps.to_pdf())
"""

PDF_LIMITS_ONLY = """\
from aspose_pdf import PdfLoadLimits

limits = PdfLoadLimits(
    max_input_bytes=64 * 1024 * 1024,
    max_decoded_stream_bytes=16 * 1024 * 1024,
)
"""

PDF_CREATE_SAVE = """\
from aspose_pdf import Document

document = Document()
document.pages.add()
document.save("output.pdf")
"""

TEX_JOB_RUN = """\
from pathlib import Path
from aspose_tex import TeXJob, TeXOptions, PdfDevice, create_input_source

source = create_input_source("Hello World\\n\\\\bye")
device = PdfDevice(Path("hello.pdf"))
job = TeXJob(source, device, options=TeXOptions(load_format=False))
job.run()
"""


def _candidate(candidate_id: str, code: str) -> VerifiedExampleCandidateV1:
    return VerifiedExampleCandidateV1(
        candidate_id=candidate_id,
        language="python",
        code=code,
        verification_state="verified",
    )


def test_page_open_only_is_setup_not_a_complete_workflow() -> None:
    result = assess_minimal_example_value("python", PAGE_OPEN_ONLY)

    assert result.classification == "setup_only"
    assert result.signals.has_input is True
    assert result.signals.has_meaningful_operation is False
    assert result.signals.has_observable_result is False
    assert result.approval_eligible is False


def test_page_conversion_with_written_output_is_complete() -> None:
    result = assess_minimal_example_value("python", PAGE_PS_TO_PDF)

    assert result.classification == "complete_workflow"
    assert result.signals.has_input is True
    assert result.signals.has_meaningful_operation is True
    assert result.signals.has_observable_result is True
    assert result.approval_eligible is True


def test_pdf_limits_constructor_is_setup_not_a_complete_workflow() -> None:
    result = assess_minimal_example_value("python", PDF_LIMITS_ONLY)

    assert result.classification == "setup_only"
    assert result.signals.has_input is False
    assert result.signals.has_meaningful_operation is False
    assert result.signals.has_observable_result is False
    assert result.approval_eligible is False


def test_pdf_create_and_save_is_complete() -> None:
    result = assess_minimal_example_value("python", PDF_CREATE_SAVE)

    assert result.classification == "complete_workflow"
    assert result.signals.has_meaningful_operation is True
    assert result.signals.has_observable_result is True
    assert result.approval_eligible is True


def test_tex_job_run_with_file_device_is_a_complete_workflow() -> None:
    result = assess_minimal_example_value("python", TEX_JOB_RUN)

    assert result.classification == "complete_workflow"
    assert result.signals.has_meaningful_operation is True
    assert result.signals.has_observable_result is True
    assert result.approval_eligible is True


def test_conversion_without_observable_result_is_not_complete() -> None:
    source = (
        "from aspose.page.ps.document import PsDocument\n"
        'ps = PsDocument.from_file("input.ps")\n'
        "output_pdf = ps.to_pdf()\n"
    )

    result = assess_minimal_example_value("python", source)

    assert result.classification == "operation_without_observable_result"
    assert result.approval_eligible is False


def test_ranking_rejects_page_open_only_when_complete_verified_workflow_exists() -> None:
    selection = rank_verified_minimal_examples(
        [
            _candidate("page.open-only", PAGE_OPEN_ONLY),
            _candidate("page.ps-to-pdf", PAGE_PS_TO_PDF),
        ]
    )

    assert selection.selected_candidate_id == "page.ps-to-pdf"
    assert selection.approval_eligible is True
    open_only = next(row for row in selection.ranked if row.candidate_id == "page.open-only")
    assert open_only.selectable is False
    assert open_only.rejection_reason == "stronger verified complete workflow is available"


def test_ranking_rejects_pdf_limits_only_when_complete_verified_workflow_exists() -> None:
    selection = rank_verified_minimal_examples(
        [
            _candidate("pdf.limits-only", PDF_LIMITS_ONLY),
            _candidate("pdf.create-save", PDF_CREATE_SAVE),
        ]
    )

    assert selection.selected_candidate_id == "pdf.create-save"
    assert selection.approval_eligible is True
    limits_only = next(row for row in selection.ranked if row.candidate_id == "pdf.limits-only")
    assert limits_only.selectable is False


def test_setup_only_fallback_is_visible_but_not_approval_eligible() -> None:
    selection = rank_verified_minimal_examples([_candidate("page.open-only", PAGE_OPEN_ONLY)])

    assert selection.selected_candidate_id == "page.open-only"
    assert selection.approval_eligible is False


def test_equal_value_candidates_use_stable_size_then_id_tie_breaking() -> None:
    selection = rank_verified_minimal_examples(
        [
            _candidate("zeta", PDF_CREATE_SAVE),
            _candidate("alpha", PDF_CREATE_SAVE),
        ]
    )

    assert selection.selected_candidate_id == "alpha"
    assert [row.candidate_id for row in selection.ranked] == ["alpha", "zeta"]


def test_comment_private_api_and_minimality_fail_closed() -> None:
    source = (
        "from package import Document\n"
        "# visitor comment\n"
        "document = Document()\n"
        "document._save('output.pdf')\n"
        + "\n".join(f"value_{index} = {index}" for index in range(20))
    )

    result = assess_minimal_example_value("python", source)

    assert result.classification == "invalid"
    assert result.score == 0
    assert any("source comment" in failure for failure in result.failures)
    assert any("private attribute" in failure for failure in result.failures)
    assert any("nonempty lines" in failure for failure in result.failures)


def test_unverified_complete_workflow_never_outranks_verified_fallback() -> None:
    selection = rank_verified_minimal_examples(
        [
            _candidate("verified.setup", PAGE_OPEN_ONLY),
            VerifiedExampleCandidateV1(
                candidate_id="unverified.complete",
                language="python",
                code=PAGE_PS_TO_PDF,
                verification_state="unverified",
            ),
        ]
    )

    assert selection.selected_candidate_id == "verified.setup"
    assert selection.approval_eligible is False


def test_new_ecosystem_can_supply_an_isolated_evaluator() -> None:
    def evaluator(_source: str) -> ExampleValueSignalsV1:
        return ExampleValueSignalsV1(
            has_input=True,
            has_meaningful_operation=True,
            has_observable_result=True,
        )

    result = assess_minimal_example_value(
        "future-lang",
        "run product workflow",
        evaluators={"future-lang": evaluator},
    )

    assert result.classification == "complete_workflow"
    assert result.approval_eligible is True
