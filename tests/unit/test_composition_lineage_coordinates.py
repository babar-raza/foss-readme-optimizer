"""Focused persisted README composition-lineage and source-placement controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_lineage_models import (
    ExactSourcePlacementV1,
)
from readme_agent.readme.composition_lineage_validation import composition_ledger_errors
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import CandidateContentProvenanceV1

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


def test_document_operation_prefix_cannot_turn_ordinary_provenance_into_lineage_only() -> None:
    binding = CandidateContentProvenanceV1(
        provenance_id="document-operation.forged-factual.0000",
        candidate_byte_start=0,
        candidate_byte_end=5,
        configured_standard_ids=["readme.factual-standard"],
        rationale="The ID prefix cannot change typed factual authority.",
    )

    assert binding.authority_scope == "factual_or_configured"
    assert binding.lineage_operation_id is None
    with pytest.raises(ValueError, match="cannot claim factual authority"):
        CandidateContentProvenanceV1(
            provenance_id="document-operation.real.lineage",
            authority_scope="lineage_only",
            lineage_operation_id="readme.real",
            candidate_byte_start=0,
            candidate_byte_end=5,
            fact_ids=["fact.must-not-donate"],
            configured_standard_ids=["readme.lineage-only"],
            rationale="Lineage ownership cannot grant factual authority.",
        )

    source = "old"
    candidate = "Fact."
    operation = build_operation(
        operation_id="readme.prefix-control",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Prove an ordinary typed binding remains ordinary despite its ID.",
    )
    exact = legacy_operation_provenance(
        replay_operation_origins(source.encode("utf-8"), [operation])
    )
    ledger = build_composition_ledger(source, candidate, [operation], [binding, *exact])

    assert (
        composition_ledger_errors(
            ledger,
            source,
            candidate,
            [operation],
            [binding, *exact],
        )
        == []
    )


def test_duplicate_text_lineage_keeps_generated_occurrence_on_exact_provenance() -> None:
    source = "Shared text."
    candidate = "Shared text.\n\nShared text."
    generated_start = candidate.rindex("Shared text.")
    generated_start_byte = len(candidate[:generated_start].encode("utf-8"))
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.generated-duplicate",
        candidate_byte_start=generated_start_byte,
        candidate_byte_end=generated_start_byte + len(b"Shared text."),
        configured_standard_ids=["readme.duplicate-control"],
        rationale="Bind only the generated duplicate occurrence.",
    )
    operation = build_operation(
        operation_id="readme.duplicate-control",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=candidate,
        fact_ids=["fact.broad-operation-only"],
        treatment="presentation_policy_correction",
        rationale="Exercise deterministic duplicate lineage.",
    )

    placement = ExactSourcePlacementV1(
        placement_id="source.explicit-duplicate",
        placement_basis="composer_inserted_exact",
        source_owner_id="claim.explicit-duplicate",
        source_byte_start=0,
        source_byte_end=len(source.encode("utf-8")),
        source_content_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        final_byte_start=0,
        final_byte_end=len(source.encode("utf-8")),
        final_content_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )
    operation_provenance = legacy_operation_provenance(
        replay_operation_origins(source.encode("utf-8"), [operation])
    )
    complete_provenance = [provenance, *operation_provenance]
    ledger = build_composition_ledger(
        source,
        candidate,
        [operation],
        complete_provenance,
        [placement],
    )
    generated = [
        segment for segment in ledger.segments if provenance.provenance_id in segment.provenance_ids
    ]
    preserved = [segment for segment in ledger.segments if segment.origin == "source_preserved"]

    assert len(generated) == 1
    assert generated[0].final_byte_start == generated_start_byte
    assert "fact.broad-operation-only" not in generated[0].fact_ids
    assert "".join(segment.content_text for segment in preserved) == source
    assert all(segment.final_byte_end <= generated_start_byte for segment in preserved)
    assert (
        composition_ledger_errors(
            ledger,
            source,
            candidate,
            [operation],
            complete_provenance,
        )
        == []
    )


def test_unicode_eof_lineage_uses_utf8_boundaries_and_reconstructs_navigation() -> None:
    source = "# Δ\n\n## Navigation\n\n- [EOF](#eof)\n\n## EOF\n\nExact α at EOF"
    candidate = source.replace("## EOF", "## Generated ✨\n\nBound.\n\n## EOF")
    operation = build_operation(
        operation_id="readme.unicode-navigation",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Exercise Unicode, Navigation, and EOF boundaries.",
    )
    generated_text = "## Generated ✨\n\nBound.\n\n"
    generated_character = candidate.index(generated_text)
    generated_start = len(candidate[:generated_character].encode("utf-8"))
    provenance = CandidateContentProvenanceV1(
        provenance_id="template.unicode-navigation",
        candidate_byte_start=generated_start,
        candidate_byte_end=generated_start + len(generated_text.encode("utf-8")),
        configured_standard_ids=["readme.navigation"],
        rationale="Bind the generated Unicode-safe section.",
    )

    source_bytes = source.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    insertion_source_start = len(source[: source.index("## EOF")].encode("utf-8"))
    inserted_bytes = len(generated_text.encode("utf-8"))
    placements = [
        ExactSourcePlacementV1(
            placement_id="source.unicode-prefix",
            placement_basis="composer_inserted_exact",
            source_owner_id="section.unicode-prefix",
            source_byte_start=0,
            source_byte_end=insertion_source_start,
            source_content_sha256=hashlib.sha256(source_bytes[:insertion_source_start]).hexdigest(),
            final_byte_start=0,
            final_byte_end=insertion_source_start,
            final_content_sha256=hashlib.sha256(source_bytes[:insertion_source_start]).hexdigest(),
        ),
        ExactSourcePlacementV1(
            placement_id="source.unicode-eof",
            placement_basis="composer_inserted_exact",
            source_owner_id="section.unicode-eof",
            source_byte_start=insertion_source_start,
            source_byte_end=len(source_bytes),
            source_content_sha256=hashlib.sha256(source_bytes[insertion_source_start:]).hexdigest(),
            final_byte_start=insertion_source_start + inserted_bytes,
            final_byte_end=len(candidate_bytes),
            final_content_sha256=hashlib.sha256(source_bytes[insertion_source_start:]).hexdigest(),
        ),
    ]
    operation_provenance = legacy_operation_provenance(
        replay_operation_origins(source.encode("utf-8"), [operation])
    )
    complete_provenance = [provenance, *operation_provenance]
    ledger = build_composition_ledger(
        source,
        candidate,
        [operation],
        complete_provenance,
        placements,
    )

    assert (
        composition_ledger_errors(
            ledger,
            source,
            candidate,
            [operation],
            complete_provenance,
        )
        == []
    )
    assert ledger.segments[-1].content_text.endswith("Exact α at EOF")
    assert ledger.segments[-1].origin == "source_preserved"
    assert all(
        len(candidate.encode("utf-8")[: segment.final_byte_start].decode("utf-8")) >= 0
        for segment in ledger.segments
    )
