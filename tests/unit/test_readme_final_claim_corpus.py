"""Complete inherited and generated README claim-accountability controls."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.claim_accountability import (
    build_readme_claim_accountability_map,
)
from readme_agent.readme.claim_accountability_models import ReadmeClaimAccountabilityMapV1
from readme_agent.readme.claim_accountability_validation import (
    validate_claim_accountability_map,
)
from readme_agent.readme.claim_map import ReadmeClaimMapV1, build_readme_claim_map
from readme_agent.readme.document_renderer import build_readme_document_candidate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPRESENTATIVES = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-contextual-linking"
    / "representatives"
)


def _case(platform: str):
    root = REPRESENTATIVES / platform
    source = (root / "original-readme.md").read_text(encoding="utf-8")
    facts = ProductFactsV2.model_validate_json(
        (root / "product-facts-v2.json").read_text(encoding="utf-8")
    )
    revision = next(
        fact.source.source_revision
        for fact in facts.facts
        if fact.source.source_revision is not None
    )
    candidate, plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=revision,
    )
    claim_map = build_readme_claim_map(
        plan,
        facts,
        source_text=source,
        candidate_text=candidate,
    )
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=claim_map,
    )
    assert plan.claim_accountability == accountability
    return source, candidate, facts, plan, accountability


def _record_containing(
    accountability: ReadmeClaimAccountabilityMapV1,
    document: str,
    stage: str,
    needle: str,
):
    document_bytes = document.encode("utf-8")
    matches = [
        record
        for record in accountability.claims
        if record.stage == stage
        and needle
        in document_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
    ]
    assert len(matches) == 1, (stage, needle, len(matches))
    return matches[0]


@pytest.mark.parametrize("platform", ["java", "python", "typescript"])
def test_real_source_and_candidate_claim_inventories_are_complete(platform: str):
    source, candidate, _facts, _plan, accountability = _case(platform)
    source_records = [record for record in accountability.claims if record.stage == "source"]
    candidate_records = [record for record in accountability.claims if record.stage == "candidate"]

    assert len(source_records) == len(assess_material_claims(source))
    assert len(candidate_records) == len(assess_material_claims(candidate))
    assert len({record.claim_id for record in accountability.claims}) == len(accountability.claims)
    for document, records in ((source, source_records), (candidate, candidate_records)):
        document_bytes = document.encode("utf-8")
        for record in records:
            content = document_bytes[record.source_byte_start : record.source_byte_end]
            assert hashlib.sha256(content).hexdigest() == record.content_sha256
            assert record.expected_disposition
            assert record.rationale


def test_real_corpus_freezes_parity_performance_format_installation_and_example_controls():
    python_source, python_candidate, _python_facts, _python_plan, python_map = _case("python")
    (
        typescript_source,
        _typescript_candidate,
        _typescript_facts,
        _typescript_plan,
        typescript_map,
    ) = _case("typescript")

    parity = _record_containing(
        python_map,
        python_source,
        "source",
        "same public API design",
    )
    performance = _record_containing(
        python_map,
        python_source,
        "source",
        "higher performance",
    )
    stale_install = _record_containing(
        python_map,
        python_source,
        "source",
        "pip install aspose-3d-foss",
    )
    stale_example = _record_containing(
        python_map,
        python_source,
        "source",
        "ObjLoadOptions",
    )
    verified_example = _record_containing(
        python_map,
        python_candidate,
        "candidate",
        "from aspose.threed import Scene",
    )
    format_claim = _record_containing(
        typescript_map,
        typescript_source,
        "source",
        "FBX - Autodesk FBX format support",
    )

    assert parity.expected_disposition == "unjustified_loss"
    assert performance.expected_disposition == "unjustified_loss"
    assert stale_install.expected_disposition == "authoritative_owner_validation"
    assert stale_example.expected_disposition == "unjustified_loss"
    assert all(
        not record.currently_accountable
        for record in (parity, performance, stale_install, stale_example)
    )
    assert verified_example.expected_disposition == "accepted_fact"
    assert verified_example.currently_accountable is True
    assert format_claim.expected_disposition == "accepted_fact"


def test_preservation_and_regeneration_do_not_hide_missing_accountability():
    _source, _candidate, facts, _plan, _accountability = _case("python")
    source = "# Product\n\nMaintainer performance parity statement.\n"
    candidate = "# Product\n\nGenerated fastest-in-class statement.\n"
    empty_claim_map = ReadmeClaimMapV1(
        org_repo=facts.org_repo,
        facts_hash=facts.canonical_hash(),
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        claims=[],
    )

    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=empty_claim_map,
    )
    source_record = _record_containing(
        accountability,
        source,
        "source",
        "Maintainer performance parity",
    )
    candidate_record = _record_containing(
        accountability,
        candidate,
        "candidate",
        "Generated fastest-in-class",
    )

    assert source_record.expected_disposition == "unjustified_loss"
    assert source_record.currently_accountable is False
    assert candidate_record.expected_disposition == "unbound_generated"
    assert candidate_record.currently_accountable is False


def test_renderer_embeds_a_structurally_verified_map_and_exposes_approval_blockers():
    source, candidate, facts, plan, accountability = _case("python")

    verdict = validate_claim_accountability_map(
        accountability,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        operations=plan.operations,
    )

    assert verdict.valid is True
    assert verdict.approval_eligible is False
    assert verdict.blocking_claim_ids
    assert all(verdict.checks.values())


def test_stale_accountability_span_fails_closed():
    source, candidate, facts, plan, accountability = _case("java")
    first = accountability.claims[0].model_copy(update={"content_sha256": "0" * 64})
    tampered = accountability.model_copy(update={"claims": [first, *accountability.claims[1:]]})

    verdict = validate_claim_accountability_map(
        tampered,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        operations=plan.operations,
    )

    assert verdict.valid is False
    assert verdict.checks["claim_spans_exact"] is False
