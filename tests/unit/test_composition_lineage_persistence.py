"""Focused persisted README composition-lineage and source-placement controls."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.composition_lineage_validation import composition_ledger_errors
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _review_facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))


def _document_facts(org_repo: str) -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == org_repo)
    return ProductFactsV2.model_validate(pilot["product_facts_v2"]), pilot["snapshot"][
        "source_revision"
    ]


def test_composition_ledger_rejects_gap_overlap_hash_and_stale_source_tampering() -> None:
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _document_facts(org_repo)
    source = "# Cells\n\nUnicode α source at EOF"
    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    ledger = plan.composition_ledger
    source_segment = next(
        segment for segment in ledger.segments if segment.origin == "source_preserved"
    )

    gap_segment = source_segment.model_copy(
        update={"final_byte_start": source_segment.final_byte_start + 1}
    )
    gap_ledger = ledger.model_copy(
        update={
            "segments": [
                gap_segment if item.segment_id == source_segment.segment_id else item
                for item in ledger.segments
            ]
        }
    )
    overlap_segment = source_segment.model_copy(
        update={"final_byte_end": source_segment.final_byte_end + 1}
    )
    overlap_ledger = ledger.model_copy(
        update={
            "segments": [
                overlap_segment if item.segment_id == source_segment.segment_id else item
                for item in ledger.segments
            ]
        }
    )
    hash_ledger = ledger.model_copy(update={"candidate_sha256": "0" * 64})
    stale_source = source.replace("Unicode α", "Unicode β")

    assert composition_ledger_errors(
        gap_ledger, source, candidate, plan.operations, plan.candidate_content_provenance
    )
    assert composition_ledger_errors(
        overlap_ledger, source, candidate, plan.operations, plan.candidate_content_provenance
    )
    assert composition_ledger_errors(
        hash_ledger, source, candidate, plan.operations, plan.candidate_content_provenance
    )
    assert composition_ledger_errors(
        ledger, stale_source, candidate, plan.operations, plan.candidate_content_provenance
    )


def test_composition_ledger_rejects_stale_source_coordinate_and_segment_hash() -> None:
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _document_facts(org_repo)
    source = "# Cells\n\nExact source detail."
    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )
    ledger = plan.composition_ledger
    source_segment = next(
        segment for segment in ledger.segments if segment.origin == "source_preserved"
    )
    stale_coordinate = source_segment.model_copy(
        update={"source_byte_start": source_segment.source_byte_start + 1}
    )
    stale_hash = source_segment.model_copy(update={"source_content_sha256": "f" * 64})

    for tampered_segment in (stale_coordinate, stale_hash):
        tampered = ledger.model_copy(
            update={
                "segments": [
                    tampered_segment if item.segment_id == source_segment.segment_id else item
                    for item in ledger.segments
                ]
            }
        )
        errors = composition_ledger_errors(
            tampered,
            source,
            candidate,
            plan.operations,
            plan.candidate_content_provenance,
        )
        assert any("exact source lineage changed" in error for error in errors)


def test_historical_v1_plan_without_composition_ledger_still_parses() -> None:
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _document_facts(org_repo)
    source = "# Cells\n\nHistorical plan compatibility."
    _, plan = build_readme_document_candidate(org_repo, source, facts, base_revision=revision)
    historical_payload = plan.model_dump(mode="json")
    historical_payload.pop("composition_ledger")

    parsed = ReadmeDocumentPlanV1.model_validate(historical_payload)

    assert parsed.schema_version == 1
    assert parsed.composition_ledger is None


def test_current_candidate_validation_fails_closed_when_ledger_is_missing() -> None:
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _document_facts(org_repo)
    source = "# Cells\n\nCurrent outputs require lineage."
    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )

    decision = validate_readme_document_candidate(
        source,
        candidate,
        plan.model_copy(update={"composition_ledger": None}),
        facts,
    )

    assert decision.checks["composition_lineage"] is False
    assert "current document plan is missing its composition ledger" in decision.errors
