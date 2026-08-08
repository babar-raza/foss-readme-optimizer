"""Focused persisted README composition-lineage and source-placement controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.presentation.verified_source_placements import (
    exclude_source_placements_from_provenance,
    resolve_preserve_claim_placements,
)
from readme_agent.presentation.verified_source_preservation import (
    compose_verified_source_preservation,
)
from readme_agent.readme.assessment import assess_readme_document
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
from readme_agent.readme.document_structure import parse_headings

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


def test_exact_preserved_h2_at_eof_gets_generated_separator_and_is_idempotent() -> None:
    facts = _review_facts()
    source = "# Email library\n\n## Package Entry Points\n\nExact detail at EOF"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    candidate = (
        "# Email library\n\n"
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)\n\n"
        "## Navigation\n\n"
        "- [At a glance](#at-a-glance)\n"
        "- [License](#license)\n\n"
        "## At a glance\n\n"
        "```mermaid\nflowchart LR\n  Input --- Email --- Output\n```\n\n"
        "## License\n\nPermit use under the [license](LICENSE).\n"
    )
    navigation_text = "- [At a glance](#at-a-glance)\n- [License](#license)"
    navigation_start = candidate.index(navigation_text)
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.navigation",
            candidate_byte_start=len(candidate[:navigation_start].encode("utf-8")),
            candidate_byte_end=len(
                candidate[: navigation_start + len(navigation_text)].encode("utf-8")
            ),
            configured_standard_ids=["readme.navigation"],
            rationale="Bind the generated Navigation before the exact source insertion.",
        )
    ]

    first = compose_verified_source_preservation(
        candidate,
        source,
        facts,
        assessment,
        set(),
        provenance,
    )
    second = compose_verified_source_preservation(
        first.candidate,
        source,
        facts,
        assessment,
        set(),
        first.provenance,
    )
    headings = parse_headings(first.candidate)

    assert "## Package Entry Points\n\nExact detail at EOF\n\n## License" in first.candidate
    assert [heading.title for heading in headings if heading.level == 2].count("License") == 1
    assert second.candidate == first.candidate
    assert second.provenance == first.provenance
    assert {item.placement_basis for item in first.source_placements} == {"composer_inserted_exact"}
    assert {item.placement_basis for item in second.source_placements} == {
        "structural_exact_equivalence"
    }
    assert all(item.source_owner_id for item in second.source_placements)
    assert all(
        item.structural_role == "h2:package-entry-points" for item in second.source_placements
    )


def test_composer_fails_closed_on_unplaced_generated_duplicate_of_preserve_claim() -> None:
    facts = _review_facts()
    exact_claim = "Exact repository-owned detail."
    source = f"# Email library\n\n## Repository details\n\n{exact_claim}\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    candidate = (
        "# Email library\n\n"
        "## Navigation\n\n- [Repository details](#repository-details)\n\n"
        f"## Repository details\n\n{exact_claim}\n\n{exact_claim}\n\n"
        "## License\n\nPermit use under the [license](LICENSE).\n"
    )
    claim_start = candidate.index(exact_claim)
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.generated-collision",
            candidate_byte_start=len(candidate[:claim_start].encode("utf-8")),
            candidate_byte_end=len(candidate[: claim_start + len(exact_claim)].encode("utf-8")),
            configured_standard_ids=["readme.generated-collision-control"],
            rationale="Prove generated ownership cannot launder a preserve claim.",
        )
    ]

    with pytest.raises(ValueError, match="explicit source placement required"):
        compose_verified_source_preservation(
            candidate,
            source,
            facts,
            assessment,
            set(),
            provenance,
        )


def test_fact_authorized_exact_claim_can_move_to_one_governed_h2() -> None:
    facts = _review_facts()
    exact_claim = "Exact repository-owned detail."
    source = f"# Email library\n\n## Repository details\n\n{exact_claim}\n"
    assessment = assess_readme_document(
        facts.org_repo,
        source,
        facts,
        base_revision="a" * 40,
    )
    claim = next(item for item in assessment.material_claims if item.disposition == "preserve")
    candidate = (
        "# Email library\n\n"
        "## Quick start\n\n"
        f"Generated fact-backed introduction.\n\n{exact_claim}\n"
    )
    broad_start = candidate.index("Generated fact-backed introduction.")
    broad_end = candidate.index(exact_claim) + len(exact_claim)
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.quick-start",
            candidate_byte_start=len(candidate[:broad_start].encode("utf-8")),
            candidate_byte_end=len(candidate[:broad_end].encode("utf-8")),
            fact_ids=["example.minimal:verified"],
            configured_standard_ids=["readme.primary_example"],
            rationale="Bind the complete generated quick-start body.",
        )
    ]

    missing, placements = resolve_preserve_claim_placements(
        candidate,
        source,
        assessment,
        set(),
        {claim.claim_id},
        [],
    )
    split = exclude_source_placements_from_provenance(provenance, placements)

    assert not missing
    assert len(placements) == 1
    assert placements[0].source_owner_id == claim.claim_id
    assert placements[0].placement_basis == "relocated_exact_equivalence"
    assert placements[0].structural_role == "h2:quick-start"
    fact_bound = [
        binding
        for binding in split
        if binding.candidate_byte_start == placements[0].final_byte_start
        and binding.fact_ids == ["example.minimal:verified"]
    ]
    assert len(fact_bound) == 1
    assert not candidate.encode("utf-8")[
        fact_bound[0].candidate_byte_end : placements[0].final_byte_end
    ].strip()


def test_ledger_rejects_operation_mismatch_and_overlapping_origin_authority() -> None:
    source = "Exact source."
    candidate = "Exact source.\n\nGenerated."
    operation = build_operation(
        operation_id="readme.origin-control",
        operation="replace",
        source=source.encode("utf-8"),
        start=0,
        end=len(source.encode("utf-8")),
        replacement=candidate,
        fact_ids=[],
        treatment="presentation_policy_correction",
        rationale="Exercise build-time operation and origin consistency.",
    )
    placement = ExactSourcePlacementV1(
        placement_id="source.origin-control",
        placement_basis="composer_inserted_exact",
        source_owner_id="claim.origin-control",
        source_byte_start=0,
        source_byte_end=len(source.encode("utf-8")),
        source_content_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        final_byte_start=0,
        final_byte_end=len(source.encode("utf-8")),
        final_content_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
    )
    overlapping = CandidateContentProvenanceV1(
        provenance_id="template.invalid-overlap",
        candidate_byte_start=0,
        candidate_byte_end=len(source.encode("utf-8")),
        configured_standard_ids=["readme.invalid-overlap-control"],
        rationale="Negative control for dual source/generated authority.",
    )
    generated_start = len(b"Exact source.\n\n")
    generated = CandidateContentProvenanceV1(
        provenance_id="template.generated-origin-control",
        candidate_byte_start=generated_start,
        candidate_byte_end=len(candidate.encode("utf-8")),
        configured_standard_ids=["readme.generated-origin-control"],
        rationale="Bind only the exact generated prose bytes.",
    )
    operation_provenance = legacy_operation_provenance(
        replay_operation_origins(source.encode("utf-8"), [operation])
    )

    with pytest.raises(ValueError, match="do not reconstruct"):
        build_composition_ledger(source, candidate + "!", [operation], [], [placement])
    with pytest.raises(ValueError, match="overlaps generated provenance"):
        build_composition_ledger(
            source,
            candidate,
            [operation],
            [overlapping, *operation_provenance],
            [placement],
        )
    operation_only = build_composition_ledger(
        source,
        candidate,
        [operation],
        operation_provenance,
        [placement],
    )
    unbound = [segment for segment in operation_only.segments if segment.authority == "unbound"]
    assert unbound
    assert "Generated." in "".join(segment.content_text for segment in unbound)
    assert all(
        not segment.fact_ids and not segment.configured_standard_ids and not segment.provenance_ids
        for segment in unbound
    )
    operation_only_errors = composition_ledger_errors(
        operation_only,
        source,
        candidate,
        [operation],
        operation_provenance,
    )
    assert any("substantive generated bytes lack" in error for error in operation_only_errors)

    complete_provenance = [generated, *operation_provenance]
    ledger = build_composition_ledger(
        source,
        candidate,
        [operation],
        complete_provenance,
        [placement],
    )
    errors = composition_ledger_errors(
        ledger,
        source,
        candidate,
        [operation],
        [generated, overlapping, *operation_provenance],
    )
    assert any("overlaps provenance" in error for error in errors)
