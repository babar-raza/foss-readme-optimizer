# Pilot rerun: before/after proof

Scope note: this module was never integrated into the real README-generation pipeline (by
charter — see `REPORT.md`). "Pilot rerun" here means running the module's own full check
pipeline (`evaluate_public_candidate_quality`, all 8 registered checks) end-to-end against real,
already-committed candidate READMEs, comparing the current (fixed, pushed) code against a
precisely reconstructed pre-fix snapshot. No LLM calls, no pipeline integration, no writes to
`main`, product repos, or any evidence file.

## Pilot target

Three real committed candidates, chosen because they are the exact ones named in the module's
original task brief and each has documented real defects from the owner audits:

- `plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-3d-foss-for-python/candidate-readme.md`
- `.../aspose-barcode-foss-for-python/candidate-readme.md`
- `.../aspose-note-foss-for-python/candidate-readme.md` (primary pilot — this is where the real
  bugs were found and fixed)

Read read-only from the main checkout; never modified.

## Method

1. **"After"** = the current code at pushed HEAD (`5d46e1bf`).
2. **"Before"** = the current code with the two dry-run fix hunks (`_CONDITIONAL_MARKER` in Tiers
   B/C, `_EXCEPTION_CLAUSE`/`_excepted_discriminators` in Tier C) precisely reverted — reconstructed
   because the buggy intermediate state was never itself committed to git. The revert removed
   exactly 13 lines / added 2 (`git diff --stat` on the swap), matching the size of the two guard
   blocks added during the original fix.
3. Ran `evaluate_public_candidate_quality` (full check pipeline, no facts/claim_accountability
   supplied) against all three candidates under both variants, keeping the module file swap
   entirely inside the isolated lane repo and restoring via `git checkout --` immediately after
   each "before" run — verified clean (`git status --short`) before and after every swap.
4. Compared the two structured `PublicQualityReportV1` outputs by each finding's own unique
   `finding_id` (a content-only fingerprint, not a coarse heuristic key) to get an exact
   removed/added/unchanged finding set.
5. Additionally ran the full committed test suite against the reconstructed "before" code, to
   check whether the existing tests would have caught the regression on their own.

## Results

### Counts, before vs after

| candidate | metric | before | after |
|---|---|---|---|
| 3d-python | cross_section_contradiction | 0 | 0 |
| 3d-python | all other categories/counts | identical | identical |
| barcode-python | cross_section_contradiction | 0 | 0 |
| barcode-python | all other categories/counts | identical | identical |
| **note-python** | **cross_section_contradiction** | **9** | **0** |
| note-python | critical / blocking | 10 / 10 | 1 / 1 |
| note-python | all other categories/counts | identical | identical |

`candidate_sha256` and `checks_run` were identical before/after on all three candidates — the
same 8 checks ran both times; nothing was newly skipped or newly enabled. The change is entirely
in what the (unchanged) check *registry* produced, not in which checks ran.

### Exact finding-level diff (by unique `finding_id`)

- **3d-python**: 0 removed, 0 added, 9 unchanged (byte-identical finding_ids before/after).
- **barcode-python**: 0 removed, 0 added, 4 unchanged.
- **note-python**: **9 removed, 0 added**, 4 unchanged.

The 9 removed findings, summarized by exact claim/limitation text pairs (verified by manual
review, not assumed):

- 8x `contradiction_capability_phrase`: all pairing the negative line *"Saving formats other than
  PDF (HTML/images/ONE) are declared for compatibility but not implemented."* against 8 different
  unrelated PDF-positive lines elsewhere in the document (a code example, a golden-workflow
  description, an installation instruction, a section heading, a third-party-notices sentence).
  Manually verified: **all 8 were false positives** — the negative line's own "other than PDF"
  clause explicitly exempts PDF from the limitation; it was never a real contradiction.
- 1x `contradiction_capability_symbol`: `` `PyMuPDF` `` claimed available in one sentence and
  unavailable in another. Manually verified: **also a false positive** — both sentences are
  conditional test-fallback prose ("if `PyMuPDF` is installed... / if `PyMuPDF` is unavailable but
  `pdftoppm` is available...  "), not competing firm claims.

**Zero of the 9 removed findings were true positives.** No genuine defect was suppressed by the
fix, and 0 new findings were introduced anywhere — the fix did not trade one false-positive class
for another.

### Test-suite gap found and closed

Running the full committed suite (22 tests, before this pilot rerun) against the reconstructed
pre-fix code: **21 of 22 still passed.** The only failure was
`test_checks_source_hash_matches_recorded_version` — a generic source-hash tripwire that flags
"the module's source changed," not "this specific behavior regressed." Neither real bug had a
dedicated behavioral regression test. Closed in commit `5d46e1bf`: two new tests
(`test_exception_clause_exempts_a_named_format_from_a_broader_limitation`,
`test_conditional_dependency_prose_is_not_a_firm_capability_claim`), each verified **red** (fails)
against the reconstructed pre-fix code and **green** (passes) against current HEAD — proper
regression coverage, not just a source-hash bump. Suite is now 24/24 passing at HEAD.

(One authoring bug surfaced while building the first regression test: a triple-quoted fixture
string accidentally line-wrapped "...but not\n  implemented." across two lines, which silently
defeated the negative-cue match entirely on both before/after code, making the test pass
vacuously either way. Caught by checking that the test actually failed against the reconstructed
"before" code before trusting it — fixed by keeping the negative sentence on one logical line via
adjacent string-literal concatenation. Left in this report as a concrete illustration of why
verifying red-before-green matters, not just green-after.)

## Summary

1. **What improved**: the one real defect class this pilot could exercise —
   cross-section contradiction false positives from exception-clause blindness and
   conditional-prose misreading — is fully resolved on the pilot set: 9 → 0 on the candidate that
   had them, 0 → 0 (no change, no regression) on the two that didn't. All 9 removed findings were
   confirmed false positives by manual review of their exact text, not assumed. Regression
   coverage for both specific bugs now exists at the test-suite level (previously absent).
2. **What did not improve**: nothing else changed — `malformed_low_information_prose`,
   `structural_size_outlier`, `structural_detail_density`, and `process_leakage` findings are
   byte-identical (same `finding_id`) before and after on all three candidates. This pilot did not
   exercise `claim_grounding_negative_fact` (none of the three candidates were run with
   `ProductFactsV2` supplied) or `empty_or_placeholder_section` (none fired on these candidates) —
   those paths are covered by the unit test suite but not by this real-candidate pilot.
3. **Regressions introduced**: none found. 0 findings added on any of the three candidates; the
   full 24-test suite passes at HEAD; ruff/ruff-format/mypy clean at HEAD (see `TEST_RESULTS.json`).
   This is evidence of absence within the pilot's scope, not proof of absence everywhere — see
   "remaining root causes" below.
4. **Production-ready or still incomplete**: **ready for Codex's integration review, with the
   limitations already on record honestly stated — not a finished, fully-hardened production
   gate.** The two specific bugs this pilot targeted are fixed and now regression-tested. But this
   pilot only exercised 3 real candidates end-to-end; `KNOWN_LIMITATIONS.md`'s broader points stand
   unchanged by this exercise — cue-pattern lists are grown from a small real sample, not
   exhaustively validated; Tier C's precision-over-recall tradeoff and the uncalibrated structural
   thresholds are still design choices, not empirically tuned; recall against contradiction shapes
   with no shared code symbol and no shared discriminator token remains unproven and likely zero.

## Remaining root causes and next production-grade actions (if pursuing further before integration)

- **Root cause**: the module's only real-world validation before this pilot was a single manual
  dry-run during implementation, with no committed mechanism to grow that validation over time.
  **Next action**: introduce the golden-corpus fixture noted as deliberately not created yet in
  `KNOWN_LIMITATIONS.md` (`tests/fixtures/public_candidate_quality/corpus.json`, mirroring
  `presentation_defects/corpus.json`), seeded with this pilot's Note-candidate case, so future
  real-candidate misses get added as data, not hand-tuned regexes reacted to blind.
- **Root cause**: precision was checked (manually, on 3 candidates); recall was not measured
  against any labeled defect set — there is no way to know, from evidence gathered so far, what
  fraction of real contradictions this module would miss. **Next action**: before or during
  integration, run the module against the exact real candidate revisions the owner-audit score
  matrices scored (`execution-2026-08-20/candidate-aspose-parity/CANDIDATE_SCORE_MATRIX.json`) and
  check whether it reproduces the documented findings for 3D `Mesh.union`/`NurbsSurface.to_mesh`
  and BarCode symbology/backend claims — **verified, not assumed**: the 3D candidate used in this
  pilot contains zero mentions of `Mesh.union`/`NurbsSurface`/`to_mesh`/`NotImplementedError`
  (`grep -in` returned no matches), and the BarCode candidate explicitly states "SVG and PNG are
  implemented for every symbology" (line 101) — the opposite of the audited "only SVG is
  implemented for Code 128" defect. Both are evidently a different/later, already-corrected
  candidate revision than the one the owner audit scored, so this pilot could not confirm or deny
  recall against those two specific historical defects — only that the module doesn't false-positive
  on their current, already-fixed replacements.
- **Root cause**: this pilot never ran with `facts`/`claim_accountability` supplied against a real
  candidate, so `claim_grounding_negative_fact` — the tier documented as most durable across LLM
  rewording — has zero real-candidate validation, only synthetic unit-test validation.
  **Next action**: Codex (who has access to real `ProductFactsV2` artifacts for these repos, e.g.
  via `plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-corrected-
  acquisition-2026-07-24/immutable-snapshot-and-product-facts-proof.json`) should run this pilot
  again with real facts supplied before trusting Tier A in production.
