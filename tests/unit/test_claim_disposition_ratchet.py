"""The claim-disposition ratchet (2026-08-18 Gate A recovery): an accepted,
deterministically corroborated verdict is persisted per claim-content hash and
replayed on later runs with zero provider calls -- while its evidence still
corroborates against the CURRENT candidate/source. Regression anchor: with no
ratchet, every live re-run re-rolled the model per claim, and the observed
corroboration nondeterminism made claim counts fluctuate (words 1->2, note
2->1->2) with unchanged inputs.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from readme_agent import paths
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.claim_accountability_llm_disposition import (
    claim_disposition_ratchet_path,
    llm_verified_claim_disposition,
    shared_claim_disposition_ratchet_path,
)

CLAIM = "Select any symbology by name -- canonical or alias -- through the generic entry point."
CANDIDATE = f"# Widget\n\n## Key Capabilities\n\n{CLAIM}\n"


@pytest.fixture(autouse=True)
def _isolated_shared_ratchet_store(monkeypatch, tmp_path):
    """The portfolio-shared store resolves through paths.runs_dir(); unit
    tests must never read from or write to a real runs/ directory."""

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")


def _redundant_verdict(quote: str) -> ForcedToolResult:
    return ForcedToolResult(
        arguments={
            "classification": "redundant_with_candidate",
            "evidence_type": "candidate_section_reference",
            "evidence_ref": "Key Capabilities",
            "evidence_quote": quote,
            "reasoning": "the candidate already states this capability",
        },
        meta=LLMResponseMeta(),
    )


class _ExplodingClient:
    """Proves a code path never consulted the model."""

    def call(self, messages, tool_schema):
        raise AssertionError("the ratchet replay must not call the model")


class TestRatchetReplay:
    def test_an_accepted_verdict_is_persisted_and_replayed_without_the_model(self, tmp_path):
        ratchet = tmp_path / "ratchet.json"
        first = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=ratchet,
        )
        assert first is not None and first.corroborated

        replayed = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            _ExplodingClient(),
            ratchet_path=ratchet,
        )
        assert replayed is not None
        assert replayed.corroborated is True
        assert replayed.classification == "redundant_with_candidate"

    def test_replay_recorroborates_against_the_current_candidate(self, tmp_path):
        """A stored quote the new candidate no longer contains must NOT be
        accepted from the ratchet -- the model is consulted again live."""

        ratchet = tmp_path / "ratchet.json"
        llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=ratchet,
        )

        changed_candidate = "# Widget\n\n## Key Capabilities\n\nSomething else entirely.\n"
        fresh_verdict = ForcedToolResult(
            arguments={
                "classification": "narrative_filler",
                "evidence_type": "none",
                "evidence_ref": "",
                "evidence_quote": "",
                "reasoning": "transitional prose, no factual claim",
            },
            meta=LLMResponseMeta(),
        )
        result = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            changed_candidate,
            tmp_path,
            FixtureForcedToolClient([fresh_verdict]),
            ratchet_path=ratchet,
        )
        assert result is not None
        assert result.classification == "narrative_filler"

    def test_an_accepted_excluded_with_reason_verdict_replays_like_the_others(self, tmp_path):
        """E5 slice 1: the new classification persists and replays through
        the exact same store and deterministic re-corroboration as the
        pre-existing classifications."""

        ratchet = tmp_path / "ratchet.json"
        stale_claim = "Requires widget 1.2.3 exactly."
        candidate = "# Widget\n\nRequires widget 2.0 or newer.\n"
        verdict = ForcedToolResult(
            arguments={
                "classification": "excluded_with_reason",
                "evidence_type": "checkable_predicate",
                "evidence_ref": "stale_version_string:1.2.3",
                "evidence_quote": "",
                "reasoning": "the candidate no longer pins this version anywhere",
            },
            meta=LLMResponseMeta(),
        )
        first = llm_verified_claim_disposition(
            "claim-1",
            stale_claim,
            candidate,
            tmp_path,
            FixtureForcedToolClient([verdict]),
            ratchet_path=ratchet,
        )
        assert first is not None and first.corroborated
        assert first.classification == "excluded_with_reason"

        replayed = llm_verified_claim_disposition(
            "claim-1",
            stale_claim,
            candidate,
            tmp_path,
            _ExplodingClient(),
            ratchet_path=ratchet,
        )
        assert replayed is not None
        assert replayed.corroborated is True
        assert replayed.classification == "excluded_with_reason"
        assert replayed.evidence_ref == "stale_version_string:1.2.3"

    def test_a_rejected_verdict_is_never_persisted(self, tmp_path):
        ratchet = tmp_path / "ratchet.json"
        hallucinated = _redundant_verdict("text that is not in the candidate")
        result = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([hallucinated]),
            ratchet_path=ratchet,
        )
        assert result is None
        assert not ratchet.exists()

    def test_a_malformed_ratchet_file_degrades_to_a_live_call(self, tmp_path):
        ratchet = tmp_path / "ratchet.json"
        ratchet.write_text("{corrupt", encoding="utf-8")
        result = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=ratchet,
        )
        assert result is not None and result.corroborated
        # And the accepted verdict repaired the store.
        payload = json.loads(ratchet.read_text(encoding="utf-8"))
        content_sha256 = hashlib.sha256(CLAIM.encode("utf-8")).hexdigest()
        assert content_sha256 in payload["accepted"]

    def test_no_ratchet_path_reproduces_existing_behavior(self, tmp_path):
        result = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
        )
        assert result is not None and result.corroborated
        assert list(tmp_path.glob("**/*.json")) == []

    def test_verdicts_are_keyed_by_claim_content_not_claim_id(self, tmp_path):
        """Claim ids embed byte coordinates that shift between runs; the
        stable key is the claim text hash, so a relocated identical claim
        still replays."""

        ratchet = tmp_path / "ratchet.json"
        llm_verified_claim_disposition(
            "source:claim:4064:aaaa",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=ratchet,
        )
        replayed = llm_verified_claim_disposition(
            "source:claim:5121:bbbb",
            CLAIM,
            CANDIDATE,
            tmp_path,
            _ExplodingClient(),
            ratchet_path=ratchet,
        )
        assert replayed is not None and replayed.corroborated
        assert replayed.claim_id == "source:claim:5121:bbbb"


class TestSharedPortfolioRatchet:
    """E5 design principle 5: identical claim text recurs verbatim across
    repos, so accepted verdicts are shared portfolio-wide through a
    read-through store -- safe by construction because every replay still
    passes the full deterministic corroboration in the replaying repo."""

    def test_acceptance_in_repo_a_replays_in_repo_b_without_the_model(self, tmp_path):
        repo_a = tmp_path / "org__repo-a" / "claim-disposition-ratchet.json"
        repo_b = tmp_path / "org__repo-b" / "claim-disposition-ratchet.json"

        first = llm_verified_claim_disposition(
            "claim-a",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=repo_a,
        )
        assert first is not None and first.corroborated
        # A fresh acceptance persists to BOTH stores.
        content_sha256 = hashlib.sha256(CLAIM.encode("utf-8")).hexdigest()
        assert content_sha256 in json.loads(repo_a.read_text(encoding="utf-8"))["accepted"]
        shared = shared_claim_disposition_ratchet_path()
        assert content_sha256 in json.loads(shared.read_text(encoding="utf-8"))["accepted"]

        replayed = llm_verified_claim_disposition(
            "claim-b",
            CLAIM,
            CANDIDATE,
            tmp_path,
            _ExplodingClient(),
            ratchet_path=repo_b,
        )
        assert replayed is not None
        assert replayed.corroborated is True
        assert replayed.classification == "redundant_with_candidate"

    def test_shared_replay_still_gates_on_current_repo_corroboration(self, tmp_path):
        """A shared verdict whose evidence the replaying repo's candidate
        does not contain must fall through to a live call -- never be
        accepted portfolio-wide on repo A's corroboration alone."""

        repo_a = tmp_path / "org__repo-a" / "claim-disposition-ratchet.json"
        repo_b = tmp_path / "org__repo-b" / "claim-disposition-ratchet.json"
        llm_verified_claim_disposition(
            "claim-a",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=repo_a,
        )

        repo_b_candidate = "# Widget\n\n## Key Capabilities\n\nSomething else entirely.\n"
        fresh_verdict = ForcedToolResult(
            arguments={
                "classification": "narrative_filler",
                "evidence_type": "none",
                "evidence_ref": "",
                "evidence_quote": "",
                "reasoning": "transitional prose, no factual claim",
            },
            meta=LLMResponseMeta(),
        )
        result = llm_verified_claim_disposition(
            "claim-b",
            CLAIM,
            repo_b_candidate,
            tmp_path,
            FixtureForcedToolClient([fresh_verdict]),
            ratchet_path=repo_b,
        )
        assert result is not None
        assert result.classification == "narrative_filler"

    def test_a_malformed_shared_store_degrades_to_empty(self, tmp_path):
        shared = shared_claim_disposition_ratchet_path()
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text("{corrupt", encoding="utf-8")
        ratchet = tmp_path / "org__repo-a" / "claim-disposition-ratchet.json"
        result = llm_verified_claim_disposition(
            "claim-1",
            CLAIM,
            CANDIDATE,
            tmp_path,
            FixtureForcedToolClient([_redundant_verdict(CLAIM)]),
            ratchet_path=ratchet,
        )
        assert result is not None and result.corroborated
        # The accepted verdict repaired the shared store too.
        payload = json.loads(shared.read_text(encoding="utf-8"))
        content_sha256 = hashlib.sha256(CLAIM.encode("utf-8")).hexdigest()
        assert content_sha256 in payload["accepted"]


def test_ratchet_path_is_repo_scoped(monkeypatch, tmp_path):
    import readme_agent.paths as paths

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    path = claim_disposition_ratchet_path("org/repo")
    assert path == tmp_path / "runs" / "readme-poc" / "org__repo" / "claim-disposition-ratchet.json"


def test_end_to_end_map_replay_survives_an_unavailable_model(tmp_path):
    """Through the real accountability map: run 1 accepts with a live client
    and persists; run 2's client would explode if consulted -- the claim
    stays accountable purely from the replayed, re-corroborated verdict."""

    from readme_agent.facts.schema_v2 import ProductFactsV2
    from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
    from readme_agent.readme.claim_accountability import build_readme_claim_accountability_map
    from readme_agent.readme.claim_map import ReadmeClaimMapV1

    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    source = f"# Widget\n\n## Key Capabilities\n\n{CLAIM}\n"
    claim_map = ReadmeClaimMapV1(
        org_repo=facts.org_repo,
        facts_hash=facts.canonical_hash(),
        candidate_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        claims=[],
    )
    ratchet = tmp_path / "ratchet.json"
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

    def _records(accountability):
        source_bytes = source.encode("utf-8")
        return [
            record
            for record in accountability.claims
            if "generic entry point"
            in source_bytes[record.source_byte_start : record.source_byte_end].decode(
                "utf-8", errors="replace"
            )
        ]

    first = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=source,
        facts=facts,
        generated_claim_map=claim_map,
        llm_disposition_client=FixtureForcedToolClient([verdict, verdict]),
        repository_root=tmp_path,
        disposition_ratchet_path=ratchet,
    )
    assert any(record.currently_accountable for record in _records(first))

    second = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=source,
        candidate_text=source,
        facts=facts,
        generated_claim_map=claim_map,
        llm_disposition_client=_ExplodingClient(),
        repository_root=tmp_path,
        disposition_ratchet_path=ratchet,
    )
    replay_records = _records(second)
    assert replay_records
    assert all(record.currently_accountable for record in replay_records)
    assert all(
        record.expected_disposition == "llm_verified_disposition" for record in replay_records
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
