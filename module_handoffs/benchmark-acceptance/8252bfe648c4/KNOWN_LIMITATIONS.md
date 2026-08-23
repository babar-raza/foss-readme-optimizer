# Known limitations

Stated plainly, per instruction, rather than implied to be solved.

## 1. Cannot fix upstream evidence-generation nondeterminism

This module is a pure function; it never calls an LLM and never re-derives a review verdict. That
means it also cannot *prevent* the temperature-0 forced-tool-call nondeterminism documented in
Decision #105 (see `INTEGRATION.md`) from producing different `factual_review_evidence`/
`visitor_review_evidence` on two runs of the same candidate. Its contribution is limited to making
that drift observable (`evidence_bundle_sha256`, optional `predecessor_acceptance_sha256`) -- not to
eliminating the root cause, which lives entirely in code this lane does not own.

## 2. No detection for numeric/list-count inconsistencies

The task brief lists "numeric/list inconsistencies" among the defect classes the evaluator should
catch. No existing check anywhere in this codebase currently detects this class (confirmed against
`public_quality_registry.py`'s full 9-check registry). Building one here would mean duplicating
`public_quality_structure_checks.py`'s job from outside its own module -- explicitly prohibited.
Recommendation: add a dedicated check to `public_quality_structure_checks.py` itself if this defect
class proves material in practice; this module will pick it up automatically once it lands in
`PublicQualityReportV1.findings`, since dimension resolution reads findings generically by category,
not by a hardcoded check-id allowlist.

## 3. The dimension-to-category map is a documented judgment call, not a certainty

`_DIMENSION_QUALITY_CATEGORIES` maps each of the 14 applicable benchmark dimensions to the subset of
the 5 `PublicQualityCategory` values considered relevant to it. This mapping was authored by
reasoning about each dimension's obligation text against each category's stated purpose -- it was
not derived from labeled data or validated against real-world false-positive/false-negative rates.
It follows the same category-level (not content/keyword-level) precedent as
`candidate_benchmark_comparison.py`'s own `_DIMENSION_EVIDENCE` table, but should be revisited once
this module has run against real generated candidates.

## 4. `accepted` and `adapted` dispositions share identical pass/fail mechanics

Both require a candidate-bound, non-conflicting, category-clean PASS to succeed; the disposition
label is the only place they differ in the output. Inventing distinct "adapted-only" leniency rules
would mean guessing at product-specific adaptation semantics, which the task brief explicitly
prohibits ("do not hardcode family/platform behavior"). The `obligation` field is carried through to
every dimension result verbatim so at least the normative text a dimension was judged against is
visible to any downstream consumer that wants to interpret `adapted` differently -- but this module
itself does not.

## 5. The predecessor-hash chain has no enforcement without a store

`predecessor_acceptance_sha256` is threaded through with no lookup performed (this module owns no
persistence layer, and none was requested). It is a schema hook for a future integration to enforce
(e.g. reject an acceptance result whose predecessor hash doesn't match a stored prior result for the
same candidate) -- not a guarantee this module provides by itself today.

## 6. The similarity/copy guard is a coarse, dual-signal heuristic, not exhaustive

`_suspicious_overlap` requires both a `difflib.SequenceMatcher` ratio and a word-level Jaccard ratio
to cross fixed thresholds (`0.75`/`0.6`) before disqualifying. This resists single-metric boundary
flakiness but was validated only with an identical-text positive case and an unrelated-text negative
case -- exhaustive boundary-value pinning across a range of partial-overlap scenarios was not done.
It is also explicitly test/audit-only: no production caller in this codebase populates
`reference_excerpts` with real Aspose.org content, and none should.

## 7. `facts_hash` is not independently verified

This module's signature never receives a `ProductFactsV2` object, so `facts_hash` is bound into the
result as an opaque, caller-attested string and never recomputed/reconciled against a live facts
object. Downstream consumers that need fact-grounding assurance should still go through the existing
`supervisor/product_truth.py`/`readme/document_validation.py` reconciliation paths -- this module's
`facts_hash` field is provenance metadata, not a fact-freshness proof.

## 8. Not validated against a real generated candidate bundle

All 28 tests use hand-built fixtures constructed directly from the real imported types (never
mocked/redeclared), and the 61 narrowest-relevant existing regression tests still pass. This lane
did not run the module against a real, end-to-end generated PF-02/PF-03 evidence bundle (explicitly
out of scope -- "do not run it against production state"). The dimension-to-category map (limitation
3) in particular should be recalibrated against real findings once that becomes possible.
