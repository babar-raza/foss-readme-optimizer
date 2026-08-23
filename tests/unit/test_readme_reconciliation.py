"""Gate R6: the five-bucket README reconciliation report (preserved /
corrected / relocated / superseded / omitted), derived purely from a real
candidate's own `ReadmeCompositionLedgerV1` and operations."""

from __future__ import annotations

import hashlib

import pytest

from readme_agent.readme.composition_lineage import build_composition_ledger
from readme_agent.readme.composition_lineage_models import ExactSourcePlacementV1
from readme_agent.readme.composition_operation_origins import (
    legacy_operation_provenance,
    replay_operation_origins,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_operations import build_operation
from readme_agent.readme.document_plan import (
    PresentationSpanAdoptionV1,
    ReadmeDocumentPlanV1,
    SourceClaimResolutionV1,
)
from readme_agent.readme.readme_reconciliation import (
    SourceReconciliationEntryV1,
    _validate_no_destination_overlap,
    build_readme_reconciliation_report,
)


def _plan(
    source: str,
    operations: list,
    *,
    source_claim_resolutions: list[SourceClaimResolutionV1] | None = None,
) -> ReadmeDocumentPlanV1:
    source_bytes = source.encode("utf-8")
    candidate_bytes = source_bytes
    for operation in operations:
        start, end = operation.source_byte_start, operation.source_byte_end
        candidate_bytes = (
            candidate_bytes[:start]
            + operation.replacement_text.encode("utf-8")
            + candidate_bytes[end:]
        )
    candidate = candidate_bytes.decode("utf-8")
    replay = replay_operation_origins(source_bytes, operations)
    provenance = list(legacy_operation_provenance(replay))
    ledger = build_composition_ledger(source, candidate, operations, provenance)
    return ReadmeDocumentPlanV1(
        org_repo="acme/widget",
        immutable_base_revision="deadbeef",
        facts_hash="a" * 64,
        template_sha256="b" * 64,
        source_sha256=sha256_hex(source),
        adoption=PresentationSpanAdoptionV1(
            already_adopted=True,
            source_document_sha256=sha256_hex(source),
            source_inner_sha256=sha256_hex(source),
            source_inner_bytes=len(source_bytes),
            preservation_check="byte_identical",
        ),
        operations=operations,
        source_claim_resolutions=source_claim_resolutions or [],
        candidate_sha256=sha256_hex(candidate),
        composition_ledger=ledger,
    )


def test_pure_no_op_source_is_entirely_preserved():
    source = "# Widget\n\nA small tool.\n"
    plan = _plan(source, [])

    report = build_readme_reconciliation_report(plan, source_text=source)

    assert report.source_bytes == len(source.encode("utf-8"))
    assert report.preserved_count == 1
    assert report.corrected_count == 0
    assert report.relocated_count == 0
    assert report.superseded_count == 0
    assert report.omitted_count == 0
    total = sum(e.source_byte_end - e.source_byte_start for e in report.entries)
    assert total == report.source_bytes


def test_fact_corrected_span_is_bucketed_as_corrected_with_operation_lineage():
    source = "# Widget\n\nSupports 3 formats.\n"
    start = source.index("Supports 3 formats.")
    end = start + len("Supports 3 formats.")
    operation = build_operation(
        operation_id="readme.example.correct-format-count",
        operation="replace",
        source=source.encode("utf-8"),
        start=start,
        end=end,
        replacement="Supports 5 formats.",
        fact_ids=["product.formats:verified"],
        treatment="authoritative_fact_correction",
        rationale="Correct the format count to the verified value.",
    )
    plan = _plan(source, [operation])

    report = build_readme_reconciliation_report(plan, source_text=source)

    assert report.corrected_count == 1
    corrected = next(e for e in report.entries if e.disposition == "corrected")
    assert corrected.source_byte_start == start
    assert corrected.source_byte_end == end
    assert corrected.operation_id == "readme.example.correct-format-count"
    assert corrected.rationale == "Correct the format count to the verified value."
    # Bytes before and after the correction are still preserved, not lost.
    assert report.preserved_count == 2
    total = sum(e.source_byte_end - e.source_byte_start for e in report.entries)
    assert total == report.source_bytes


def test_policy_replaced_span_is_bucketed_as_superseded():
    source = "# Widget\n\nSee forum.example.com/widget for help.\n"
    start = source.index("forum.example.com/widget")
    end = start + len("forum.example.com/widget")
    operation = build_operation(
        operation_id="readme.links.unwrap-unbound:1",
        operation="replace",
        source=source.encode("utf-8"),
        start=start,
        end=end,
        replacement="",
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Remove an excluded-domain link per link hygiene policy.",
    )
    plan = _plan(source, [operation])

    report = build_readme_reconciliation_report(plan, source_text=source)

    assert report.superseded_count == 1
    superseded = next(e for e in report.entries if e.disposition == "superseded")
    assert superseded.operation_id == "readme.links.unwrap-unbound:1"
    assert superseded.evidence is not None
    assert any(item.startswith("source-content-sha256:") for item in superseded.evidence)
    assert any(item.startswith("replacement-content-sha256:") for item in superseded.evidence)
    assert any(item.startswith("validator:") for item in superseded.evidence)
    total = sum(e.source_byte_end - e.source_byte_start for e in report.entries)
    assert total == report.source_bytes


def test_whole_document_template_operation_defers_to_granular_exact_placements():
    """A template compiler owns the document rewrite while exact inherited
    bytes inside that rewrite retain their stronger placement disposition."""

    source = "# Widget\n\nValuable repository detail.\n"
    start = source.index("Valuable repository detail.")
    end = start + len("Valuable repository detail.")
    replacement = "# Widget\n\n## Overview\n\nValuable repository detail.\n"
    operation = build_operation(
        operation_id="readme.verified-template.compile",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=replacement,
        fact_ids=["product.identity:verified"],
        treatment="presentation_policy_correction",
        rationale="Compile the accepted presentation contract.",
    )
    plan = _plan(source, [operation])
    detail_start = replacement.index("Valuable repository detail.")
    detail_sha256 = hashlib.sha256(source.encode("utf-8")[start:end]).hexdigest()
    granular_placement = ExactSourcePlacementV1(
        placement_id="source.repository-detail",
        placement_basis="composer_inserted_exact",
        source_owner_id="source:repository-detail",
        source_byte_start=start,
        source_byte_end=end,
        source_content_sha256=detail_sha256,
        final_byte_start=detail_start,
        final_byte_end=detail_start + (end - start),
        final_content_sha256=detail_sha256,
    )
    assert plan.composition_ledger is not None
    plan = plan.model_copy(
        update={
            "composition_ledger": plan.composition_ledger.model_copy(
                update={"source_placements": (granular_placement,)}
            )
        }
    )

    report = build_readme_reconciliation_report(plan, source_text=source)

    preserved = next(entry for entry in report.entries if entry.disposition == "preserved")
    assert (preserved.source_byte_start, preserved.source_byte_end) == (start, end)
    assert (preserved.final_byte_start, preserved.final_byte_end) == (
        detail_start,
        detail_start + (end - start),
    )
    assert report.superseded_count == 2
    assert sum(entry.source_byte_end - entry.source_byte_start for entry in report.entries) == len(
        source.encode("utf-8")
    )


def test_no_composition_ledger_fails_closed():
    source = "# Widget\n"
    plan = _plan(source, []).model_copy(update={"composition_ledger": None})

    with pytest.raises(ValueError, match="composition_ledger"):
        build_readme_reconciliation_report(plan, source_text=source)


def test_wrong_source_text_fails_closed():
    source = "# Widget\n"
    plan = _plan(source, [])

    with pytest.raises(ValueError, match="does not match"):
        build_readme_reconciliation_report(plan, source_text="# Something else entirely\n")


def test_every_entry_partitions_source_bytes_with_no_gap_or_overlap():
    source = "# Widget\n\nSupports 3 formats. Ask on forum.example.com/widget.\n"
    correction_start = source.index("Supports 3 formats.")
    correction_end = correction_start + len("Supports 3 formats.")
    link_start = source.index("forum.example.com/widget")
    link_end = link_start + len("forum.example.com/widget")
    operations = [
        build_operation(
            operation_id="readme.example.correct-format-count",
            operation="replace",
            source=source.encode("utf-8"),
            start=correction_start,
            end=correction_end,
            replacement="Supports 5 formats.",
            fact_ids=["product.formats:verified"],
            treatment="authoritative_fact_correction",
            rationale="Correct the format count.",
        ),
        build_operation(
            operation_id="readme.links.unwrap-unbound:1",
            operation="replace",
            source=source.encode("utf-8"),
            start=link_start,
            end=link_end,
            replacement="",
            fact_ids=[],
            treatment="presentation_policy_correction",
            rationale="Remove an excluded-domain link.",
        ),
    ]
    plan = _plan(source, operations)

    report = build_readme_reconciliation_report(plan, source_text=source)

    cursor = 0
    for entry in sorted(report.entries, key=lambda item: item.source_byte_start):
        assert entry.source_byte_start == cursor, "reconciliation must have no gap"
        cursor = entry.source_byte_end
    assert cursor == report.source_bytes, "reconciliation must cover every source byte"
    assert (
        report.preserved_count
        + report.corrected_count
        + report.relocated_count
        + report.superseded_count
        + report.omitted_count
        == len(report.entries)
    )


def test_relocated_h2_block_is_matched_by_heading_identity_with_destination_coordinates():
    """Stage 3A repair: a genuine canonical-section-order move (whole H2
    blocks swapped, content byte-identical, just repositioned) is now
    recovered by matching the same heading title between source and final
    candidate text -- never a raw cross-document substring scan -- and the
    resulting entry carries real destination coordinates."""

    source = "# Widget\n\n## Alpha\n\nAlpha content here.\n\n## Beta\n\nBeta content here.\n"
    swapped = "## Beta\n\nBeta content here.\n\n## Alpha\n\nAlpha content here.\n"
    move_start = source.index("## Alpha")
    move = build_operation(
        operation_id="readme.presentation.canonical-section-order",
        operation="move_exact",
        source=source.encode("utf-8"),
        start=move_start,
        end=len(source.encode("utf-8")),
        replacement=swapped,
        fact_ids=[],
        treatment="preserve",
        rationale="Move complete H2 blocks into the accepted portfolio journey.",
        coordinate_space="candidate_utf8",
    )
    plan = _plan(source, [move])

    report = build_readme_reconciliation_report(plan, source_text=source)

    assert report.relocated_count == 2
    relocated = {
        source[e.source_byte_start : e.source_byte_end].split("\n")[0].strip("# "): e
        for e in report.entries
        if e.disposition == "relocated"
    }
    assert set(relocated) == {"Alpha", "Beta"}
    for entry in relocated.values():
        assert entry.operation_id == "readme.presentation.canonical-section-order"
        assert entry.final_byte_start is not None
        assert entry.final_byte_end is not None
        # The destination span covers the section's core content; a trailing
        # inter-section blank-line separator does not survive verbatim once a
        # section becomes the last one (normalized away), so it may
        # legitimately be a few bytes shorter than the full source span.
        original_core = source[entry.source_byte_start : entry.source_byte_end].rstrip()
        candidate = "# Widget\n\n" + swapped
        relocated_text = candidate.encode("utf-8")[entry.final_byte_start : entry.final_byte_end]
        assert relocated_text.decode("utf-8") == original_core
    total = sum(e.source_byte_end - e.source_byte_start for e in report.entries)
    assert total == report.source_bytes


def test_verified_omission_claim_resolution_is_preferred_over_generic_operation_covering():
    """Stage 3A repair: an evidence-backed `verified_omission` claim
    resolution for a gap takes priority over the old "any covering
    operation, any treatment" heuristic, and its real evidence/rationale is
    carried onto the entry -- not a bare operation lookup."""

    source = "# Widget\n\nAn unverifiable claim about magic.\n"
    start = source.index("An unverifiable claim about magic.")
    end = start + len("An unverifiable claim about magic.")
    removal = build_operation(
        operation_id="readme.example.remove-unverifiable-claim",
        operation="replace",
        source=source.encode("utf-8"),
        start=start,
        end=end,
        replacement="",
        fact_ids=[],
        treatment="preserve",
        rationale="Generic removal operation -- must not win over real claim evidence.",
    )
    resolution = SourceClaimResolutionV1(
        claim_id="source-claim:magic",
        source_byte_start=start,
        source_byte_end=end,
        content_sha256=hashlib.sha256(source.encode("utf-8")[start:end]).hexdigest(),
        resolution="verified_omission",
        evidence=["assessment:explicit-omission", "review:unverifiable-claim-rejected"],
        rationale="Claim could not be verified against any accepted fact; omitted, not lost.",
    )
    plan = _plan(source, [removal], source_claim_resolutions=[resolution])

    report = build_readme_reconciliation_report(plan, source_text=source)

    omitted = next(e for e in report.entries if e.disposition == "omitted")
    assert omitted.operation_id == "source-claim:magic"
    assert omitted.rationale == resolution.rationale
    assert omitted.evidence == tuple(resolution.evidence)
    total = sum(e.source_byte_end - e.source_byte_start for e in report.entries)
    assert total == report.source_bytes


def test_verified_equivalence_claim_resolution_yields_relocated_with_its_own_destination():
    """A `verified_equivalence` claim resolution already carries its own
    exact candidate-span binding -- reconciliation must use it directly as
    the relocated entry's destination, no matching needed."""

    source = "# Widget\n\nThe magic phrase.\n"
    start = source.index("The magic phrase.")
    end = start + len("The magic phrase.")
    removal = build_operation(
        operation_id="readme.example.move-magic-phrase",
        operation="replace",
        source=source.encode("utf-8"),
        start=start,
        end=end,
        replacement="",
        fact_ids=[],
        treatment="preserve",
        rationale="Content moves elsewhere in the candidate via a verified-equivalence claim.",
    )
    resolution = SourceClaimResolutionV1(
        claim_id="source-claim:magic-phrase",
        source_byte_start=start,
        source_byte_end=end,
        content_sha256=hashlib.sha256(source.encode("utf-8")[start:end]).hexdigest(),
        resolution="verified_equivalence",
        fact_ids=["product.identity:verified"],
        candidate_claim_id="candidate-claim:magic-phrase",
        candidate_byte_start=42,
        candidate_byte_end=60,
        candidate_content_sha256=hashlib.sha256(b"The magic phrase.").hexdigest(),
        evidence=["candidate-claim:magic-phrase"],
        rationale="Preserved verbatim elsewhere in the candidate's Key Capabilities section.",
    )
    plan = _plan(source, [removal], source_claim_resolutions=[resolution])

    report = build_readme_reconciliation_report(plan, source_text=source)

    relocated = next(e for e in report.entries if e.disposition == "relocated")
    assert relocated.operation_id == "source-claim:magic-phrase"
    assert relocated.final_byte_start == 42
    assert relocated.final_byte_end == 60


def test_destination_overlap_across_reconciliation_entries_is_rejected():
    """The check that makes double-counted relocation attribution
    structurally impossible: two entries whose destination bytes overlap
    must raise, never silently coexist."""

    entries = [
        SourceReconciliationEntryV1(
            source_byte_start=0,
            source_byte_end=5,
            disposition="relocated",
            final_byte_start=10,
            final_byte_end=20,
        ),
        SourceReconciliationEntryV1(
            source_byte_start=5,
            source_byte_end=10,
            disposition="relocated",
            final_byte_start=15,
            final_byte_end=25,
        ),
    ]

    with pytest.raises(ValueError, match="reconciliation destination ranges overlap"):
        _validate_no_destination_overlap(entries)


def test_real_net_fixture_relocates_moves_and_fails_closed_on_real_loss():
    """Stage 3A repair proof against the real net fixture: the
    canonical-section-order move (whole H2 blocks swapped) that used to be
    this module's only recoverable case now resolves cleanly via
    heading-identity matching -- proven here by the raised error no longer
    covering any move-touched span, and no longer covering the first ~360
    bytes of the dropped `## Status` section either (an earlier sub-range
    that failed before the heading-boundary gap-splitting fix landed). A
    genuinely separate defect remains in this same real fixture: the
    non-canonical `## Status` section's "advanced features not available"
    limitations list (source bytes [1745, 2020)) is dropped from the
    candidate by an earlier stage with no operation, claim resolution, or
    placement explaining it at all -- real, previously-silent content loss,
    not a reconciliation-lineage gap. `build_readme_reconciliation_report`
    is documented to fail closed on exactly this (never silently report an
    incomplete reconciliation), so this test asserts that fail-closed
    behavior directly instead of hiding it behind `xfail` -- logged
    separately (GOV-014, `plans/backlog-post-poc.md`)."""

    from readme_agent.readme.document_renderer import build_readme_document_candidate
    from readme_agent.readme.markers import find_presentation_span
    from tests.unit.test_readme_existing_section_regressions import (
        NET_EVIDENCE,
        NET_REVISION,
        _net_facts,
    )

    facts = _net_facts()
    source = (NET_EVIDENCE / "original-readme.md").read_text(encoding="utf-8")
    _candidate, plan = build_readme_document_candidate(
        facts.org_repo, source, facts, base_revision=NET_REVISION
    )
    existing = find_presentation_span(source)
    inner_text = existing.content if existing is not None else source

    move_operations = [op for op in plan.operations if op.operation == "move_exact"]
    assert move_operations, "this fixture is only meaningful once section order is enforced"

    with pytest.raises(ValueError, match=r"unaccounted source loss: bytes \[1745, 2020\)"):
        build_readme_reconciliation_report(plan, source_text=inner_text)
