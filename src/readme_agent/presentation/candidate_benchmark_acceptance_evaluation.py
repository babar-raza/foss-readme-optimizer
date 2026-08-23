"""Evaluate benchmark-acceptance preconditions and per-dimension evidence."""

from __future__ import annotations

from pathlib import Path

from readme_agent.presentation.candidate_benchmark_acceptance_contracts import (
    BenchmarkDimensionAcceptanceV1,
    CandidateRubricEvidenceV1,
)
from readme_agent.presentation.candidate_benchmark_acceptance_policy import (
    REQUIRED_DETERMINISTIC_CHECK_IDS,
    quality_categories_for_dimension,
    suspicious_benchmark_overlap,
)
from readme_agent.presentation.candidate_benchmark_comparison import (
    CandidateBenchmarkComparisonV1,
    load_benchmark_quality_profile,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.readme_review_roles import RoleReviewRecordV1
from readme_agent.validation.public_quality_contracts import PublicQualityReportV1


def benchmark_preconditions(
    *,
    candidate_markdown: str,
    candidate_sha256: str,
    comparison: CandidateBenchmarkComparisonV1,
    deterministic_evidence: PublicQualityReportV1,
    factual_review_evidence: RoleReviewRecordV1,
    visitor_review_evidence: RoleReviewRecordV1,
    rubric_evidence: CandidateRubricEvidenceV1,
    reference_excerpts: tuple[str, ...],
    predecessor_acceptance_sha256: str | None,
    predecessor_acceptance_hash: str | None,
    profile_path: Path | None,
) -> tuple[list[str], str]:
    """Return hard disqualifiers and the current frozen-profile identity."""

    failures: list[str] = []
    missing_checks = sorted(
        REQUIRED_DETERMINISTIC_CHECK_IDS - set(deterministic_evidence.checks_run)
    )
    if missing_checks:
        failures.append(
            "required deterministic benchmark checks did not run: " + ", ".join(missing_checks)
        )
    if predecessor_acceptance_sha256 is not None:
        if predecessor_acceptance_hash is None:
            failures.append(
                "predecessor_acceptance_sha256 was supplied without the predecessor record"
            )
        elif predecessor_acceptance_hash != predecessor_acceptance_sha256:
            failures.append(
                "predecessor_acceptance_sha256 does not match the supplied predecessor record"
            )
    elif predecessor_acceptance_hash is not None:
        failures.append("a predecessor acceptance record was supplied without its expected hash")
    if sha256_hex(candidate_markdown) != candidate_sha256:
        failures.append(
            "candidate_sha256 does not match sha256 of the supplied candidate_markdown bytes"
        )
    bindings = (
        (comparison.candidate_sha256, "comparison"),
        (deterministic_evidence.candidate_sha256, "deterministic_evidence"),
        (factual_review_evidence.candidate_sha256, "factual_review_evidence"),
        (visitor_review_evidence.candidate_sha256, "visitor_review_evidence"),
        (rubric_evidence.candidate_sha256, "rubric_evidence"),
    )
    for observed, label in bindings:
        if observed != candidate_sha256:
            failures.append(f"{label}.candidate_sha256 is not bound to this candidate")
    if factual_review_evidence.identity.role != "factual_plan_reviewer":
        failures.append(
            "factual_review_evidence was not produced by the factual_plan_reviewer role"
        )
    if visitor_review_evidence.identity.role != "blind_quality_reviewer":
        failures.append(
            "visitor_review_evidence was not produced by the blind_quality_reviewer role"
        )
    current_profile_hash = (
        load_benchmark_quality_profile(profile_path)[1]
        if profile_path is not None
        else load_benchmark_quality_profile()[1]
    )
    if current_profile_hash != comparison.benchmark_profile_sha256:
        failures.append(
            "comparison.benchmark_profile_sha256 does not match the current on-disk frozen "
            "benchmark profile -- comparison was built against a since-changed profile"
        )
    if factual_review_evidence.verdict != "ACCEPT":
        failures.append(
            f"factual_review_evidence verdict is {factual_review_evidence.verdict!r}, not ACCEPT"
        )
    if visitor_review_evidence.verdict != "ACCEPT":
        failures.append(
            f"visitor_review_evidence verdict is {visitor_review_evidence.verdict!r}, not ACCEPT"
        )
    if rubric_evidence.outcome.hard_disqualifier_count > 0:
        failures.append(
            f"rubric_evidence carries {rubric_evidence.outcome.hard_disqualifier_count} "
            "hard disqualifier(s)"
        )
    if rubric_evidence.outcome.accepted and rubric_evidence.outcome.hard_disqualifier_count > 0:
        failures.append(
            "rubric_evidence is internally inconsistent: accepted=True with a nonzero "
            "hard_disqualifier_count"
        )
    failures.extend(suspicious_benchmark_overlap(candidate_markdown, reference_excerpts))
    return failures, current_profile_hash


def benchmark_dimension_results(
    comparison: CandidateBenchmarkComparisonV1,
    deterministic_evidence: PublicQualityReportV1,
    *,
    blocked: bool,
) -> list[BenchmarkDimensionAcceptanceV1]:
    """Resolve every benchmark dimension through deterministic evidence categories."""

    results: list[BenchmarkDimensionAcceptanceV1] = []
    for dimension in sorted(comparison.dimensions, key=lambda item: item.dimension_id):
        if dimension.status == "NOT_APPLICABLE":
            results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dimension.dimension_id,
                    benchmark_disposition=dimension.benchmark_disposition,
                    obligation=dimension.obligation,
                    verdict="NOT_APPLICABLE",
                    evidence_paths_considered=tuple(dimension.evidence_paths),
                )
            )
            continue
        if dimension.status == "QUARANTINED_NOT_FACT_AUTHORITY":
            results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dimension.dimension_id,
                    benchmark_disposition=dimension.benchmark_disposition,
                    obligation=dimension.obligation,
                    verdict="QUARANTINED",
                    evidence_paths_considered=tuple(dimension.evidence_paths),
                )
            )
            continue
        if dimension.status != "EVIDENCE_BOUND_PENDING_ACCEPTANCE":
            results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dimension.dimension_id,
                    benchmark_disposition=dimension.benchmark_disposition,
                    obligation=dimension.obligation,
                    verdict="UNKNOWN",
                    evidence_paths_considered=tuple(dimension.evidence_paths),
                    failure_reason=f"unrecognized comparison dimension status {dimension.status!r}",
                )
            )
            continue
        categories = quality_categories_for_dimension(dimension.dimension_id)
        if blocked:
            results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dimension.dimension_id,
                    benchmark_disposition=dimension.benchmark_disposition,
                    obligation=dimension.obligation,
                    verdict="UNKNOWN",
                    evidence_paths_considered=tuple(dimension.evidence_paths),
                    evidence_categories_considered=tuple(sorted(categories)),
                    failure_reason="blocked by hard disqualifier(s); see hard_disqualifiers",
                )
            )
            continue
        blocking_ids = tuple(
            sorted(
                finding.finding_id
                for finding in deterministic_evidence.findings
                if finding.blocking and finding.category in categories
            )
        )
        results.append(
            BenchmarkDimensionAcceptanceV1(
                dimension_id=dimension.dimension_id,
                benchmark_disposition=dimension.benchmark_disposition,
                obligation=dimension.obligation,
                verdict="FAIL" if blocking_ids else "PASS",
                evidence_paths_considered=tuple(dimension.evidence_paths),
                evidence_categories_considered=tuple(sorted(categories)),
                blocking_finding_ids=blocking_ids,
                failure_reason=(
                    "blocking deterministic quality finding(s) in a relevant category: "
                    + ", ".join(blocking_ids)
                    if blocking_ids
                    else None
                ),
            )
        )
    return results


__all__ = ["benchmark_dimension_results", "benchmark_preconditions"]
