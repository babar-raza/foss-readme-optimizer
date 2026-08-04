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
    ReadmeCompositionLedgerV1,
)
from readme_agent.readme.composition_lineage_validation import composition_ledger_errors
from readme_agent.readme.document_operations import build_operation

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


def test_ledger_rejects_forged_operation_basis_duplicate_reuse_and_utf8_splits() -> None:
    source = "Exact."
    candidate = "Exact.\n\nExact."
    operation = build_operation(
        operation_id="readme.forged-origin",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Negative control for coincidental equal replacement bytes.",
    )
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()

    def placement(placement_id: str, final_start: int) -> ExactSourcePlacementV1:
        return ExactSourcePlacementV1(
            placement_id=placement_id,
            placement_basis="operation_unchanged_exact",
            source_byte_start=0,
            source_byte_end=len(source.encode("utf-8")),
            source_content_sha256=source_hash,
            final_byte_start=final_start,
            final_byte_end=final_start + len(source.encode("utf-8")),
            final_content_sha256=source_hash,
        )

    with pytest.raises(ValueError, match="lacks replayed origins"):
        build_composition_ledger(
            source,
            candidate,
            [operation],
            [],
            [placement("operation.forged", 0)],
        )
    with pytest.raises(ValueError, match="reuses source bytes"):
        build_composition_ledger(
            source,
            candidate,
            [operation],
            [],
            [placement("operation.duplicate-a", 0), placement("operation.duplicate-b", 8)],
        )
    forged_no_op = placement("source.forged-no-op", 0).model_copy(
        update={"placement_basis": "no_op_whole_source"}
    )
    with pytest.raises(ValueError, match="sole exact zero-operation placement"):
        build_composition_ledger(
            source,
            candidate,
            [operation],
            [],
            [forged_no_op],
        )

    unicode_source = "α"
    unicode_candidate = "α!"
    unicode_operation = build_operation(
        operation_id="readme.utf8-origin",
        operation="replace",
        source=unicode_source.encode("utf-8"),
        start=0,
        end=len(unicode_source.encode("utf-8")),
        replacement=unicode_candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Negative control for UTF-8-split placements.",
    )
    split_byte = unicode_source.encode("utf-8")[1:2]
    split_hash = hashlib.sha256(split_byte).hexdigest()
    split = ExactSourcePlacementV1(
        placement_id="source.utf8-split",
        placement_basis="composer_inserted_exact",
        source_owner_id="claim.utf8-split",
        source_byte_start=1,
        source_byte_end=2,
        source_content_sha256=split_hash,
        final_byte_start=1,
        final_byte_end=2,
        final_content_sha256=split_hash,
    )
    with pytest.raises(ValueError, match="UTF-8 boundary aligned"):
        build_composition_ledger(
            unicode_source,
            unicode_candidate,
            [unicode_operation],
            [],
            [split],
        )
    valid_unicode_ledger = build_composition_ledger(unicode_source, unicode_source, [], [], None)
    persisted_payload = valid_unicode_ledger.model_dump(mode="json")
    persisted_payload["source_placements"] = [split.model_dump(mode="json")]
    with pytest.raises(ValueError):
        ReadmeCompositionLedgerV1.model_validate(persisted_payload)
    bypassed = valid_unicode_ledger.model_copy(update={"source_placements": [split]})
    assert any(
        "UTF-8 aligned" in error
        for error in composition_ledger_errors(
            bypassed,
            unicode_source,
            unicode_source,
            [],
            [],
        )
    )


def test_persisted_ledger_rejects_out_of_bounds_empty_slice_placement() -> None:
    source = "Exact."
    ledger = build_composition_ledger(source, source, [], [], None)
    empty_hash = hashlib.sha256(b"").hexdigest()
    out_of_bounds = ExactSourcePlacementV1(
        placement_id="source.out-of-bounds",
        placement_basis="composer_inserted_exact",
        source_owner_id="claim.out-of-bounds",
        source_byte_start=999,
        source_byte_end=1000,
        source_content_sha256=empty_hash,
        final_byte_start=999,
        final_byte_end=1000,
        final_content_sha256=empty_hash,
    )
    payload = ledger.model_dump(mode="json")
    payload["source_placements"] = [out_of_bounds.model_dump(mode="json")]

    with pytest.raises(ValueError, match="exceeds ledger boundaries"):
        ReadmeCompositionLedgerV1.model_validate(payload)
    bypassed = ledger.model_copy(update={"source_placements": [out_of_bounds]})
    errors = composition_ledger_errors(bypassed, source, source, [], [])
    assert any("exact source placement changed" in error for error in errors)
