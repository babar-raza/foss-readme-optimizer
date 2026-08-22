"""Tests for the standalone bounded-review packetizer, validator, aggregator, and repair router.

Builds minimal-but-valid ``ReadmeDocumentPlanV1`` / ``ReadmeClaimAccountabilityMapV1`` /
``ProductFactsV2`` instances with a private helper below (no new support module -- outside the
granted writable test scope) against the synthetic ~162KB candidate at
``tests/fixtures/bounded_review_packets/candidate.md``. Claim/provenance spans are located by
searching for exact literal marker sentences in the loaded fixture text at test time, never by
hardcoded byte offsets, so the fixture can be edited without hand-recomputing spans as long as the
markers are preserved.
"""

from __future__ import annotations

from bounded_review_accountability_support import (
    DEFAULT_CLAIM_ACCOUNTABILITY,
    DEFAULT_DO_NOT_CLAIM,
    DEFAULT_DOCUMENT_PLAN,
    DEFAULT_FACTS,
    DEFAULT_PROVENANCE,
)
from bounded_review_fact_support import (
    CANDIDATE_TEXT,
    DEFAULT_BUDGET_CHARS,
    FACTUAL_PROMPT_SHA256,
    VISITOR_PROMPT_SHA256,
)

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
)
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
    ReadmeDocumentPlanV1,
)
from readme_agent.specialists import bounded_review_packets as brp


def _plan(
    *,
    candidate_text: str = CANDIDATE_TEXT,
    document_plan: ReadmeDocumentPlanV1 = DEFAULT_DOCUMENT_PLAN,
    claim_accountability: ReadmeClaimAccountabilityMapV1 = DEFAULT_CLAIM_ACCOUNTABILITY,
    product_facts: ProductFactsV2 = DEFAULT_FACTS,
    do_not_claim: list[dict] | None = None,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
    budget_chars: int = DEFAULT_BUDGET_CHARS,
    **kwargs: object,
) -> brp.BoundedReviewPlanV1:
    return brp.plan_bounded_review_packets(
        candidate_text=candidate_text,
        document_plan=document_plan,
        claim_accountability=claim_accountability,
        product_facts=product_facts,
        do_not_claim=DEFAULT_DO_NOT_CLAIM if do_not_claim is None else do_not_claim,
        candidate_content_provenance=(
            DEFAULT_PROVENANCE
            if candidate_content_provenance is None
            else candidate_content_provenance
        ),
        budget_chars=budget_chars,
        factual_prompt_sha256=FACTUAL_PROMPT_SHA256,
        visitor_prompt_sha256=VISITOR_PROMPT_SHA256,
        **kwargs,
    )


def _atomic_units(
    *,
    candidate_text: str = CANDIDATE_TEXT,
    claim_accountability: ReadmeClaimAccountabilityMapV1 = DEFAULT_CLAIM_ACCOUNTABILITY,
    product_facts: ProductFactsV2 = DEFAULT_FACTS,
    candidate_content_provenance: list[CandidateContentProvenanceV1] | None = None,
) -> tuple[brp.AtomicUnitV1, ...]:
    provenance = (
        DEFAULT_PROVENANCE if candidate_content_provenance is None else candidate_content_provenance
    )
    return brp.build_atomic_units(candidate_text, claim_accountability, product_facts, provenance)
