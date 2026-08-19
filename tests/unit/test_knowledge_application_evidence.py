"""`knowledge-application.json` evidence artifact -- the auditable record of
exactly which imported knowledge affected a candidate, where, and why it was
trusted. Tested against the real imported corpus."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent.facts.knowledge_application_evidence import (
    KnowledgeApplicationV1,
    build_knowledge_application_report,
)
from readme_agent.facts.schema_v2 import descriptive_fact_id
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import PresentationSpanAdoptionV1, ReadmeDocumentPlanV1

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"
_3D_PYTHON_REPO_SHA = "ee05c1ba9153ef5916b7a108406c794f2e464d01"


def test_build_knowledge_application_report_real_corpus(tmp_path):
    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    assert isinstance(report, KnowledgeApplicationV1)
    assert report.org_repo == "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    assert report.freshness == "current"
    assert report.imported_bundle_repo_sha == _3D_PYTHON_REPO_SHA
    assert report.considered_count == report.selected_count + report.rejected_count
    assert report.considered_count > 1000  # the real 3d/python corpus
    assert report.selected_count > 0
    assert len(report.fact_fields_produced) > 0
    assert len(report.sections_considered) > 0
    assert len(report.sections_selected_for_planning) > 0
    # No document_plan was supplied -- "influenced" must never be guessed
    # from intent, only from a real, surviving render (Gate R5).
    assert report.sections_influenced == ()
    assert report.rendered_output_spans == ()
    assert len(report.dispositions) == report.considered_count


def test_build_knowledge_application_report_is_deterministic(tmp_path):
    """Same corpus + same revision -> byte-identical report every time
    (proves the report can be part of a no-op rerun's zero-new-work proof)."""

    kwargs = dict(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        family="3d",
        platform="python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    first = build_knowledge_application_report(**kwargs)
    second = build_knowledge_application_report(**kwargs)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_build_knowledge_application_report_absent_corpus_degrades_gracefully(tmp_path):
    report = build_knowledge_application_report(
        "some-org/some-repo",
        "nonexistent-family",
        "nonexistent-platform",
        data_root=tmp_path,
        clone_cache=tmp_path,
        source_revision=None,
    )

    assert report.considered_count == 0
    assert report.selected_count == 0
    assert report.fact_fields_produced == ()
    assert report.sections_considered == ()
    assert report.sections_selected_for_planning == ()
    assert report.sections_influenced == ()
    assert report.rendered_output_spans == ()


def _minimal_plan(source: bytes, operations: list) -> ReadmeDocumentPlanV1:
    source_sha = hashlib.sha256(source).hexdigest()
    return ReadmeDocumentPlanV1(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        immutable_base_revision=_3D_PYTHON_REPO_SHA,
        facts_hash=hashlib.sha256(b"facts").hexdigest(),
        template_sha256=hashlib.sha256(b"template").hexdigest(),
        source_sha256=source_sha,
        adoption=PresentationSpanAdoptionV1(
            already_adopted=True,
            source_document_sha256=source_sha,
            source_inner_sha256=source_sha,
            source_inner_bytes=len(source),
            preservation_check="byte_identical",
        ),
        operations=operations,
        candidate_sha256=hashlib.sha256(b"candidate").hexdigest(),
    )


def test_build_knowledge_application_report_influenced_sections_require_a_real_surviving_operation(
    tmp_path,
):
    """Gate R5: `sections_influenced`/`rendered_output_spans` are only ever
    populated from a real document-plan operation whose own `fact_ids`
    cites one of this run's selected fact IDs -- never merely from a
    claim's `intended_section`, which every considered claim carries
    whether selected, rejected, or never rendered."""

    report_without_plan = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )
    selected_field = report_without_plan.fact_fields_produced[0]
    real_fact_id = descriptive_fact_id(selected_field, "aspose-knowledge")
    expected_section = next(
        d.intended_section
        for d in report_without_plan.dispositions
        if d.accepted and d.resulting_fact_field == selected_field
    )

    source = b"# Aspose.3D FOSS for Python\n\nOriginal text.\n"
    citing_operation = build_operation(
        operation_id="readme.test.cite-knowledge-fact",
        operation="insert_after",
        source=source,
        start=len(source),
        end=len(source),
        replacement="Extra capability text.",
        fact_ids=[real_fact_id],
        treatment="preserve",
        rationale="test citation",
    )
    unrelated_operation = build_operation(
        operation_id="readme.test.unrelated",
        operation="insert_after",
        source=source,
        start=0,
        end=0,
        replacement="",
        fact_ids=["some.other.fact:not-from-this-run"],
        treatment="preserve",
        rationale="unrelated citation",
    )
    plan = _minimal_plan(source, [citing_operation, unrelated_operation])

    report_with_plan = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
        document_plan=plan,
    )

    assert expected_section in report_with_plan.sections_influenced
    matching_spans = [
        span for span in report_with_plan.rendered_output_spans if span.fact_id == real_fact_id
    ]
    assert matching_spans
    assert matching_spans[0].operation_id == "readme.test.cite-knowledge-fact"
    assert matching_spans[0].section == expected_section
    assert all(
        span.fact_id != "some.other.fact:not-from-this-run"
        for span in report_with_plan.rendered_output_spans
    )
