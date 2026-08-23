# Public interface

Module: `src/readme_agent/presentation/candidate_benchmark_acceptance.py`

## Entry point

```python
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
) -> CandidateBenchmarkAcceptanceV1
```

Pure function. No LLM call, no network access, no filesystem write. The only read is
`load_benchmark_quality_profile()` (imported unmodified from `candidate_benchmark_comparison.py`),
used solely to detect drift between `comparison`'s recorded profile hash and the current on-disk
frozen profile.

## Types imported unmodified (never redefined)

- `readme_agent.presentation.candidate_benchmark_comparison`: `BenchmarkDispositionV1`,
  `CandidateBenchmarkComparisonV1`, `load_benchmark_quality_profile`
- `readme_agent.validation.public_quality_contracts`: `PublicQualityCategory`,
  `PublicQualityReportV1`
- `readme_agent.specialists.readme_review_roles`: `RoleReviewRecordV1`
- `readme_agent.supervisor.portfolio_proof_engine.contracts`: `RubricAcceptanceOutcome`
- `readme_agent.readme.document_hashing`: `sha256_hex`

## Types this module defines

```python
CandidateRubricEvidenceV1(_StrictModel):
    candidate_sha256: str            # 64-hex, fences against the recomputed candidate hash
    outcome: RubricAcceptanceOutcome # the existing type -- not redefined
    def canonical_hash(self) -> str

BenchmarkDimensionAcceptanceV1(_StrictModel):
    dimension_id: str
    benchmark_disposition: BenchmarkDispositionV1
    obligation: str
    verdict: Literal["PASS", "FAIL", "NOT_APPLICABLE", "QUARANTINED", "UNKNOWN"]
    evidence_categories_considered: tuple[PublicQualityCategory, ...]
    blocking_finding_ids: tuple[str, ...]
    failure_reason: str | None

CandidateBenchmarkAcceptanceV1(_StrictModel):
    schema_version: Literal[1]
    acceptance_contract_version: Literal[1]
    repository: str
    source_revision: str
    candidate_sha256: str
    facts_hash: str
    comparison_identity_sha256: str        # canonical hash of `comparison`, dimension-order-insensitive
    benchmark_profile_sha256: str          # freshly recomputed, not merely copied from `comparison`
    deterministic_evidence_sha256: str     # == deterministic_evidence.report_hash
    factual_review_sha256: str             # == factual_review_evidence.input_sha256
    visitor_review_sha256: str             # == visitor_review_evidence.input_sha256
    rubric_evidence_sha256: str            # == rubric_evidence.canonical_hash()
    evidence_bundle_sha256: str            # combined hash of the four evidence identities above
    predecessor_acceptance_sha256: str | None
    dimensions: tuple[BenchmarkDimensionAcceptanceV1, ...]   # sorted by dimension_id
    applicable_dimension_ids: tuple[str, ...]
    quarantined_dimension_ids: tuple[str, ...]
    not_applicable_dimension_ids: tuple[str, ...]
    unresolved_dimension_ids: tuple[str, ...]   # UNKNOWN dimensions only
    hard_disqualifiers: tuple[str, ...]
    acceptance_status: Literal["BENCHMARK_ACCEPTANCE_PROVEN", "BENCHMARK_ACCEPTANCE_NOT_PROVEN"]
    failure_reasons: tuple[str, ...]
    publishes_acceptance: Literal[False]
    transitions_lifecycle_state: Literal[False]
    replaces_rubric_30_of_30: Literal[False]
    def canonical_hash(self) -> str
```

## Overall pass condition

`acceptance_status == "BENCHMARK_ACCEPTANCE_PROVEN"` iff: the candidate hash and every evidence
source's own hash fence match; the current profile hash matches `comparison`'s recorded hash;
`hard_disqualifiers` is empty; and every applicable dimension's verdict is `PASS` (no `UNKNOWN`,
no `FAIL`).
