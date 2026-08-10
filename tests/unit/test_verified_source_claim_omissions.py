"""Prove exact, fail-closed dispositions for withheld inherited source claims."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.presentation.verified_source_claim_omissions import (
    _capability_anchor_matches,
    deferred_unverified_obligation_detail_resolution,
    deferred_withheld_source_resolution,
    verified_paired_example_intro_resolution,
)
from readme_agent.presentation.verified_source_claim_resolution_engine import (
    resolve_source_claims,
)
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.document_plan import CandidateContentProvenanceV1, SourceClaimResolutionV1
from readme_agent.readme.source_claim_risk import classify_source_claim_risk
from tests.unit.test_source_claim_capability_binding import _slides_api_facts

ROOT = Path(__file__).resolve().parents[2]
FACTS = (
    ROOT
    / "tests"
    / "fixtures"
    / "readmes"
    / "verified_source_assurance"
    / "aspose-3d-python-facts-ab1a2267.json"
)


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate_json(FACTS.read_text(encoding="utf-8"))


def _optional_source() -> tuple[str, ReadmeMaterialClaimAssessmentV1]:
    source = (
        "# Product\n\n## Quick Start\n\n### Alternative\n\nAlternative optional workflow detail.\n"
    )
    return source, assess_material_claims(source)[0]


def test_mandatory_source_detail_can_defer_only_after_verified_core_exists() -> None:
    source = "# Product\n\n## API reference\n\n- Detailed API wording to verify later.\n"
    claim = assess_material_claims(source)[0]
    claim_text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    risk = classify_source_claim_risk(source, claim)

    resolution = deferred_unverified_obligation_detail_resolution(
        claim,
        claim_text,
        b"# Verified candidate\n",
        risk,
        _facts(),
        correction_candidate_claim_ids=frozenset({claim.claim_id}),
        candidate_core_present=True,
    )

    assert resolution is not None
    assert resolution.resolution == "deferred_verification"
    assert resolution.fact_ids == []
    assert resolution.replacement_provenance_ids == []
    assert (
        deferred_unverified_obligation_detail_resolution(
            claim,
            claim_text,
            b"# Candidate without a verified API slot\n",
            risk,
            _facts(),
            correction_candidate_claim_ids=frozenset({claim.claim_id}),
            candidate_core_present=False,
        )
        is None
    )


def test_generic_content_group_defers_only_when_verified_capabilities_cover_content() -> None:
    facts = _facts()
    capability = facts.selected_fact("product.capabilities")
    replacement = capability.model_copy(update={"value": ["Image and attachment content"]})
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == capability.fact_id else fact for fact in facts.facts
            ]
        }
    )
    source = "# Product\n\n## Capabilities\n\n- Content extraction\n"
    claim = assess_material_claims(source)[0]
    claim_text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
    risk = classify_source_claim_risk(source, claim)

    resolution = deferred_unverified_obligation_detail_resolution(
        claim,
        claim_text,
        b"# Candidate with verified content capabilities\n",
        risk,
        facts,
        correction_candidate_claim_ids=frozenset({claim.claim_id}),
        candidate_core_present=True,
    )

    assert resolution is not None
    assert resolution.resolution == "deferred_verification"


def test_multirow_capability_table_can_defer_unverified_row_qualifiers() -> None:
    facts = _facts()
    capability = facts.selected_fact("product.capabilities")
    replacement = capability.model_copy(
        update={
            "value": [
                "Code 128 generation with automatic switching",
                "QR Code generation",
                "EAN-13 and EAN-8 generation",
            ]
        }
    )
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == capability.fact_id else fact for fact in facts.facts
            ]
        }
    )
    table = (
        "| Symbology | Function | Accepted input |\n"
        "| --- | --- | --- |\n"
        "| Code 128 | `code128()` | 12 characters |\n"
        "| QR Code | `qr()` | Versions 1-40 |\n"
        "| EAN-13 | `ean13()` | 13 digits |\n"
    )

    assert _capability_anchor_matches(table, facts)


def test_capability_anchor_ignores_markdown_link_destination_tokens() -> None:
    facts = _facts()
    capability = facts.selected_fact("product.capabilities")
    replacement = capability.model_copy(update={"value": ["EmailMessage conversion"]})
    facts = facts.model_copy(
        update={
            "facts": [
                replacement if fact.fact_id == capability.fact_id else fact for fact in facts.facts
            ]
        }
    )
    claim = (
        "Convert between MSG and [`email.message.EmailMessage`]"
        "(https://docs.python.org/3/library/email.message.html#email.message.EmailMessage)"
    )

    assert _capability_anchor_matches(claim, facts)


def test_api_anchored_feature_can_defer_only_its_unverified_detail() -> None:
    facts = _slides_api_facts()
    for detail in (
        "**Slides** — Add, remove, clone, reorder, and iterate slides",
        "**Presentation I/O** — Open, create, and save `.pptx` files with full round-trip fidelity",
    ):
        source = f"# Product\n\n## Features\n\n- {detail}\n"
        claim = assess_material_claims(source)[0]
        claim_text = source.encode()[claim.source_byte_start : claim.source_byte_end].decode()
        risk = classify_source_claim_risk(source, claim)

        resolution = deferred_unverified_obligation_detail_resolution(
            claim,
            claim_text,
            b"# Candidate with independently verified capabilities\n",
            risk,
            facts,
            correction_candidate_claim_ids=frozenset({claim.claim_id}),
            candidate_core_present=True,
        )

        assert resolution is not None
        assert resolution.resolution == "deferred_verification"
        assert resolution.fact_ids == []


def _verified_example_case(
    *,
    source_execution_verified: bool = False,
    source_static_verified: bool = True,
    source_validation_reason: str = "accepted",
    input_name: str = "model.obj",
    fixture_paths: list[dict[str, object]] | None = None,
    scan_status: str = "complete",
    minimal_outcome: str = "SOURCE_BUILD_VERIFIED",
) -> tuple[ProductFactsV2, str, str, list[CandidateContentProvenanceV1]]:
    facts = _facts()
    code = f'from aspose.threed import Scene\n\nscene = Scene()\nscene.open("{input_name}")'
    source = f"# Product\n\n## Quick Start\n\n```python\n{code}\n```\n"
    source_revision = "a" * 40
    inventory = {
        "schema_version": 1,
        "scan_status": scan_status,
        "scan_root": ".",
        "source_revision": source_revision,
        "tree_id": "b" * 40 if scan_status == "complete" else None,
        "inventory_sha256": "c" * 64 if scan_status == "complete" else None,
        "tracked_file_count": 2 if scan_status == "complete" else None,
        "recognized_extensions": [
            ".3ds",
            ".dae",
            ".doc",
            ".docx",
            ".eml",
            ".eot",
            ".fbx",
            ".glb",
            ".gltf",
            ".htm",
            ".html",
            ".jpeg",
            ".jpg",
            ".mbox",
            ".msg",
            ".obj",
            ".one",
            ".otf",
            ".pdf",
            ".ply",
            ".png",
            ".ppt",
            ".pptx",
            ".stl",
            ".svg",
            ".tif",
            ".tiff",
            ".ttf",
            ".woff",
            ".woff2",
            ".xls",
            ".xlsx",
        ],
        "fixture_paths": fixture_paths or [],
        "failure_reason": None if scan_status == "complete" else "enumeration_unavailable",
    }
    examples = FactRecordV2(
        fact_id="repository.examples:fixture-inventory",
        field="repository.examples",
        value={
            "execution_policy": "inventory_only",
            "files": [],
            "inline_examples": [
                {
                    "title": "Quick Start",
                    "code": code,
                    "language": "python",
                    "static_api_verified": source_static_verified,
                    "execution_verified": source_execution_verified,
                    "evidence_modules": ["aspose.threed"],
                }
            ]
            if source_static_verified
            else [],
            "withheld_inline_examples": []
            if source_static_verified
            else [
                {
                    "title": "Quick Start",
                    "code": code,
                    "language": "python",
                    "static_api_verified": False,
                    "execution_verified": False,
                    "validation_reason": source_validation_reason,
                    "evidence_modules": [],
                }
            ],
            "result_assets": [],
            "readme_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "fixture_inventory": inventory,
        },
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://fixture",
            source_revision=source_revision,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.examples"],
    )
    minimal_id = facts.selected_fact_ids["example.minimal"]
    minimal = facts.fact_by_id(minimal_id).model_copy(
        update={
            "value": {**facts.fact_by_id(minimal_id).value, "verification_outcome": minimal_outcome}
        }
    )
    records = [minimal if item.fact_id == minimal_id else item for item in facts.facts]
    updated = facts.model_copy(
        update={
            "facts": [*records, examples],
            "selected_fact_ids": {
                **facts.selected_fact_ids,
                "repository.examples": examples.fact_id,
            },
        }
    )
    minimal_code = str(minimal.value["code"]).rstrip()
    candidate = f"# Product\n\n## Quick Start\n\n```python\n{minimal_code}\n```\n"
    start = candidate.index("```python")
    end = len(candidate)
    provenance = [
        CandidateContentProvenanceV1(
            provenance_id="template.section.quick_start",
            candidate_byte_start=len(candidate[:start].encode()),
            candidate_byte_end=len(candidate[:end].encode()),
            fact_ids=[minimal_id],
            rationale="Source-build-verified minimal example.",
        )
    ]
    return ProductFactsV2.model_validate(updated), source, candidate, provenance


def test_exact_optional_withholding_has_hash_bound_deferred_disposition() -> None:
    source, claim = _optional_source()
    candidate = "# Product\n"
    coordinates = (claim.source_byte_start, claim.source_byte_end)

    resolutions = resolve_source_claims(
        source,
        candidate,
        _facts(),
        [],
        authoritative_correction_ranges=[coordinates],
        fail_on_unresolved_preserve=False,
    )

    assert len(resolutions) == 1
    resolution = resolutions[0]
    assert resolution.resolution == "deferred_verification"
    assert resolution.claim_id == claim.claim_id
    assert resolution.content_sha256 == claim.content_sha256
    assert resolution.evidence == [
        f"source-claim:{claim.claim_id}",
        f"source-content-sha256:{claim.content_sha256}",
        f"candidate-content-sha256:{hashlib.sha256(candidate.encode()).hexdigest()}",
        "authority:verified-source-assurance:correction-candidate",
        "risk-policy:optional-inherited-detail-deferred-v1",
    ]


@pytest.mark.parametrize("offset", [-1, 1])
def test_partial_or_spoofed_withholding_range_is_rejected(offset: int) -> None:
    source, claim = _optional_source()
    coordinates = (claim.source_byte_start + offset, claim.source_byte_end)

    with pytest.raises(ValueError, match="partial, spoofed, or stale"):
        resolve_source_claims(
            source,
            "# Product\n",
            _facts(),
            [],
            authoritative_correction_ranges=[coordinates],
            fail_on_unresolved_preserve=False,
        )


def test_spoofed_claim_bytes_cannot_receive_deferred_disposition() -> None:
    source, claim = _optional_source()
    risk = classify_source_claim_risk(source, claim)

    with pytest.raises(ValueError, match="do not match the assessed claim hash"):
        deferred_withheld_source_resolution(
            claim,
            "Spoofed optional workflow detail.\n",
            b"# Product\n",
            risk,
            correction_candidate_claim_ids=frozenset({claim.claim_id}),
        )


def test_mandatory_unsupported_claim_remains_unresolved_and_blocking() -> None:
    source = "# Product\n\n## Security\n\nAll reports are vulnerability-free.\n"
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        "# Product\n",
        _facts(),
        [],
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert classify_source_claim_risk(source, claim).risk_class == "mandatory_fact_resolution"
    assert resolutions == []


def test_fact_authorized_claim_cannot_be_silently_withheld() -> None:
    source, claim = _optional_source()
    coordinates = (claim.source_byte_start, claim.source_byte_end)

    with pytest.raises(ValueError, match="preserve disposition lost a source claim"):
        resolve_source_claims(
            source,
            "# Product\n",
            _facts(),
            [],
            preserved_source_ranges=[coordinates],
            fail_on_unresolved_preserve=True,
        )


def test_one_claim_cannot_have_preservation_and_withholding_authority() -> None:
    source, claim = _optional_source()
    coordinates = (claim.source_byte_start, claim.source_byte_end)

    with pytest.raises(ValueError, match="both fact-authorized and correction-required"):
        resolve_source_claims(
            source,
            "# Product\n",
            _facts(),
            [],
            preserved_source_ranges=[coordinates],
            authoritative_correction_ranges=[coordinates],
            fail_on_unresolved_preserve=False,
        )


def test_static_source_example_with_absent_fixture_is_explicitly_deferred() -> None:
    facts, source, candidate, provenance = _verified_example_case()
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert len(resolutions) == 1
    resolution = resolutions[0]
    assert resolution.resolution == "verified_omission"
    assert resolution.obligation_id == "primary_example"
    assert facts.selected_fact_ids["repository.examples"] in resolution.fact_ids
    assert facts.selected_fact_ids["example.minimal"] in resolution.fact_ids
    assert "absent-input-fixture:model.obj" in resolution.evidence
    assert "disposition:static-only-source-example-deferred-v1" in resolution.evidence
    assert "without claiming falsity or execution" in resolution.rationale


def test_rejected_source_example_with_absent_fixture_is_explicitly_deferred() -> None:
    facts, source, candidate, provenance = _verified_example_case(
        source_static_verified=False,
        source_validation_reason="unknown_member:FontQaReporter.json_path",
        input_name="Roboto-VariableFont_wdth,wght.ttf",
    )
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert len(resolutions) == 1
    resolution = resolutions[0]
    assert resolution.resolution == "verified_omission"
    assert "absent-input-fixture:Roboto-VariableFont_wdth,wght.ttf" in resolution.evidence
    assert "recorded static validation decision" in resolution.rationale


def test_paired_example_intro_is_omitted_only_with_fact_bound_adjacent_example() -> None:
    facts, _, _, primary_provenance = _verified_example_case()
    source = "# Product\n\n## Quick Start\n\nLoad an OBJ scene:\n\n```python\npass\n```\n"
    intro, example = assess_material_claims(source)
    examples_id = facts.selected_fact_ids["repository.examples"]
    example_text = source.encode()[example.source_byte_start : example.source_byte_end].decode()
    paired_resolution = SourceClaimResolutionV1(
        claim_id=example.claim_id,
        source_byte_start=example.source_byte_start,
        source_byte_end=example.source_byte_end,
        content_sha256=example.content_sha256,
        resolution="verified_equivalence",
        fact_ids=[examples_id],
        candidate_claim_id="claim:100:paired",
        candidate_byte_start=100,
        candidate_byte_end=100 + len(example_text.encode()),
        candidate_content_sha256=example.content_sha256,
        evidence=["exact-paired-example"],
        rationale="Exact paired example remains in the candidate.",
    )
    accepted_primary = (
        primary_provenance,
        [facts.selected_fact_ids["example.minimal"]],
    )

    resolution = verified_paired_example_intro_resolution(
        intro,
        source.encode()[intro.source_byte_start : intro.source_byte_end].decode(),
        example,
        example_text,
        source,
        classify_source_claim_risk(source, intro),
        facts,
        accepted_primary,
        paired_resolution,
        correction_candidate_claim_ids=frozenset({intro.claim_id}),
    )

    assert resolution is not None
    assert resolution.resolution == "verified_omission"
    assert resolution.obligation_id == "primary_example"
    assert "disposition:paired-example-intro-superseded-v1" in resolution.evidence
    assert examples_id not in resolution.fact_ids
    assert f"paired-accepted-fact:{examples_id}" in resolution.evidence


def test_paired_example_intro_without_exact_pair_remains_unresolved() -> None:
    facts, _, _, primary_provenance = _verified_example_case()
    source = "# Product\n\n## Quick Start\n\nLoad an OBJ scene:\n\n```python\npass\n```\n"
    intro, example = assess_material_claims(source)

    assert (
        verified_paired_example_intro_resolution(
            intro,
            source.encode()[intro.source_byte_start : intro.source_byte_end].decode(),
            example,
            source.encode()[example.source_byte_start : example.source_byte_end].decode(),
            source,
            classify_source_claim_risk(source, intro),
            facts,
            (primary_provenance, [facts.selected_fact_ids["example.minimal"]]),
            None,
            correction_candidate_claim_ids=frozenset({intro.claim_id}),
        )
        is None
    )


def test_execution_verified_source_example_cannot_be_deferred() -> None:
    facts, source, candidate, provenance = _verified_example_case(source_execution_verified=True)
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert resolutions == []


def test_source_example_deferral_requires_executed_minimal_example() -> None:
    facts, source, candidate, provenance = _verified_example_case(
        minimal_outcome="STATIC_API_VERIFIED"
    )
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert resolutions == []


def test_unrelated_prose_cannot_receive_source_example_deferral() -> None:
    facts, source, candidate, provenance = _verified_example_case()
    source = "# Product\n\n## Quick Start\n\nOpen model.obj with the product.\n"
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert resolutions == []


def test_source_example_bytes_surviving_candidate_cannot_be_deferred() -> None:
    facts, source, candidate, provenance = _verified_example_case()
    source_code = source.split("```python\n", 1)[1].split("\n```", 1)[0]
    candidate = candidate + f"\n```python\n{source_code}\n```\n"
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert resolutions == []


@pytest.mark.parametrize(
    ("scan_status", "fixture_paths"),
    [
        ("unscanned", []),
        (
            "complete",
            [
                {
                    "path": "testdata/model.obj",
                    "extension": ".obj",
                    "object_id": "d" * 40,
                    "size": 12,
                }
            ],
        ),
    ],
)
def test_source_example_deferral_requires_complete_proof_of_fixture_absence(
    scan_status: str,
    fixture_paths: list[dict[str, object]],
) -> None:
    facts, source, candidate, provenance = _verified_example_case(
        scan_status=scan_status,
        fixture_paths=fixture_paths,
    )
    claim = assess_material_claims(source)[0]

    resolutions = resolve_source_claims(
        source,
        candidate,
        facts,
        provenance,
        authoritative_correction_ranges=[(claim.source_byte_start, claim.source_byte_end)],
        fail_on_unresolved_preserve=False,
    )

    assert resolutions == []
