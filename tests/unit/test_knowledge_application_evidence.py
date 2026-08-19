"""`knowledge-application.json` evidence artifact -- the auditable record of
exactly which imported knowledge affected a candidate, where, and why it was
trusted. Tested against the real imported corpus."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.knowledge_application_evidence import (
    KnowledgeApplicationV1,
    build_knowledge_application_report,
)

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
    assert len(report.sections_influenced) > 0
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
    assert report.sections_influenced == ()
