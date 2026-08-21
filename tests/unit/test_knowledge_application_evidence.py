"""`knowledge-application.json` evidence artifact -- the auditable record of
exactly which imported knowledge affected a candidate, where, and why it was
trusted. Tested against the real imported corpus."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.knowledge_application_evidence import (
    FinalKnowledgeItemDispositionV1,
    KnowledgeApplicationV1,
    RenderedOutputSpanV1,
    build_knowledge_application_report,
)
from readme_agent.facts.schema_v2 import descriptive_fact_id
from readme_agent.readme.claim_accountability_coordinates import (
    structured_list_item_coordinate,
)
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    PresentationSpanAdoptionV1,
    ReadmeDocumentPlanV1,
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


def test_candidate_content_provenance_produces_a_rendered_span_with_zero_operation_fact_ids(
    tmp_path,
):
    """Verified-template production commonly carries its real per-fact
    lineage only in `candidate_content_provenance` -- its own compile
    operation cites no `fact_ids` at all. K3-2: the report must join both
    channels, not operations alone."""

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
    candidate_text = "# Aspose.3D FOSS for Python\n\nCompiled capability text.\n"
    compile_operation = build_operation(
        operation_id="readme.verified-template.compile",
        operation="replace",
        source=source,
        start=0,
        end=len(source),
        replacement=candidate_text,
        fact_ids=[],  # the real, observed shape: zero operation-level fact_ids
        treatment="presentation_policy_correction",
        rationale="compile the verified-template contract",
    )
    span_start = candidate_text.index("Compiled capability text.")
    span_end = span_start + len(b"Compiled capability text.")
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.capabilities.claim:1",
        candidate_byte_start=span_start,
        candidate_byte_end=span_end,
        fact_ids=[real_fact_id],
        rationale="capability sentence bound to the selected accepted fact",
    )
    plan = _minimal_plan(source, [compile_operation])
    plan = plan.model_copy(update={"candidate_content_provenance": [provenance]})

    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
        document_plan=plan,
        candidate_text=candidate_text,
        status="final",
    )

    assert expected_section in report.sections_influenced
    provenance_spans = [
        span
        for span in report.rendered_output_spans
        if span.operation_id == provenance.provenance_id
    ]
    assert len(provenance_spans) == 1
    span = provenance_spans[0]
    assert span.fact_id == real_fact_id
    assert span.candidate_byte_start == span_start
    assert span.candidate_byte_end == span_end
    assert (
        span.replacement_sha256
        == hashlib.sha256(candidate_text.encode("utf-8")[span_start:span_end]).hexdigest()
    )


def test_final_report_binds_source_revision_facts_hash_plan_hash_and_candidate_sha256(tmp_path):
    source = b"# Aspose.3D FOSS for Python\n\nOriginal text.\n"
    plan = _minimal_plan(source, [])

    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
        document_plan=plan,
        candidate_text="# Aspose.3D FOSS for Python\n\nOriginal text.\n",
        status="final",
    )

    assert report.status == "final"
    assert report.source_revision == _3D_PYTHON_REPO_SHA
    assert report.facts_hash == plan.facts_hash
    assert report.candidate_sha256 == plan.candidate_sha256
    assert report.document_plan_hash is not None
    assert len(report.document_plan_hash) == 64


def _synthetic_selection_result(field: str = "aspose.feature_claims"):
    """One output-authorizing (accepted, verified, corroborated) claim for
    `field`, plus a matching minimal `FactRecordV2` -- real-corpus tests
    above use `select_knowledge_claims()` unmocked, but corroboration there
    always resolves `uncorroborated` without a real product-repo clone at
    `clone_cache`, so any test asserting genuine output-authorizing state
    needs this synthetic, fully-controlled fixture instead."""

    from readme_agent.facts.aspose_knowledge_selection import (
        KnowledgeClaimDispositionV1,
        KnowledgeSelectionResultV1,
    )
    from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2

    disposition = KnowledgeClaimDispositionV1(
        global_claim_id="3d/python/CLM-synthetic-0001",
        family="3d",
        platform="python",
        kind="feature",
        source_revision=_3D_PYTHON_REPO_SHA,
        freshness="current",
        corroboration="corroborated",
        intended_section="Key Capabilities",
        accepted=True,
        resulting_fact_field=field,
        verification_state="verified",
    )
    item = {
        "claim_id": disposition.global_claim_id,
        "kind": "feature",
        "text": "Synthetic capability text.",
        "confidence": 1.0,
    }
    fact_record = FactRecordV2(
        fact_id=descriptive_fact_id(field, "aspose-knowledge"),
        field=field,
        value=[item],
        source=FactSourceV2(
            source_type="approved_documentation",
            location="synthetic-fixture",
            source_revision=_3D_PYTHON_REPO_SHA,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["capabilities"],
    )
    return KnowledgeSelectionResultV1(
        family="3d",
        platform="python",
        source_revision=_3D_PYTHON_REPO_SHA,
        bundle_repo_sha=_3D_PYTHON_REPO_SHA,
        freshness="current",
        load_findings=(),
        dispositions=(disposition,),
        fact_records=(fact_record,),
    )


def test_provisional_report_without_a_document_plan_marks_every_authorizing_item_not_applicable(
    tmp_path, monkeypatch
):
    import readme_agent.facts.knowledge_application_evidence as module

    monkeypatch.setattr(
        module, "select_knowledge_claims", lambda *a, **k: _synthetic_selection_result()
    )

    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    assert report.status == "provisional"
    assert len(report.final_dispositions) == 1
    entry = report.final_dispositions[0]
    assert entry.disposition == "not_applicable_with_reason"
    assert "provisional" in entry.reason


def test_final_report_marks_uncited_authorizing_item_intentionally_omitted(tmp_path, monkeypatch):
    import readme_agent.facts.knowledge_application_evidence as module

    monkeypatch.setattr(
        module, "select_knowledge_claims", lambda *a, **k: _synthetic_selection_result()
    )
    source = b"# Aspose.3D FOSS for Python\n\nOriginal text.\n"
    plan = _minimal_plan(source, [])  # no operations cite anything

    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
        document_plan=plan,
        candidate_text="# Aspose.3D FOSS for Python\n\nOriginal text.\n",
        status="final",
    )

    assert len(report.final_dispositions) == 1
    entry = report.final_dispositions[0]
    assert entry.disposition == "intentionally_omitted_with_evidence"
    assert entry.reason.strip()
    assert entry.output_spans == ()


def test_final_report_output_authorizing_item_rendered_via_a_real_span_never_omitted(
    tmp_path, monkeypatch
):
    """The exact false-positive KGAP-002 shows the mirror image of: a claim
    demonstrably cited by a real operation must be `rendered_with_exact_spans`
    -- proof by actual usage always wins over the item-level re-check."""

    import readme_agent.facts.knowledge_application_evidence as module

    field = "aspose.feature_claims"
    monkeypatch.setattr(
        module, "select_knowledge_claims", lambda *a, **k: _synthetic_selection_result(field)
    )
    source = b"# Aspose.3D FOSS for Python\n\nOriginal text.\n"
    candidate_text = "# Aspose.3D FOSS for Python\n\nSynthetic capability text.\n"
    real_fact_id = descriptive_fact_id(field, "aspose-knowledge")
    item = {
        "claim_id": "3d/python/CLM-synthetic-0001",
        "kind": "feature",
        "text": "Synthetic capability text.",
        "confidence": 1.0,
    }
    coordinate = structured_list_item_coordinate(real_fact_id, field, item)
    start = candidate_text.index("Synthetic capability text.")
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.capabilities.claim:1",
        candidate_byte_start=start,
        candidate_byte_end=start + len("Synthetic capability text."),
        fact_ids=[real_fact_id],
        fact_coordinates=[coordinate],
        rationale="exact selected knowledge item rendered in the capability section",
    )
    plan = _minimal_plan(source, []).model_copy(
        update={"candidate_content_provenance": [provenance]}
    )

    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
        document_plan=plan,
        candidate_text=candidate_text,
        status="final",
    )

    assert len(report.final_dispositions) == 1
    entry = report.final_dispositions[0]
    assert entry.disposition == "rendered_with_exact_spans"
    assert entry.output_spans


def test_one_rendered_item_never_promotes_an_unrendered_verified_sibling(tmp_path, monkeypatch):
    import readme_agent.facts.knowledge_application_evidence as module

    result = _synthetic_selection_result()
    first_disposition = result.dispositions[0]
    second_disposition = first_disposition.model_copy(
        update={"global_claim_id": "3d/python/CLM-synthetic-0002"}
    )
    first_item = result.fact_records[0].value[0]
    second_item = {
        "claim_id": second_disposition.global_claim_id,
        "kind": "feature",
        "text": "A separate verified capability.",
        "confidence": 1.0,
    }
    fact = result.fact_records[0].model_copy(update={"value": [first_item, second_item]})
    result = result.model_copy(
        update={
            "dispositions": (first_disposition, second_disposition),
            "fact_records": (fact,),
        }
    )
    monkeypatch.setattr(module, "select_knowledge_claims", lambda *a, **k: result)

    candidate_text = "# Product\n\nSynthetic capability text.\n"
    start = candidate_text.index("Synthetic capability text.")
    first_coordinate = structured_list_item_coordinate(fact.fact_id, fact.field, first_item)
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.section.capabilities.claim:1",
        candidate_byte_start=start,
        candidate_byte_end=start + len("Synthetic capability text."),
        fact_ids=[fact.fact_id],
        fact_coordinates=[first_coordinate],
        rationale="only the first exact selected item survives",
    )
    source = b"# Product\n"
    plan = _minimal_plan(source, []).model_copy(
        update={"candidate_content_provenance": [provenance]}
    )

    report = build_knowledge_application_report(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
        document_plan=plan,
        candidate_text=candidate_text,
        status="final",
    )

    by_claim = {entry.global_claim_id: entry for entry in report.final_dispositions}
    assert by_claim[first_disposition.global_claim_id].disposition == "rendered_with_exact_spans"
    assert (
        by_claim[second_disposition.global_claim_id].disposition
        == "intentionally_omitted_with_evidence"
    )
    assert by_claim[second_disposition.global_claim_id].output_spans == ()


def test_rejected_claim_gets_rejected_before_authorship():
    report = build_knowledge_application_report(
        "some-org/some-repo",
        "nonexistent-family",
        "nonexistent-platform",
        data_root=Path("/nonexistent"),
        clone_cache=Path("/nonexistent"),
        source_revision=None,
    )

    assert report.final_dispositions == ()  # nothing considered at all


def test_duplicate_final_disposition_attribution_is_rejected():
    entry = FinalKnowledgeItemDispositionV1(
        global_claim_id="claim:1",
        fact_field="product.capabilities",
        disposition="rejected_before_authorship",
        reason="rejected",
    )
    disposition = _considered_disposition("claim:1")

    with pytest.raises(ValueError, match="duplicate final disposition attribution"):
        _report_with(dispositions=(disposition,), final_dispositions=(entry, entry))


def test_final_disposition_citing_an_unknown_claim_is_rejected():
    entry = FinalKnowledgeItemDispositionV1(
        global_claim_id="claim:unknown",
        fact_field=None,
        disposition="rejected_before_authorship",
        reason="rejected",
    )

    with pytest.raises(ValueError, match="cites an unknown claim"):
        _report_with(dispositions=(), final_dispositions=(entry,))


def test_rendered_with_exact_spans_requires_non_empty_output_spans():
    entry = FinalKnowledgeItemDispositionV1(
        global_claim_id="claim:1",
        fact_field="product.capabilities",
        disposition="rendered_with_exact_spans",
        reason="",
        output_spans=(),
    )
    disposition = _considered_disposition("claim:1")

    with pytest.raises(ValueError, match="carries no output_spans"):
        _report_with(dispositions=(disposition,), final_dispositions=(entry,))


def test_rendered_with_exact_spans_requires_item_level_fact_coordinates():
    span = RenderedOutputSpanV1(
        fact_id=descriptive_fact_id("aspose.feature_claims", "aspose-knowledge"),
        section="Key Capabilities",
        operation_id="op.1",
        operation="verified_template_provenance",
        replacement_sha256="a" * 64,
    )
    entry = FinalKnowledgeItemDispositionV1(
        global_claim_id="claim:1",
        fact_field="aspose.feature_claims",
        disposition="rendered_with_exact_spans",
        reason="rendered",
        output_spans=(span,),
    )
    disposition = _considered_disposition("claim:1")

    with pytest.raises(ValueError, match="no exact fact coordinate"):
        _report_with(dispositions=(disposition,), final_dispositions=(entry,))


def test_non_rendered_disposition_requires_a_reason():
    entry = FinalKnowledgeItemDispositionV1(
        global_claim_id="claim:1",
        fact_field="product.capabilities",
        disposition="not_applicable_with_reason",
        reason="   ",
    )
    disposition = _considered_disposition("claim:1")

    with pytest.raises(ValueError, match="no omission/rejection reason"):
        _report_with(dispositions=(disposition,), final_dispositions=(entry,))


def test_unaccounted_rendered_output_span_blocks_a_final_report():
    """A fact_id that reached `rendered_output_spans` but has no matching
    `rendered_with_exact_spans` entry in `final_dispositions` is exactly the
    ticket's "unaccounted rendered claim" -- must never construct."""

    disposition = _considered_disposition("claim:1", resulting_fact_field="product.capabilities")
    span = RenderedOutputSpanV1(
        fact_id=descriptive_fact_id("product.capabilities", "aspose-knowledge"),
        section="Key Capabilities",
        operation_id="op.1",
        operation="replace",
        replacement_sha256="a" * 64,
        fact_coordinates=(
            structured_list_item_coordinate(
                descriptive_fact_id("product.capabilities", "aspose-knowledge"),
                "product.capabilities",
                "claim:1",
            ),
        ),
    )

    with pytest.raises(ValueError, match="unaccounted for"):
        _report_with(
            dispositions=(disposition,),
            final_dispositions=(),
            rendered_output_spans=(span,),
            status="final",
        )


def _considered_disposition(global_claim_id: str, *, resulting_fact_field: str | None = None):
    from readme_agent.facts.aspose_knowledge_selection import KnowledgeClaimDispositionV1

    return KnowledgeClaimDispositionV1(
        global_claim_id=global_claim_id,
        family="3d",
        platform="python",
        kind="feature",
        source_revision=_3D_PYTHON_REPO_SHA,
        freshness="current",
        corroboration="corroborated",
        intended_section="Key Capabilities",
        accepted=True,
        resulting_fact_field=resulting_fact_field,
        verification_state="verified",
    )


def _report_with(
    *,
    dispositions,
    final_dispositions,
    rendered_output_spans=(),
    status: str = "final",
):
    return KnowledgeApplicationV1(
        status=status,
        org_repo="example-org/Example",
        family="3d",
        platform="python",
        source_revision=None,
        imported_bundle_repo_sha=None,
        freshness="current",
        considered_count=len(dispositions),
        selected_count=0,
        rejected_count=0,
        fact_fields_produced=(),
        sections_considered=(),
        sections_selected_for_planning=(),
        sections_influenced=(),
        rendered_output_spans=rendered_output_spans,
        final_dispositions=final_dispositions,
        load_findings=(),
        dispositions=dispositions,
        seo_keyword_dispositions=(),
    )
