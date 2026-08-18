# E5 design: the reasoned-exclusion / correction disposition path (queued, not yet implemented)

The single largest remaining agent-fixable blocker class (S1 residue after the ratchet):
inherited claims — prose the mechanical coverage rule cannot bind AND the accept-only LLM
fallback cannot corroborate, plus inherited **code blocks** (note's `source:claim:4781`,
diagnosed literally: the Quick Start fence). aspose.org closes this class with per-unit
dispositions (`merged_verbatim | merged_reframed | excluded` + mandatory `excluded_reason`
≥15 chars + typed verification), decided by the composing agent and checked deterministically.

## Design principles (bind to existing machinery, no second path)

1. **Reuse the existing expected-disposition vocabulary.** `ExpectedClaimDisposition` already
   has `verified_obligation_replacement`, `verified_omission`, `presentation_policy_correction`
   — the missing piece is PRODUCING resolutions for claims outside today's obligation/
   correction-range coverage, not new enum values.
2. **Code-block claims route to the example machinery, never to text corroboration.** A fenced
   source example is `merged_reframed` when the candidate carries a *verified* example serving
   the same section (obligation `primary_example` → `verified_obligation_replacement`), or
   `excluded` with reason when the source example is unverifiable (fixture-dependent, like
   note's `Document("SimpleTable.one")` — the file is a repo fixture the isolated verifier
   can't assume). The existing `deferred_unverified_source_example_resolution` path is close;
   extend its preconditions to cover fixture-dependent inherited examples whose candidate
   replacement is verified.
3. **The LLM's role stays one bounded verdict per claim** — a new `excluded_with_reason`
   classification in `claim_disposition_check`'s tool schema, corroborated deterministically:
   accepted ONLY when (a) the model's cited replacement quote is found verbatim in the
   candidate (reframed case), or (b) the stated exclusion reason cites a checkable predicate
   (unverifiable-fixture, superseded-by-slot, stale-version-string) that code re-verifies.
   Never accepted on say-so — same shape as today's corroboration layer.
4. **Ratchet coverage**: accepted exclusion/reframe verdicts persist in the same
   claim-disposition ratchet (content-hash keyed) and replay through the same corroboration.
5. **Shared portfolio ratchet** (from the iteration-1 finding): identical claim text recurs
   across repos (page/note share content hash `7ff54c1da64deecb`). Add a portfolio-level
   read-through store keyed purely by claim-content hash; per-repo acceptance still requires
   per-repo re-corroboration, so sharing is safe by construction.
6. **Cells-class inputs get a different lane entirely**: when the source README is already the
   aspose.org-refreshed output (detectable: profile identity with the reference candidate, or
   provenance markers), prefer preservation/minimal-delta composition over recomposition —
   this removes most of the claim population from the disposition problem for those repos.

## Acceptance (per Phase-7 discipline)

- Canary: note-python (code-block claim) + one boilerplate-claim repo (page or words).
- A failing regression test per new path (fixture-dependent example exclusion; reframed
  acceptance; hallucinated exclusion refused).
- Second unchanged run produces zero new provider calls and identical blocking counts.
- No factuality/preservation gate weakened: exclusions must carry checkable reasons; losses
  without them keep blocking.

## Explicitly out of scope

Whole-document rewriting; loosening `_covered_by_fact_variants`; auto-accepting
`verified_against_source` quotes drawn from the source README itself (the circularity noted in
the ledger — close that hole in the same change).
