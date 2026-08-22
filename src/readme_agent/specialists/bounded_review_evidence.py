"""Build deterministic bounded-review inputs at the candidate boundary."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm import prompt_registry
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.specialists.bounded_review_contracts import BoundedReviewPlanV1
from readme_agent.specialists.bounded_review_coverage import (
    CoverageLedgerV1,
    CoverageValidationV1,
    build_coverage_ledger,
    validate_coverage_ledger,
)
from readme_agent.specialists.bounded_review_packets import (
    build_atomic_units,
    plan_bounded_review_packets,
)

_FACTUAL_PROMPT_ID = "factual_readme_plan_review"
_VISITOR_PROMPT_ID = "blind_readme_quality_review"
# Keep indivisible Markdown tables and fences atomic while still bounding every
# reviewer input below the 240k whole-document trigger. The qualified 3D Python
# API inventory requires 101,013 characters including its fact context.
_CANDIDATE_REVIEW_BUDGET_CHARS = 120_000


def build_candidate_bounded_review_evidence(
    *,
    candidate_text: str,
    document_plan: ReadmeDocumentPlanV1,
    product_facts: ProductFactsV2,
) -> tuple[BoundedReviewPlanV1, CoverageLedgerV1, CoverageValidationV1]:
    """Prepare exhaustive reviewer packets without making provider calls."""

    accountability = document_plan.claim_accountability
    if accountability is None:
        raise ValueError("candidate boundary requires the validated claim-accountability map")
    plan = plan_bounded_review_packets(
        candidate_text=candidate_text,
        document_plan=document_plan,
        claim_accountability=accountability,
        product_facts=product_facts,
        budget_chars=_CANDIDATE_REVIEW_BUDGET_CHARS,
        factual_prompt_sha256=prompt_registry.prompt_hash(_FACTUAL_PROMPT_ID),
        visitor_prompt_sha256=prompt_registry.prompt_hash(_VISITOR_PROMPT_ID),
        candidate_content_provenance=document_plan.candidate_content_provenance,
    )
    units = build_atomic_units(
        candidate_text,
        accountability,
        product_facts,
        document_plan.candidate_content_provenance,
    )
    coverage = build_coverage_ledger(plan, atomic_units=units)
    return plan, coverage, validate_coverage_ledger(coverage)


__all__ = ["build_candidate_bounded_review_evidence"]
