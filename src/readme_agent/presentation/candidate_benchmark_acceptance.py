"""Resolve real per-dimension benchmark-acceptance verdicts from already-collected evidence.

Distinct from `candidate_benchmark_comparison.py`: that module proves evidence *files exist* per
dimension (`status="EVIDENCE_BOUND_PENDING_ACCEPTANCE"`) without judging content.  This module
consumes that comparison plus three independently produced evidence artifacts -- deterministic
quality findings, factual review, visitor review, rubric outcome -- and resolves each applicable
dimension to a real verdict. It never calls an LLM, never reaches Aspose.org, and never grants
publication or lifecycle authority; the 30-point rubric remains the sole acceptance authority.
"""

from __future__ import annotations

from pathlib import Path

from readme_agent.presentation.candidate_benchmark_acceptance_contracts import (
    AcceptanceStatus,
    BenchmarkDimensionAcceptanceV1,
    CandidateBenchmarkAcceptanceV1,
    CandidateRubricEvidenceV1,
    DimensionVerdict,
    canonical_benchmark_acceptance_payload_hash,
)
from readme_agent.presentation.candidate_benchmark_acceptance_evaluation import (
    benchmark_dimension_results,
    benchmark_preconditions,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    CandidateBenchmarkComparisonV1,
)
from readme_agent.specialists.readme_review_roles import RoleReviewRecordV1
from readme_agent.validation.public_quality_contracts import PublicQualityReportV1


def evaluate_candidate_benchmark_acceptance(
    *,
    candidate_markdown: str,
    candidate_sha256: str,
    facts_hash: str,
    comparison: CandidateBenchmarkComparisonV1,
    deterministic_evidence: PublicQualityReportV1,
    factual_review_evidence: RoleReviewRecordV1,
    visitor_review_evidence: RoleReviewRecordV1,
    rubric_evidence: CandidateRubricEvidenceV1,
    reference_excerpts: tuple[str, ...] = (),
    predecessor_acceptance_sha256: str | None = None,
    predecessor_acceptance: CandidateBenchmarkAcceptanceV1 | None = None,
    profile_path: Path | None = None,
) -> CandidateBenchmarkAcceptanceV1:
    """Resolve real PASS/FAIL/UNKNOWN/QUARANTINED/NOT_APPLICABLE verdicts for a candidate already
    evidence-mapped by `build_candidate_benchmark_comparison`, from already-collected, independently
    produced evidence. Pure function of its typed inputs plus the current on-disk frozen benchmark
    profile (read once, solely to detect drift against `comparison`'s own recorded hash) -- no LLM
    call, no network access, no mutation of any input.
    """

    hard_disqualifiers, fresh_profile_sha256 = benchmark_preconditions(
        candidate_markdown=candidate_markdown,
        candidate_sha256=candidate_sha256,
        comparison=comparison,
        deterministic_evidence=deterministic_evidence,
        factual_review_evidence=factual_review_evidence,
        visitor_review_evidence=visitor_review_evidence,
        rubric_evidence=rubric_evidence,
        reference_excerpts=reference_excerpts,
        predecessor_acceptance_sha256=predecessor_acceptance_sha256,
        predecessor_acceptance_hash=(
            predecessor_acceptance.canonical_hash() if predecessor_acceptance is not None else None
        ),
        profile_path=profile_path,
    )

    seen_dimension_ids: set[str] = set()
    for dim in comparison.dimensions:
        if dim.dimension_id in seen_dimension_ids:
            raise ValueError(f"duplicate dimension_id in comparison: {dim.dimension_id!r}")
        seen_dimension_ids.add(dim.dimension_id)

    dimension_results = benchmark_dimension_results(
        comparison,
        deterministic_evidence,
        blocked=bool(hard_disqualifiers),
    )

    applicable_dimension_ids = tuple(
        sorted(dim.dimension_id for dim in comparison.dimensions if dim.applicable)
    )
    quarantined_dimension_ids = tuple(
        sorted(
            dim.dimension_id
            for dim in comparison.dimensions
            if dim.status == "QUARANTINED_NOT_FACT_AUTHORITY"
        )
    )
    not_applicable_dimension_ids = tuple(
        sorted(dim.dimension_id for dim in comparison.dimensions if dim.status == "NOT_APPLICABLE")
    )
    unresolved_dimension_ids = tuple(
        sorted(result.dimension_id for result in dimension_results if result.verdict == "UNKNOWN")
    )

    failure_reasons: list[str] = list(hard_disqualifiers)
    for result in dimension_results:
        if result.verdict == "FAIL" and result.blocking_finding_ids:
            failure_reasons.append(f"{result.dimension_id}: {result.failure_reason}")

    applicable_id_set = set(applicable_dimension_ids)
    all_applicable_pass = all(
        result.verdict == "PASS"
        for result in dimension_results
        if result.dimension_id in applicable_id_set
    )
    acceptance_status: AcceptanceStatus = (
        "BENCHMARK_ACCEPTANCE_PROVEN"
        if not hard_disqualifiers and all_applicable_pass
        else "BENCHMARK_ACCEPTANCE_NOT_PROVEN"
    )

    comparison_payload = comparison.model_dump(mode="json")
    # Dimension order on `comparison` carries no semantic meaning -- sort before hashing so a
    # comparison built with an equivalent-but-reordered dimensions list yields the same identity.
    comparison_payload["dimensions"] = sorted(
        comparison_payload["dimensions"], key=lambda item: item["dimension_id"]
    )
    comparison_identity_sha256 = canonical_benchmark_acceptance_payload_hash(comparison_payload)
    rubric_evidence_sha256 = rubric_evidence.canonical_hash()
    evidence_bundle_sha256 = canonical_benchmark_acceptance_payload_hash(
        {
            "deterministic_evidence_sha256": deterministic_evidence.report_hash,
            "factual_review_sha256": factual_review_evidence.input_sha256,
            "visitor_review_sha256": visitor_review_evidence.input_sha256,
            "rubric_evidence_sha256": rubric_evidence_sha256,
        }
    )

    return CandidateBenchmarkAcceptanceV1(
        repository=comparison.repository,
        source_revision=comparison.source_revision,
        candidate_sha256=candidate_sha256,
        facts_hash=facts_hash,
        comparison_identity_sha256=comparison_identity_sha256,
        benchmark_profile_sha256=fresh_profile_sha256,
        deterministic_evidence_sha256=deterministic_evidence.report_hash,
        factual_review_sha256=factual_review_evidence.input_sha256,
        visitor_review_sha256=visitor_review_evidence.input_sha256,
        rubric_evidence_sha256=rubric_evidence_sha256,
        evidence_bundle_sha256=evidence_bundle_sha256,
        predecessor_acceptance_sha256=predecessor_acceptance_sha256,
        dimensions=tuple(dimension_results),
        applicable_dimension_ids=applicable_dimension_ids,
        quarantined_dimension_ids=quarantined_dimension_ids,
        not_applicable_dimension_ids=not_applicable_dimension_ids,
        unresolved_dimension_ids=unresolved_dimension_ids,
        hard_disqualifiers=tuple(hard_disqualifiers),
        acceptance_status=acceptance_status,
        failure_reasons=tuple(failure_reasons),
    )


__all__ = [
    "AcceptanceStatus",
    "BenchmarkDimensionAcceptanceV1",
    "CandidateBenchmarkAcceptanceV1",
    "CandidateRubricEvidenceV1",
    "DimensionVerdict",
    "evaluate_candidate_benchmark_acceptance",
]
