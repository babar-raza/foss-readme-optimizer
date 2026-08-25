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
import json

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
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


def _facts_with_generate_member() -> ProductFactsV2:
    """2026-08-19: adds a real `generate` public method to the base review
    facts, shaped exactly like `test_verified_template_api_method_index.py::
    _facts_with_api` -- the same complete-catalog access `known_public_
    surface_bare_names()` reads to give the `api_surface_member` evidence
    path something real to confirm membership against."""

    base = _facts()
    source = base.selected_fact("product.identity").source
    api = FactRecordV2(
        fact_id="api.public_surface:disposition-test",
        field="api.public_surface",
        value={
            "modules": [{"module": "aspose.barcode", "exports": ["Generator"]}],
            "classes": [{"module": "aspose.barcode", "name": "Generator", "members": []}],
            "coordinate_catalog": {
                "classes": [
                    {
                        "module": "aspose.barcode",
                        "name": "Generator",
                        "members": [
                            {
                                "name": "generate",
                                "kind": "method",
                                "surface": "generate(symbology, data)",
                                "declared_by": "Generator",
                                "inherited": False,
                            }
                        ],
                    }
                ],
                "presentation_exclusions": [],
            },
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-source",
        confidence=1.0,
        affected_surfaces=["readme.api_method_index"],
    )
    return base.model_copy(
        update={
            "facts": [*base.facts, api],
            "selected_fact_ids": {**base.selected_fact_ids, api.field: api.fact_id},
        }
    )


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


CANDIDATE_WITHOUT_CLAIM = "# Widget\n\n## Key Capabilities\n\nSomething else entirely.\n"


def test_dropped_claim_stays_unjustified_loss_without_a_client() -> None:
    """The exact live scenario this mechanism was built for: a source claim
    genuinely absent from the candidate (`survives_in_candidate is False`),
    not merely present-but-unbound. A prior wiring bug gated the LLM
    corroboration attempt on `survives is not False`, which excluded this
    exact case -- the caller never even tried the client, so the fallback
    was dead code for every real lost-source-claim block observed live
    (aspose-barcode-foss et al.)."""

    facts = _facts()
    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=SOURCE,
        candidate_text=CANDIDATE_WITHOUT_CLAIM,
        facts=facts,
        generated_claim_map=_claim_map(facts, CANDIDATE_WITHOUT_CLAIM),
    )

    record = _find_record(accountability, SOURCE)

    assert record.survives_in_candidate is False
    assert record.currently_accountable is False
    assert record.expected_disposition == "unjustified_loss"


def test_dropped_claim_becomes_accountable_with_a_corroborated_verdict(tmp_path) -> None:
    facts = _facts()
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
        candidate_text=CANDIDATE_WITHOUT_CLAIM,
        facts=facts,
        generated_claim_map=_claim_map(facts, CANDIDATE_WITHOUT_CLAIM),
        llm_disposition_client=client,
        repository_root=tmp_path,
    )

    record = _find_record(accountability, SOURCE)

    assert record.survives_in_candidate is False
    assert record.currently_accountable is True
    assert record.expected_disposition == "llm_verified_disposition"


SUPERSEDING_QUOTE = (
    "Generate every supported symbology through a single verified entry point wrapper."
)
CANDIDATE_WITH_SUPERSEDING_SLOT = f"# Widget\n\n## Key Capabilities\n\n{SUPERSEDING_QUOTE}\n"


def test_an_excluded_with_reason_verdict_flows_through_llm_verified_disposition(tmp_path) -> None:
    """E5 slice 1: an accepted excluded_with_reason record reaches
    expected_disposition through the identical llm_disposition_corroborated
    boolean as every other accepted classification -- no new consumer path."""

    facts = _facts()
    verdict = ForcedToolResult(
        arguments={
            "classification": "excluded_with_reason",
            "evidence_type": "checkable_predicate",
            "evidence_ref": "superseded_by_verified_slot:key-capabilities",
            "evidence_quote": SUPERSEDING_QUOTE,
            "reasoning": "the verified capabilities section supersedes this sentence",
        },
        meta=LLMResponseMeta(),
    )
    client = FixtureForcedToolClient([verdict, verdict])

    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=SOURCE,
        candidate_text=CANDIDATE_WITH_SUPERSEDING_SLOT,
        facts=facts,
        generated_claim_map=_claim_map(facts, CANDIDATE_WITH_SUPERSEDING_SLOT),
        llm_disposition_client=client,
        repository_root=tmp_path,
    )

    record = _find_record(accountability, SOURCE)

    assert record.survives_in_candidate is False
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


API_MEMBER_CLAIM = (
    "Select any symbology by name -- canonical or alias -- through the generic `generate()` "
    "entry point.\n"
)
API_MEMBER_SOURCE = f"# Widget\n\n## Key Capabilities\n\n{API_MEMBER_CLAIM}"


def _find_api_member_record(accountability, source_text: str):
    source_bytes = source_text.encode("utf-8")
    for record in accountability.claims:
        if record.stage != "source":
            continue
        text = source_bytes[record.source_byte_start : record.source_byte_end].decode("utf-8")
        if "canonical or alias" in text:
            return record
    raise AssertionError("api-surface-member claim not found in accountability map")


def test_api_surface_member_evidence_unblocks_the_real_barcode_python_claim(tmp_path) -> None:
    """2026-08-19, second aspose.org lesson: the exact claim shape that stays
    blocked on barcode-python (aspose.org's own content-dispositions.json
    unit_id u0017) -- a claim that is EDITORIAL PARAPHRASE of a real API
    member's behavior rather than a literal-text quote -- becomes accountable
    once `build_readme_claim_accountability_map` derives the real public
    member bare-name set from `facts` and threads it through to
    `corroborate_claim_disposition()`'s new `api_surface_member` branch."""

    facts = _facts_with_generate_member()
    verdict = ForcedToolResult(
        arguments={
            "classification": "verified_against_source",
            "evidence_type": "api_surface_member",
            "evidence_ref": "generate",
            "evidence_quote": "",
            "reasoning": "generate() is a real, public entry point",
        },
        meta=LLMResponseMeta(),
    )
    client = FixtureForcedToolClient([verdict, verdict])

    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=API_MEMBER_SOURCE,
        candidate_text=API_MEMBER_SOURCE,
        facts=facts,
        generated_claim_map=_claim_map(facts, API_MEMBER_SOURCE),
        llm_disposition_client=client,
        repository_root=tmp_path,
    )

    record = _find_api_member_record(accountability, API_MEMBER_SOURCE)

    assert record.currently_accountable is True
    assert record.expected_disposition == "llm_verified_disposition"


def test_api_surface_member_evidence_is_refused_when_the_member_is_not_real(tmp_path) -> None:
    """Without a real `generate` member in `facts` (the plain review-fixture
    facts, no api.public_surface fact at all), `known_public_surface_bare_
    names()` derives an empty set and the identical verdict is refused --
    the claim stays blocking exactly as it did before this evidence path
    existed."""

    facts = _facts()
    verdict = ForcedToolResult(
        arguments={
            "classification": "verified_against_source",
            "evidence_type": "api_surface_member",
            "evidence_ref": "generate",
            "evidence_quote": "",
            "reasoning": "generate() is a real, public entry point",
        },
        meta=LLMResponseMeta(),
    )
    client = FixtureForcedToolClient([verdict, verdict])

    accountability = build_readme_claim_accountability_map(
        org_repo=facts.org_repo,
        source_text=API_MEMBER_SOURCE,
        candidate_text=API_MEMBER_SOURCE,
        facts=facts,
        generated_claim_map=_claim_map(facts, API_MEMBER_SOURCE),
        llm_disposition_client=client,
        repository_root=tmp_path,
    )

    record = _find_api_member_record(accountability, API_MEMBER_SOURCE)

    assert record.currently_accountable is False
    assert record.expected_disposition != "llm_verified_disposition"


def test_resolve_claim_disposition_context_returns_the_standard_three_values() -> None:
    """The shared helper gate 2 (readme_factuality.py) now uses to close the
    two-gate finding: same client/repository_root/ratchet-path shape gate 1
    (build_presentation_plan.py::execute()) already resolves inline."""

    from readme_agent import paths
    from readme_agent.readme.claim_accountability_llm_disposition import (
        claim_disposition_ratchet_path,
        resolve_claim_disposition_context,
    )
    from readme_agent.registry.loader import require_listed

    org_repo = "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python"
    entry = require_listed(org_repo)

    client, repository_root, ratchet_path = resolve_claim_disposition_context(org_repo)

    assert client is not None
    assert repository_root == paths.baseline_dir(entry.org, entry.repo_name)
    assert ratchet_path == claim_disposition_ratchet_path(org_repo)


def test_default_claim_disposition_client_uses_observed_non_truncating_ceiling() -> None:
    from readme_agent.readme.claim_accountability_llm_disposition import (
        default_claim_disposition_client,
    )

    client = default_claim_disposition_client()

    assert client.max_tokens == 2400


def test_resolve_claim_disposition_context_fails_closed_for_an_unlisted_repo() -> None:
    from readme_agent.errors import NotAllowlistedError
    from readme_agent.readme.claim_accountability_llm_disposition import (
        resolve_claim_disposition_context,
    )

    try:
        resolve_claim_disposition_context("not-a-real-org/not-a-real-repo")
        raise AssertionError("expected NotAllowlistedError")
    except NotAllowlistedError:
        pass


def test_a_per_repo_replayed_verdict_backfills_the_shared_store(tmp_path, monkeypatch) -> None:
    """2026-08-19: a verdict replayed from the per-repo ratchet alone never
    reached the shared, portfolio-wide store -- only a FRESH model
    acceptance wrote to both. Live-observed: note-python's own ratchet held
    an accepted `redundant_with_candidate` verdict for the exact boilerplate
    claim (content hash 7ff54c1da64deecb) page-python's real source also
    carries verbatim, but the shared store never had it, so page-python
    could not replay it and hit a fresh block instead of a free reuse."""

    import readme_agent.paths as paths_module
    from readme_agent.readme.claim_accountability_llm_disposition import (
        claim_disposition_ratchet_path,
        llm_verified_claim_disposition,
        shared_claim_disposition_ratchet_path,
    )

    monkeypatch.setattr(paths_module, "runs_dir", lambda: tmp_path / "runs")

    claim_text = "No required third-party package dependencies."
    content_sha256 = hashlib.sha256(claim_text.encode("utf-8")).hexdigest()
    candidate_text = "## Dependencies\n\nOnly optional dependencies are declared.\n"

    per_repo_path = claim_disposition_ratchet_path("acme/widget")
    per_repo_path.parent.mkdir(parents=True, exist_ok=True)
    per_repo_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "accepted": {
                    content_sha256: {
                        "classification": "redundant_with_candidate",
                        "evidence_type": "candidate_section_reference",
                        "evidence_ref": "Dependencies",
                        "evidence_quote": "Only optional dependencies are declared.",
                        "reasoning": "covered by the candidate's own Dependencies section",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    shared_path = shared_claim_disposition_ratchet_path()
    assert not shared_path.exists()

    record = llm_verified_claim_disposition(
        "source:claim:1:aa",
        claim_text,
        candidate_text,
        tmp_path,
        None,  # no client needed -- the per-repo store must satisfy this alone
        ratchet_path=per_repo_path,
    )

    assert record is not None
    assert record.classification == "redundant_with_candidate"
    shared_accepted = json.loads(shared_path.read_text(encoding="utf-8"))["accepted"]
    assert shared_accepted[content_sha256]["classification"] == "redundant_with_candidate"
