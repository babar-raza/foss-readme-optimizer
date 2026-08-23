"""Resolve real per-dimension benchmark-acceptance verdicts from already-collected evidence.

Distinct from `candidate_benchmark_comparison.py`: that module proves evidence *files exist* per
dimension (`status="EVIDENCE_BOUND_PENDING_ACCEPTANCE"`) without judging content.  This module
consumes that comparison plus three independently produced evidence artifacts -- deterministic
quality findings, factual review, visitor review, rubric outcome -- and resolves each applicable
dimension to a real verdict. It never calls an LLM, never reaches Aspose.org, and never grants
publication or lifecycle authority; the 30-point rubric remains the sole acceptance authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.presentation.candidate_benchmark_comparison import (
    BenchmarkDispositionV1,
    CandidateBenchmarkComparisonV1,
    load_benchmark_quality_profile,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.readme_review_roles import RoleReviewRecordV1
from readme_agent.supervisor.portfolio_proof_engine.contracts import RubricAcceptanceOutcome
from readme_agent.validation.public_quality_contracts import (
    PublicQualityCategory,
    PublicQualityReportV1,
)

DimensionVerdict = Literal["PASS", "FAIL", "NOT_APPLICABLE", "QUARANTINED", "UNKNOWN"]
AcceptanceStatus = Literal["BENCHMARK_ACCEPTANCE_PROVEN", "BENCHMARK_ACCEPTANCE_NOT_PROVEN"]

_SHA256_PATTERN = r"^[0-9a-f]{64}$"

# Category-level (never content/keyword-level) map from each applicable benchmark dimension to the
# PublicQualityCategory values a blocking deterministic finding can disqualify it for. A documented
# judgment call -- same precedent as candidate_benchmark_comparison.py's own _DIMENSION_EVIDENCE
# table. A dimension missing from this table (only possible if a future profile adds one without a
# matching update here) falls back to an empty set: still subject to the global gates below, just
# without category-level differentiation until this table is extended.
_DIMENSION_QUALITY_CATEGORIES: dict[str, frozenset[PublicQualityCategory]] = {
    "information_coverage": frozenset({"claim_grounding", "cross_section_contradiction"}),
    "product_specificity": frozenset({"claim_grounding", "cross_section_contradiction"}),
    "structure_and_navigation": frozenset({"structural_quality", "malformed_prose"}),
    "branding_and_visuals": frozenset({"structural_quality"}),
    "capability_depth": frozenset(
        {"claim_grounding", "cross_section_contradiction", "structural_quality"}
    ),
    "installation_and_dependencies": frozenset({"claim_grounding", "malformed_prose"}),
    "source_derived_examples": frozenset({"claim_grounding", "malformed_prose"}),
    "api_reference_depth": frozenset({"structural_quality", "malformed_prose"}),
    "documentation_and_resources": frozenset({"malformed_prose", "structural_quality"}),
    "limitations": frozenset({"malformed_prose", "claim_grounding"}),
    "development_and_testing": frozenset({"process_leakage", "malformed_prose"}),
    "licensing": frozenset({"claim_grounding"}),
    "inherited_content_accountability": frozenset(
        {"malformed_prose", "cross_section_contradiction"}
    ),
    "public_tone_and_process_hygiene": frozenset({"process_leakage"}),
}

# Dual-signal thresholds for the optional, test/audit-only copy guard: both must be crossed before
# a disqualifier fires, trading a small false-negative risk for resistance to single-metric
# boundary flakiness (a small wording edit near one threshold should not flip the verdict alone).
_SIMILARITY_SEQUENCE_THRESHOLD = 0.75
_SIMILARITY_JACCARD_THRESHOLD = 0.6

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CandidateRubricEvidenceV1(_StrictModel):
    """Bind an otherwise-unbound rubric outcome to the exact candidate it was scored against."""

    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    outcome: RubricAcceptanceOutcome

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class BenchmarkDimensionAcceptanceV1(_StrictModel):
    dimension_id: str = Field(min_length=1)
    benchmark_disposition: BenchmarkDispositionV1
    obligation: str = Field(min_length=1)
    verdict: DimensionVerdict
    evidence_categories_considered: tuple[PublicQualityCategory, ...] = ()
    blocking_finding_ids: tuple[str, ...] = ()
    failure_reason: str | None = None


class CandidateBenchmarkAcceptanceV1(_StrictModel):
    """Per-dimension benchmark-acceptance evidence for one candidate.

    Never a publication or lifecycle verdict -- see `publishes_acceptance`,
    `transitions_lifecycle_state`, `replaces_rubric_30_of_30` below (all structurally `False`).
    Supporting evidence for the existing 30-point rubric, never a substitute for it.
    """

    schema_version: Literal[1] = 1
    acceptance_contract_version: Literal[1] = 1
    repository: str = Field(pattern=r"^[^/]+/[^/]+$")
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    facts_hash: str = Field(min_length=1)
    comparison_identity_sha256: str = Field(pattern=_SHA256_PATTERN)
    benchmark_profile_sha256: str = Field(pattern=_SHA256_PATTERN)
    deterministic_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    factual_review_sha256: str = Field(pattern=_SHA256_PATTERN)
    visitor_review_sha256: str = Field(pattern=_SHA256_PATTERN)
    rubric_evidence_sha256: str = Field(pattern=_SHA256_PATTERN)
    evidence_bundle_sha256: str = Field(pattern=_SHA256_PATTERN)
    predecessor_acceptance_sha256: str | None = None
    dimensions: tuple[BenchmarkDimensionAcceptanceV1, ...] = Field(min_length=1)
    applicable_dimension_ids: tuple[str, ...]
    quarantined_dimension_ids: tuple[str, ...]
    not_applicable_dimension_ids: tuple[str, ...]
    unresolved_dimension_ids: tuple[str, ...]
    hard_disqualifiers: tuple[str, ...] = ()
    acceptance_status: AcceptanceStatus
    failure_reasons: tuple[str, ...] = ()
    publishes_acceptance: Literal[False] = False
    transitions_lifecycle_state: Literal[False] = False
    replaces_rubric_30_of_30: Literal[False] = False

    @model_validator(mode="after")
    def _dimensions_are_unique(self) -> CandidateBenchmarkAcceptanceV1:
        ids = [item.dimension_id for item in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate benchmark acceptance dimensions must be unique")
        return self

    def canonical_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def _normalized_words(text: str) -> set[str]:
    return set(_WORD_PATTERN.findall(text.casefold()))


def _suspicious_overlap(
    candidate_markdown: str, reference_excerpts: tuple[str, ...]
) -> tuple[str, ...]:
    """Test/audit-only copy guard. Absence of excerpts is a no-op; presence can only disqualify,
    never grant credit. Both signals (sequence ratio and word-level Jaccard) must cross their
    threshold together, so a single coincidental metric spike near a boundary cannot alone flip
    the result -- see the threshold-tradeoff note above.
    """

    disqualifiers: list[str] = []
    candidate_words = _normalized_words(candidate_markdown)
    for index, excerpt in enumerate(reference_excerpts):
        sequence_ratio = SequenceMatcher(None, candidate_markdown, excerpt).ratio()
        excerpt_words = _normalized_words(excerpt)
        union = candidate_words | excerpt_words
        jaccard_ratio = len(candidate_words & excerpt_words) / len(union) if union else 0.0
        if (
            sequence_ratio >= _SIMILARITY_SEQUENCE_THRESHOLD
            and jaccard_ratio >= _SIMILARITY_JACCARD_THRESHOLD
        ):
            disqualifiers.append(
                f"suspicious_benchmark_prose_overlap: reference_excerpts[{index}] "
                f"sequence_ratio={sequence_ratio:.2f} jaccard_ratio={jaccard_ratio:.2f}"
            )
    return tuple(disqualifiers)


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
    profile_path: Path | None = None,
) -> CandidateBenchmarkAcceptanceV1:
    """Resolve real PASS/FAIL/UNKNOWN/QUARANTINED/NOT_APPLICABLE verdicts for a candidate already
    evidence-mapped by `build_candidate_benchmark_comparison`, from already-collected, independently
    produced evidence. Pure function of its typed inputs plus the current on-disk frozen benchmark
    profile (read once, solely to detect drift against `comparison`'s own recorded hash) -- no LLM
    call, no network access, no mutation of any input.
    """

    hard_disqualifiers: list[str] = []

    recomputed_candidate_sha256 = sha256_hex(candidate_markdown)
    if recomputed_candidate_sha256 != candidate_sha256:
        hard_disqualifiers.append(
            "candidate_sha256 does not match sha256 of the supplied candidate_markdown bytes"
        )

    if comparison.candidate_sha256 != candidate_sha256:
        hard_disqualifiers.append("comparison.candidate_sha256 is not bound to this candidate")
    if deterministic_evidence.candidate_sha256 != candidate_sha256:
        hard_disqualifiers.append(
            "deterministic_evidence.candidate_sha256 is not bound to this candidate"
        )
    if factual_review_evidence.candidate_sha256 != candidate_sha256:
        hard_disqualifiers.append(
            "factual_review_evidence.candidate_sha256 is not bound to this candidate"
        )
    if visitor_review_evidence.candidate_sha256 != candidate_sha256:
        hard_disqualifiers.append(
            "visitor_review_evidence.candidate_sha256 is not bound to this candidate"
        )
    if rubric_evidence.candidate_sha256 != candidate_sha256:
        hard_disqualifiers.append("rubric_evidence.candidate_sha256 is not bound to this candidate")

    if factual_review_evidence.identity.role != "factual_plan_reviewer":
        hard_disqualifiers.append(
            "factual_review_evidence was not produced by the factual_plan_reviewer role"
        )
    if visitor_review_evidence.identity.role != "blind_quality_reviewer":
        hard_disqualifiers.append(
            "visitor_review_evidence was not produced by the blind_quality_reviewer role"
        )

    fresh_profile_sha256 = (
        load_benchmark_quality_profile(profile_path)[1]
        if profile_path is not None
        else load_benchmark_quality_profile()[1]
    )
    if fresh_profile_sha256 != comparison.benchmark_profile_sha256:
        hard_disqualifiers.append(
            "comparison.benchmark_profile_sha256 does not match the current on-disk frozen "
            "benchmark profile -- comparison was built against a since-changed profile"
        )

    if factual_review_evidence.verdict != "ACCEPT":
        hard_disqualifiers.append(
            f"factual_review_evidence verdict is {factual_review_evidence.verdict!r}, not ACCEPT"
        )
    if visitor_review_evidence.verdict != "ACCEPT":
        hard_disqualifiers.append(
            f"visitor_review_evidence verdict is {visitor_review_evidence.verdict!r}, not ACCEPT"
        )
    if rubric_evidence.outcome.hard_disqualifier_count > 0:
        hard_disqualifiers.append(
            f"rubric_evidence carries {rubric_evidence.outcome.hard_disqualifier_count} "
            "hard disqualifier(s)"
        )
    if rubric_evidence.outcome.accepted and rubric_evidence.outcome.hard_disqualifier_count > 0:
        hard_disqualifiers.append(
            "rubric_evidence is internally inconsistent: accepted=True with a nonzero "
            "hard_disqualifier_count"
        )

    hard_disqualifiers.extend(_suspicious_overlap(candidate_markdown, reference_excerpts))

    seen_dimension_ids: set[str] = set()
    for dim in comparison.dimensions:
        if dim.dimension_id in seen_dimension_ids:
            raise ValueError(f"duplicate dimension_id in comparison: {dim.dimension_id!r}")
        seen_dimension_ids.add(dim.dimension_id)

    blocked = bool(hard_disqualifiers)
    dimension_results: list[BenchmarkDimensionAcceptanceV1] = []
    for dim in sorted(comparison.dimensions, key=lambda item: item.dimension_id):
        if dim.status == "NOT_APPLICABLE":
            dimension_results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dim.dimension_id,
                    benchmark_disposition=dim.benchmark_disposition,
                    obligation=dim.obligation,
                    verdict="NOT_APPLICABLE",
                )
            )
            continue
        if dim.status == "QUARANTINED_NOT_FACT_AUTHORITY":
            dimension_results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dim.dimension_id,
                    benchmark_disposition=dim.benchmark_disposition,
                    obligation=dim.obligation,
                    verdict="QUARANTINED",
                )
            )
            continue
        if dim.status != "EVIDENCE_BOUND_PENDING_ACCEPTANCE":
            # Defense in depth: comparison.dimensions[i].status is a closed Literal today, so this
            # branch is unreachable through normal validated construction. Kept so an unrecognized
            # future status value fails closed instead of silently falling through.
            dimension_results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dim.dimension_id,
                    benchmark_disposition=dim.benchmark_disposition,
                    obligation=dim.obligation,
                    verdict="UNKNOWN",
                    failure_reason=f"unrecognized comparison dimension status {dim.status!r}",
                )
            )
            continue

        relevant_categories = _DIMENSION_QUALITY_CATEGORIES.get(dim.dimension_id, frozenset())
        if blocked:
            dimension_results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dim.dimension_id,
                    benchmark_disposition=dim.benchmark_disposition,
                    obligation=dim.obligation,
                    verdict="UNKNOWN",
                    evidence_categories_considered=tuple(sorted(relevant_categories)),
                    failure_reason="blocked by hard disqualifier(s); see hard_disqualifiers",
                )
            )
            continue

        blocking_findings = tuple(
            sorted(
                finding.finding_id
                for finding in deterministic_evidence.findings
                if finding.blocking and finding.category in relevant_categories
            )
        )
        if blocking_findings:
            dimension_results.append(
                BenchmarkDimensionAcceptanceV1(
                    dimension_id=dim.dimension_id,
                    benchmark_disposition=dim.benchmark_disposition,
                    obligation=dim.obligation,
                    verdict="FAIL",
                    evidence_categories_considered=tuple(sorted(relevant_categories)),
                    blocking_finding_ids=blocking_findings,
                    failure_reason=(
                        "blocking deterministic quality finding(s) in a relevant category: "
                        + ", ".join(blocking_findings)
                    ),
                )
            )
            continue

        dimension_results.append(
            BenchmarkDimensionAcceptanceV1(
                dimension_id=dim.dimension_id,
                benchmark_disposition=dim.benchmark_disposition,
                obligation=dim.obligation,
                verdict="PASS",
                evidence_categories_considered=tuple(sorted(relevant_categories)),
            )
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
    comparison_identity_sha256 = _canonical_hash(comparison_payload)
    rubric_evidence_sha256 = rubric_evidence.canonical_hash()
    evidence_bundle_sha256 = _canonical_hash(
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
