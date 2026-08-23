# Integration notes for the owning agent

This lane implements the module only. It does not integrate it. No `__init__.py` was touched, no
capability/CLI registration was added, no rubric criterion was wired to consume this module's
output. All of the following is Codex's decision, not pre-empted here.

## Exact public entry point

`evaluate_candidate_benchmark_acceptance` in
`src/readme_agent/presentation/candidate_benchmark_acceptance.py` -- see `INTERFACE.md` for the
full signature and result contract.

## Required caller-supplied inputs and where they could plausibly come from

- `candidate_markdown` / `candidate_sha256`: the candidate README text and its byte hash -- same
  identity already threaded through `manifest.json`/`ReadmePocLifecycleStateV2.candidate_hash`
  elsewhere in the pipeline.
- `facts_hash`: this module treats it as an opaque, caller-attested identifier (it never receives a
  `ProductFactsV2` object to recompute it against) -- pass through whatever `facts_hash` the
  candidate was generated against.
- `comparison`: the output of `candidate_benchmark_comparison.build_candidate_benchmark_comparison()`
  for this exact candidate -- already produced somewhere in the PF-02/PF-03 pipeline if the frozen
  benchmark is being consulted at all.
- `deterministic_evidence`: the output of
  `readme_agent.validation.public_quality_registry.evaluate_public_candidate_quality(candidate_text,
  facts=..., claim_accountability=...)` -- this module does not call it itself, so the caller must
  run it and pass the resulting `PublicQualityReportV1` through.
- `factual_review_evidence` / `visitor_review_evidence`: the `RoleReviewRecordV1` persisted for this
  candidate by whatever already produces `review/factual-plan-review.json` /
  `review/blind-quality-review.json` in the local-POC compatibility bundle (see
  `supervisor/local_poc_review_evidence.py`, `specialists/readme_review_roles.py`).
- `rubric_evidence`: wrap the existing `RubricAcceptanceOutcome` (produced by
  `supervisor.portfolio_proof_engine.rubric.score_candidate`/`evaluate_repository`) in
  `CandidateRubricEvidenceV1(candidate_sha256=..., outcome=...)`.

## Where this should eventually run

Downstream of `DETERMINISTIC_VALIDATED` and after both `FACTUAL_REVIEWED` and `VISITOR_REVIEWED`
have real artifacts (see `ProofStageV1` in `portfolio_proof_engine/contracts.py`) -- i.e. the same
point in the pipeline where `rubric.score_candidate()` already runs, since this module needs the
same evidence rubric scoring needs plus the benchmark `comparison`.

## How it complements the rubric

`CandidateBenchmarkAcceptanceV1` is designed to become one more piece of evidence a rubric criterion
could reference, the same way `rubric_criteria.py`'s existing rows reference
`evidence_artifact`/`evidence_key` pairs against `EvidenceBundleV1`. A natural (not implemented here)
extension: add an optional `benchmark_acceptance: dict | None = None` field to `EvidenceBundleV1`
(`supervisor/portfolio_proof_engine/evidence_bundle.py`) and a new criterion/evaluator type in
`rubric_criteria.py` that reads `benchmark_acceptance["acceptance_status"]`. This lane does not make
that change -- it is explicitly the integration owner's call, including whether the 30-point rubric
should gain a 31st criterion or stay at exactly 30 with this as advisory-only context.

## Why it holds no fact or publication authority

- It never reads Aspose.org at runtime and never treats benchmark prose/verdicts as evidence of
  anything about the candidate (`quarantined` dimensions are hardcoded to verdict `QUARANTINED`
  regardless of any evidence supplied for them).
- `publishes_acceptance`, `transitions_lifecycle_state`, `replaces_rubric_30_of_30` are all
  type-enforced `Literal[False]`.
- `acceptance_status` uses `BENCHMARK_ACCEPTANCE_PROVEN`/`BENCHMARK_ACCEPTANCE_NOT_PROVEN`
  vocabulary, deliberately disjoint from the rubric's own `ACCEPTED`/`AGENT_ACCEPTED_30_OF_30`
  vocabulary, so the two outcomes can never be confused or substituted for one another downstream.

## Rerun-consistency note (Decision #105) -- read before wiring evidence generation

`plans/decisions/catalog.jsonl` decision 105, grounded in the live 2026-08-18 probe
(`plans/investigations/evidence/llm-probe/qwen-output-limits-20260818.json`): on this gateway,
qwen3-next forced-tool-call argument payloads are nondeterministic at temperature 0 (5/5 distinct
trials) even though freeform prose is byte-stable (5/5 identical). `factual_review_evidence`/
`visitor_review_evidence` (`RoleReviewRecordV1`) are exactly the artifact class already proven
unstable under this mechanism -- a previously observed symptom (claim-accountability counts
fluctuating `2 -> 1 -> 2` across reruns) was traced to this exact cause. The team's proven fix was
**ratchet, never re-roll**: persist a corroborated verdict content-addressed by its input
fingerprint and replay it (see `supervisor/blocked_decision_cache.py`,
`retry_policy.py::evaluate_retry`, and the `claim-disposition-ratchet.json` precedent).

This module cannot enforce that upstream -- it has no visibility into how
`factual_review_evidence`/`visitor_review_evidence` were produced. **Strong recommendation**:
whoever wires evidence generation for this module's caller should apply the same ratchet doctrine
to review-record generation, rather than re-asking the reviewer role on every rerun of the same
candidate. This module's contribution is limited to making the resulting drift *observable*
(`evidence_bundle_sha256`, optional `predecessor_acceptance_sha256` chain) rather than *silent* --
see `KNOWN_LIMITATIONS.md` for the precise, honest boundary of that claim.

## Potential conflicts with commits landed after this lane's base SHA

None known as of this handoff -- `origin/main` had not advanced past `8252bfe648c4bf79fd7b736069f7fd503fb5b74e`
when this lane finished (see `BASE_AND_DRIFT.json`). If it has advanced by the time this branch is
reviewed, re-check whether `candidate_benchmark_comparison.py`'s `CandidateBenchmarkComparisonV1`/
`CandidateBenchmarkDimensionV1` shapes, `data/aspose_benchmark_quality_profile.json`'s dimension set,
or `public_quality_contracts.py`'s `PublicQualityCategory` values changed -- this module's
`_DIMENSION_QUALITY_CATEGORIES` table and field reuse assume the shapes read and verified at this
base SHA.
