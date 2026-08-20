"""Content-identity fallback: when the composition ledger is present but its
positional `source_placements` do not cover a claim's exact span at all (the
real 2026-08-20 Note/Python gap -- a verified-template compile commonly
carries only a single whole-document `lineage_only` provenance binding, never
a per-claim positional placement), byte-identical content on both sides must
still resolve as verified equivalence, never fall through to
unjustified_loss/unbound_generated. Generic content-hash matching, never a
repository- or claim-ID-specific rule."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import ReadmeClaimMapV1
from readme_agent.readme.composition_lineage_models import ReadmeCompositionLedgerV1

CLAIM = "No required third-party package dependencies.\n"


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))


def _placementless_ledger(source: str, candidate: str) -> ReadmeCompositionLedgerV1:
    source_bytes = source.encode("utf-8")
    candidate_bytes = candidate.encode("utf-8")
    return ReadmeCompositionLedgerV1.model_construct(
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        source_bytes=len(source_bytes),
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        candidate_bytes=len(candidate_bytes),
        operation_reconstruction_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        source_placements=[],
        candidate_provenance=[],
        segments=[],
    )


def _accountability(source: str, candidate: str, ledger: ReadmeCompositionLedgerV1):
    facts = _facts()
    claim_map = ReadmeClaimMapV1(
        org_repo=facts.org_repo,
        facts_hash=facts.canonical_hash(),
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        claims=[],
    )
    return build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=candidate,
        facts=facts,
        generated_claim_map=claim_map,
        composition_ledger=ledger,
    )


def _stage_records(accountability, stage: str):
    return sorted(
        (record for record in accountability.claims if record.stage == stage),
        key=lambda record: record.source_byte_start,
    )


def test_byte_identical_content_resolves_via_content_hash_when_ledger_has_no_placement():
    """The real Note shape: `composition_ledger` is supplied but its
    `source_placements` array does not cover this span at all -- confirmed
    live (2026-08-20 note-ledger-accountability investigation) for
    `source:claim:4064` / `candidate:claim:4579`, both citing the identical
    sentence "No required third-party package dependencies." under the
    identical `## Dependencies` -> `### Required Package Dependencies`
    heading path, with matching `content_sha256` on both accountability
    records."""

    source = f"# Source\n\n## Dependencies\n\n{CLAIM}"
    candidate = f"# Candidate\n\n## Dependencies\n\n{CLAIM}"

    accountability = _accountability(source, candidate, _placementless_ledger(source, candidate))

    source_record = _stage_records(accountability, "source")[0]
    candidate_record = _stage_records(accountability, "candidate")[0]
    assert source_record.survives_in_candidate is True
    assert source_record.expected_disposition == "verified_equivalence"
    assert source_record.currently_accountable is True
    assert candidate_record.origin == "inherited"
    assert candidate_record.expected_disposition == "verified_equivalence"
    assert candidate_record.currently_accountable is True


def test_ambiguous_duplicate_content_across_unmatched_claims_does_not_fall_back():
    """Two source claims share identical content and only one candidate claim
    is unmatched: the fallback must refuse (stay unaccountable) rather than
    guess which source claim the surviving candidate content belongs to."""

    source = f"# Source\n\n{CLAIM}\n{CLAIM}"
    candidate = f"# Candidate\n\n{CLAIM}"

    accountability = _accountability(source, candidate, _placementless_ledger(source, candidate))

    source_records = _stage_records(accountability, "source")
    assert len(source_records) == 2
    assert all(record.survives_in_candidate is False for record in source_records)
    assert all(record.currently_accountable is False for record in source_records)


def test_genuinely_lost_content_still_reports_unjustified_loss():
    """Regression guard: the content-identity fallback must never launder a
    genuinely dropped source claim into a false equivalence."""

    source = f"# Source\n\n{CLAIM}"
    candidate = "# Candidate\n\nCompletely unrelated replacement content.\n"

    accountability = _accountability(source, candidate, _placementless_ledger(source, candidate))

    source_record = _stage_records(accountability, "source")[0]
    assert source_record.survives_in_candidate is False
    assert source_record.expected_disposition == "unjustified_loss"
    assert source_record.currently_accountable is False
