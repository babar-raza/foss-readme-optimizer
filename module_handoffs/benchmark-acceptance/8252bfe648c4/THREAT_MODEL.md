# Threat model

## In scope

This module is a pure, offline, in-memory function over typed inputs plus one local frozen-JSON
read. The threats worth naming are integrity/binding threats (can a caller fool it into granting
credit it shouldn't) and determinism threats (can two runs of the same candidate disagree), not
classic network/injection surface (there is none).

## Candidate/evidence substitution

**Threat**: a caller (accidentally or adversarially) supplies evidence produced for a *different*
candidate, hoping stale-but-passing evidence carries over.

**Mitigation**: every evidence source (`comparison`, `deterministic_evidence`,
`factual_review_evidence`, `visitor_review_evidence`, `rubric_evidence`) is fenced against the
freshly recomputed `candidate_sha256` before any dimension is resolved. A mismatch on any one source
forces every applicable dimension to `UNKNOWN` and the overall result to
`BENCHMARK_ACCEPTANCE_NOT_PROVEN` -- never a silent partial-trust fallback. Covered by
`test_candidate_hash_mismatch_fails`, `test_missing_evidence_fails_closed`,
`test_factual_review_from_another_candidate_fails`,
`test_visitor_review_from_another_candidate_fails`,
`test_rubric_evidence_from_another_candidate_fails`.

## Stale benchmark profile

**Threat**: `comparison` was built against an older frozen profile than the one currently on disk
(e.g. after a profile refresh), and a caller tries to reuse it.

**Mitigation**: `load_benchmark_quality_profile()` is called fresh on every invocation and its hash
is fenced against `comparison.benchmark_profile_sha256`. Covered by
`test_comparison_profile_mismatch_fails`, `test_missing_dimension_fails_via_profile_fence`,
`test_changing_comparison_invalidates_previous_result`.

## Role confusion between factual and visitor review

**Threat**: a caller accidentally (or an adversarial evidence producer deliberately) passes the
factual reviewer's record into the `visitor_review_evidence` parameter or vice versa, hoping a
permissive record from one role satisfies the other's requirement.

**Mitigation**: `identity.role` is checked explicitly against the expected role string for each
parameter; a mismatch is a hard disqualifier. Covered by `test_role_swap_is_rejected`.

## Benchmark content used as product-fact authority

**Threat**: benchmark prose, an upstream Aspose.org verdict, or this module's own `obligation` text
is treated as evidence that a candidate's claims are true.

**Mitigation**: `quarantined` dimensions (`benchmark_claim_authority`, `benchmark_item_verdicts`) are
hardcoded to verdict `QUARANTINED` regardless of any evidence supplied for them -- there is no code
path through which evidence could grant them `PASS`. `obligation` text is carried through to every
result purely for auditability and is never itself evaluated as a truth claim. Covered by
`test_quarantined_dimension_never_passes_regardless_of_evidence`,
`test_obligation_text_alone_cannot_grant_a_pass`.

## Prose-copying used to fabricate compliance

**Threat**: a candidate copies benchmark or reference prose verbatim (or near-verbatim), hoping
surface similarity to a "good" example substitutes for genuine, candidate-specific evidence.

**Mitigation**: no code path anywhere in this module grants credit for textual similarity -- only
the *typed evidence* inputs can produce a `PASS`. A dedicated dual-signal guard (`_suspicious_overlap`)
can additionally *disqualify* (never grant) on suspicious overlap against caller-supplied,
test/audit-only `reference_excerpts`; production callers should never populate this with real
Aspose.org content (nothing in this module fetches it). Covered by
`test_suspicious_copied_prose_disqualifies_but_never_grants_credit`,
`test_unrelated_reference_excerpt_does_not_disqualify`.

## Malformed/adversarial dimension data

**Threat**: a `comparison` object carries duplicate dimension IDs, or a dimension status this
module's dispatch logic does not recognize.

**Mitigation**: duplicate `dimension_id` values raise `ValueError` before any dimension is resolved
(defense-in-depth beyond `CandidateBenchmarkComparisonV1`'s own construction-time uniqueness
validator). An unrecognized `status` value (unreachable through normal validated construction today,
since the type is a closed `Literal`) falls to `UNKNOWN` with an explicit reason rather than being
silently skipped or defaulted to `PASS`. Covered by `test_duplicate_dimension_id_fails_closed`,
`test_unrecognized_dimension_status_fails_closed_and_blocks_overall_acceptance`.

## Silent verdict drift across reruns

**Threat**: the same candidate is evaluated twice and receives a different verdict with no visible
signal of *why* -- undermining trust that "PROVEN" means anything stable.

**Mitigation**: `evidence_bundle_sha256` binds a canonical hash of all four evidence identities into
the result, so two results for the same `candidate_sha256` are mechanically diffable; the optional
`predecessor_acceptance_sha256` chain link extends this into an audit trail once a caller starts
populating it. This does not eliminate the root cause (see `INTEGRATION.md`'s Decision #105 note) --
it makes it observable. Covered by `test_evidence_drift_is_visible_not_hidden`.

## No path injection / no code execution

Every string field in every input model is used exclusively for comparison, hashing, or pass-through
into the output -- never as a filesystem path component, format string for `eval`/`exec`, or shell
argument. The module performs exactly one filesystem read (`load_benchmark_quality_profile()`'s
fixed, repo-relative default path, or an explicit `profile_path` the *caller* controls, not
candidate-derived). Verified by `test_no_live_or_network_call_in_module_source` (static import scan)
and by inspection: no `open()`/`Path()` construction anywhere in this module's own source keys off
`candidate_markdown` or any evidence field.

## Secrets

No field in this module's models is redacted, because none is expected to carry secret-like content
in normal use (candidate markdown, review reasoning text, hashes, dimension IDs). Unlike
`evidence/writer.py`'s durable-artifact-writing path, this module never persists anything to disk,
so the redact-before-write convention does not apply here. If a future caller feeds genuinely
sensitive text through `reference_excerpts` or review `reasoning` fields, that risk is inherited from
the caller, not introduced by this module.
