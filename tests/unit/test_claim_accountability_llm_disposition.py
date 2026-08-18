"""2026-08-18: the bounded LLM-verification fallback for claim
accountability, end to end through `build_readme_claim_accountability_map`.
Proves the exact live scenario this mechanism was built for: a source
claim the mechanical fact-variant check cannot bind (no `llm_disposition_
client`/`repository_root` supplied, today's exact existing behavior) stays
blocking; the same claim becomes accountable only when a client is
supplied AND its verdict is deterministically corroborated -- never on the
model's classification alone."""

from __future__ import annotations

import hashlib

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
from readme_agent.readme.claim_map import ReadmeClaimMapV1

UNBINDABLE_CLAIM = (
    "Select any symbology by name -- canonical or alias -- through the generic entry point.\n"
)
SOURCE = f"# Widget\n\n## Key Capabilities\n\n{UNBINDABLE_CLAIM}"


def _facts() -> ProductFactsV2:
    return ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))


def _claim_map(facts: ProductFactsV2, candidate: str) -> ReadmeClaimMapV1:
    return ReadmeClaimMapV1(
        org_repo=facts.org_repo,
        facts_hash=facts.canonical_hash(),
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        claims=[],
    )


def _find_record(accountability, source_text: str):
    source_bytes = source_text.encode("utf-8")
    for record in accountability.claims:
        if record.stage != "source":
            continue
        text = source_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
        if "generic entry point" in text:
            return record
    raise AssertionError("unbindable claim not found in accountability map")


def test_unbindable_claim_stays_blocking_without_a_client() -> None:
    facts = _facts()
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=SOURCE,
        candidate_text=SOURCE,
        facts=facts,
        generated_claim_map=_claim_map(facts, SOURCE),
    )

    record = _find_record(accountability, SOURCE)

    assert record.currently_accountable is False
    assert record.expected_disposition != "llm_verified_disposition"


def test_unbindable_claim_becomes_accountable_with_a_corroborated_verdict(tmp_path) -> None:
    facts = _facts()
    # source_text == candidate_text here, so this unbindable claim is
    # processed once as a candidate-stage record and once as a source-stage
    # record -- each independently attempts the LLM fallback.
    verdict = ForcedToolResult(
        arguments={
            "classification": "narrative_filler",
            "evidence_type": "none",
            "evidence_ref": "",
            "evidence_quote": "",
            "reasoning": "transitional prose introducing the mechanism, no new claim",
        },
        meta=LLMResponseMeta(),
    )
    client = FixtureForcedToolClient([verdict, verdict])

    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=SOURCE,
        candidate_text=SOURCE,
        facts=facts,
        generated_claim_map=_claim_map(facts, SOURCE),
        llm_disposition_client=client,
        repository_root=tmp_path,
    )

    record = _find_record(accountability, SOURCE)

    assert record.currently_accountable is True
    assert record.expected_disposition == "llm_verified_disposition"


def test_an_uncorroborated_verdict_leaves_the_claim_blocking(tmp_path) -> None:
    """The safety property: a hallucinated/unverifiable verdict must never
    unblock a claim, even when a client is supplied."""
    facts = _facts()
    verdict = ForcedToolResult(
        arguments={
            "classification": "redundant_with_candidate",
            "evidence_type": "candidate_section_reference",
            "evidence_ref": "Key Capabilities",
            "evidence_quote": "text that was never actually in the candidate",
            "reasoning": "claims coverage",
        },
        meta=LLMResponseMeta(),
    )
    client = FixtureForcedToolClient([verdict, verdict])

    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=SOURCE,
        candidate_text=SOURCE,
        facts=facts,
        generated_claim_map=_claim_map(facts, SOURCE),
        llm_disposition_client=client,
        repository_root=tmp_path,
    )

    record = _find_record(accountability, SOURCE)

    assert record.currently_accountable is False
    assert record.expected_disposition != "llm_verified_disposition"
