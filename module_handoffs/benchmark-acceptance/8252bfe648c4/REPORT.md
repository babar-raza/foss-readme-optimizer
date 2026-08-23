# OPT-STANDALONE-BENCHMARK-COMPARATOR: benchmark-acceptance evaluator

## Summary

`candidate_benchmark_comparison.py` (already on `main` at the base SHA for this lane) proves that
evidence *files exist* per frozen-benchmark dimension for a candidate -- it never judges their
*content*. This lane adds the next layer: `candidate_benchmark_acceptance.py`, a standalone, pure,
deterministic evaluator that consumes that comparison plus three independently produced evidence
artifacts (deterministic quality findings, factual review, visitor review, rubric outcome) and
resolves each applicable dimension to a real `PASS`/`FAIL`/`UNKNOWN`/`QUARANTINED`/`NOT_APPLICABLE`
verdict.

No existing model, loader, rubric, or review contract was duplicated. Only two new types were
introduced: `CandidateRubricEvidenceV1` (a thin candidate-hash-bound wrapper around the existing
`RubricAcceptanceOutcome`, which has no candidate-hash field of its own) and the acceptance result
pair this module exists to produce (`BenchmarkDimensionAcceptanceV1`/`CandidateBenchmarkAcceptanceV1`).

## Base SHA and branch

- Base SHA: `8252bfe648c4bf79fd7b736069f7fd503fb5b74e`
- Branch: `claude/standalone-benchmark-acceptance-8252bfe648c4`
- Current `origin/main` SHA at handoff time: `8252bfe648c4bf79fd7b736069f7fd503fb5b74e` (no drift)

## Commits

1. `267e6e39dd1f112cc0ff49e1177bee708ea65487` -- contracts/models, stubbed entry point, full test
   file (26 of 28 tests red by design against the stub).
2. `6a61663fe7bdbf0cfa2c8fdc5d7cd5e51fa0f947` -- full implementation; all 28 tests green.
3. (this commit) -- handoff documentation only.

## What was verified

- `pytest tests/unit/test_candidate_benchmark_acceptance.py -q` -- 28 passed.
- `ruff check` / `ruff format --check` -- clean on both files.
- `mypy` -- clean on the module.
- `git diff --check` -- clean (no whitespace errors).
- Narrowest relevant existing regression tests (`test_aspose_benchmark_profile.py`,
  `test_candidate_benchmark_comparison.py`, `test_readme_review_roles.py`,
  `test_public_candidate_quality*.py`, `test_portfolio_proof_engine_contracts.py`) -- 61 passed,
  0 failed, 0 touched.
- No full-suite run was performed, per instruction (another lane may hold the test lease).

## Design highlights worth the integration owner's attention

- Candidate-binding is a fence applied to every one of five evidence sources
  (`comparison`, `deterministic_evidence`, `factual_review_evidence`, `visitor_review_evidence`,
  `rubric_evidence`) plus the frozen benchmark profile itself, mirroring
  `supervisor/portfolio_scheduler/reducer.py`'s own fence pattern.
- Global hard disqualifiers (non-`ACCEPT` review verdicts, rubric hard disqualifiers, role
  mismatches, internally-inconsistent rubric evidence, suspicious benchmark-prose overlap) apply
  uniformly to every applicable dimension, mirroring `rubric_criteria.py`'s own global (not
  per-criterion) disqualifier shape.
- A documented, category-level (never content/keyword-level) map
  (`_DIMENSION_QUALITY_CATEGORIES`) ties each applicable dimension to the `PublicQualityCategory`
  values a blocking deterministic finding can disqualify it for.
- `evidence_bundle_sha256` plus an optional `predecessor_acceptance_sha256` chain link make verdict
  drift between reruns of the same candidate mechanically diffable rather than silent -- see
  `THREAT_MODEL.md` and `INTEGRATION.md` for the Decision #105 context this responds to.
- Three explicit `Literal[False]` fields (`publishes_acceptance`, `transitions_lifecycle_state`,
  `replaces_rubric_30_of_30`) make "this is not a publication verdict" a type-enforced guarantee,
  mirroring `CandidateBenchmarkComparisonV1`'s own self-disclaiming fields.

See `INTERFACE.md`, `INTEGRATION.md`, `KNOWN_LIMITATIONS.md`, `DIMENSION_EVIDENCE_MATRIX.md`, and
`THREAT_MODEL.md` for full detail.
