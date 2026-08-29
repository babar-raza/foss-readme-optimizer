# G5 — independent verification: findings and same-cycle repairs

An independent lane that did not implement the work was given an adversarial brief: refute each of
five claims about commit `176b679d`, hunt for weakened checks, prove the new tests are not vacuous,
and report the full-suite numbers itself. It confirmed the two central repairs and found six
defects. All six are repaired in the same cycle; two remain open and are stated as open.

## What it confirmed

- The MAX_PATH under-enumeration is real and the fix works. Its own probe at a genuine 271-character
  cache path: sealed inventory 4 entries, old `rglob` saw 2, old implementation `False`, new `True`,
  tampered `False`.
- The expired-claim recovery is real: pre-fix `evaluate` leaves `active_task_id` set with empty
  eligibility; post-fix it clears the claim, records `REGRESSED`, and restores eligibility.
- The `verified_equivalence` narrowing is load-bearing and symmetric, not a weakening. It verified
  by reverting the file in memory to its parent-commit version and reproducing exactly
  `structured_fact_coordinates_exact failed`, and by reading the compensating checks
  (`_complete_resolution` rejects an empty `fact_ids`; `verified_equivalences_have_exact_candidate_claims`
  requires set equality against the source record).
- The CI `--all` gate works: exit 0 unmodified; exit 1 on a temp-copy drift with the exact
  recorded-vs-actual mismatch printed.

## Defects it found, and the repairs

**D1 (blocking) — the commit's own new tests failed inside the canonical runner.**
`run_full_pytest.py` passes `--basetemp=%TEMP%/ra-p` ("keep this deliberately short"), so the
fixture's fixed 40+40 padding produced a path of exactly 260 and its own `assert > 260` guard
tripped. They passed only under a bare `pytest`, where `tmp_path` is longer. So the earlier
"5 failing tests -> 2" claim was wrong: by the project's own runner it was 5 -> 4, two of them
newly introduced by this very commit.

Repaired: the fixture now *derives* its padding depth from the measured path length and asserts
both bounds (cache entry at or beyond MAX_PATH; bundle root below it, so the inventory still
opens). The guard is `>= 260`, matching `win_long_path`'s own "at or beyond 260".

Re-proved non-vacuous under the canonical short basetemp, with the pre-fix `rglob` restored
in memory: the positive test fails and the negative control still passes —

```
>>> pre-fix rglob restored
FAILED test_inventory_validates_a_bundle_whose_cache_path_exceeds_max_path
1 failed, 1 passed
```

**D2 — two sibling sites carried the identical defect over the same bundle.**
`local_poc_snapshot_evidence.py::_is_checksum_valid_intake_only_bundle` and
`evidence.py::assert_evidence_complete` both re-walked with `Path.rglob("*")`. The first fails
**open** — under-enumeration there can classify a complete bundle as intake-only — which is the more
dangerous direction than the one originally fixed. Both now use `enumerate_files()`. The original
fix was incomplete and the report did not say so.

**D3/D4 — `_inventory_valid`'s docstring overstated twice.** It claimed the new code "fails closed"
on a traversal error; it returns `False`, reaching the same `artifact_inventory_invalid` reason
string, so the error is no longer silent but the caller gets no new signal. It also implied no
behaviour change outside long paths; a bundle containing a dangling symlink now evaluates `False`
where `rglob`'s `is_file()` filter skipped it. Docstring corrected on both points.

**D5 — `persist_evaluation`'s docstring stated a safety guarantee that is false.** It said "an
unexpired claim is never touched … a routine evaluation cannot cancel a live worker". The verifier
demonstrated two counter-examples: an unparseable `claim_expires_at` makes `_claim_expired()`
return `True`, and the comparison uses the evaluating machine's clock, so skew releases a live
lease. Both predate this change on the `claim` path; what is new is that they are reachable from
`evaluate`, which a monitoring loop calls often. Docstring now says what is true, and names the
tightening as separate work.

**Misattributed citation, including in production source.** "reconciles graph drift, claims,
lifecycle freshness, and component hashes" is `plans/idea.md:158`, not `plans/master.md`.
`plans/master.md:476` says only that `evaluate` "first reconciles closed-task freshness", which does
not mention claims. The misattribution had propagated into `mission_control.py`,
`test_mission_control.py`, `logs/2026-08-29.md`, and `g0-…md` (there as a direct quotation).
Corrected in all four. The defect stands either way — the recovery function had one caller — but
the "documented behaviour disagrees with actual behaviour" framing rests on the product-intent
document, not the architecture plan.

## Left open, deliberately and explicitly

**D6 — widened failure surface on `evaluate`, untested.** With `active_task_id` set, the lease
expired, and that task's status not `IN_PROGRESS`, `persist_evaluation` now raises
`StateBackendError` where the old `evaluate` returned normally. The verifier could not reach that
state through `transition_task` (it clears `active_task_id` on any non-`IN_PROGRESS` transition),
so this is latent rather than a demonstrated regression — but it is a real widening on a
read-mostly command, with no test. Not fixed here; recorded.

**D7 — two residual gaps on the equivalence narrowing.** The producer raises `ValueError` on a
stale resolution (span/content-hash mismatch) before narrowing; the validator applies the narrowing
with no staleness re-check. And the commit added no test for that file, so there is no negative
control proving an equivalence record that omits an *in-scope* coordinate is still rejected. Not
fixed here; recorded.

## Also found, pre-existing and not caused by this work

`plans/investigations/tools/traceability_matrix.py --check` exits 1 on three `IMPLEMENTED` rows
that cite neither a pytest node nor a committed evidence artifact: `LLM-023` (commit `3e4da1b88`,
2026-08-27), `CORE-041` (`67f66f6d9`, 2026-08-28), `CORE-042` (`f1efd83a2`, 2026-08-28). All three
predate this sprint. This is one of the official checks, so it keeps `run_official_checks.py` red
independently of anything here.
