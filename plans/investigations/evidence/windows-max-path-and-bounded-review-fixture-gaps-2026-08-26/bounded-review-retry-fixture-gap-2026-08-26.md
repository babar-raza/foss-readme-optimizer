# VER-012 — offline bounded-review test fixture has no path for a grounding retry

## Status

Root-caused down to the exact production mechanism. Not repaired: reconstructing a
correct compact-retry response requires parsing `grounding_retry_context()`'s
reconciliation payload, which is a genuinely separate, deeper task from the three
fixes this investigation thread already delivered.

## Symptom

`tests/unit/test_supervisor_loop.py::TestBasicLoop::
test_local_poc_records_snapshot_and_profile_before_later_stages` fails with:

```
AssertionError: fixture reviewer could not find its typed review input
```

raised from `tests/review_role_fixture_support.py::GroundedAcceptingRoleReviewClient.analyze()`.

A full run of `test_supervisor_loop.py` after the three fixes below (79 passed,
4 failed) confirmed this is not isolated to the one reproduction test: three more
in the same file hit the identical symptom -- `TestBasicLoop::
test_local_poc_repairs_revalidates_and_rereviews_before_accepting`,
`TestBasicLoop::test_local_poc_byte_identical_repair_reroutes_before_rereview`,
and `TestBasicLoop::test_heterogeneous_local_poc_members_share_the_real_supervisor_path`.
All four exercise the shared `project`/equivalent fixture through a bounded-review
path whose first attempt fails grounding validation. The other 79 tests in the
file, and all 146 tests across `test_specialists.py`, `test_readme_review_roles.py`,
and `test_separated_readme_review.py`, are unaffected -- confirming the fixes
below are correct and this is a bounded scope, not a wider regression.

## How this was reached (three real fixes landed first)

This test was the reproduction vehicle for an unrelated Windows `MAX_PATH`
investigation. Fixing that investigation's three real bugs peeled back three
layers of masking, in order:

1. `local_poc_review_cache_preservation.py`'s three-part `MAX_PATH` bug (already
   committed, `494956397`) let `preserve_bounded_review_cache()` actually execute
   instead of silently no-op'ing.
2. `local_poc_superseded.py`'s downstream-pruning `shutil.rmtree()` raised
   `WinError 145` ("directory not empty") immediately afterward -- a known,
   already-documented transient Windows/AV race (`SCL-010`,
   `gitsafety/clone.py::force_rmtree`). Routing that one call through the
   existing, proven `force_rmtree()` helper (this session's change) fixed it and
   let the test's second `supervise_repo()` call proceed into real bounded-review
   execution for the first time.
3. That exposed a real, pre-existing test-fixture gap from an earlier session fix
   on the same day (`fix(review): route by rubric evidence, not candidate size`,
   `6591c6cc2`): this fixture's shared `project` fixture faked
   `build_live_merged_review_client` but never `build_live_role_review_clients`,
   so any candidate that now correctly routes to bounded review (not just
   oversized ones, per that commit) fell through to a real, unfaked network path.
   Fixed this session by wiring `_fake_accepting_role_clients` in alongside the
   existing merged-review fake.
4. That in turn exposed `tests/review_role_fixture_support.py`'s
   `_blind_candidate_anchor()` expecting `{"anchor_id": ..., "text": ...}` dicts
   from the candidate catalog, when the sole production producer
   (`compact_candidate_anchor_catalog()`,
   `specialists/factual_review_projection.py:33`) has always returned compact
   `[anchor_id, text]` pairs -- this file's own `_merged_accept_payload` in
   `test_supervisor_loop.py` already parsed the same field correctly as a list.
   Fixed this session to match.

Each of the four fixes above is independently correct and verified (146 tests
across `test_specialists.py`, `test_readme_review_roles.py`, and
`test_separated_readme_review.py` still pass; the target test's failure mode
changed after each one, converging steadily closer to root cause rather than
recurring).

## Root cause of the remaining, unfixed gap

`review_role_execution.py::run_grounded_role()` deliberately drops the original
catalog-bearing prompt turn on a grounding retry (`context_mode =
"compact_grounding_retry"`, `review_role_execution.py:321-324`):

```python
current_messages = [
    *[message for message in messages if message.get("role") == "system"],
    retry_message,
]
```

`retry_message` is built from `grounding_retry_context()`
(`review_finding_grounding.py:1459`), a compact reconciliation payload -- not the
original candidate catalog. Confirmed live by dumping the actual `messages` list
`GroundedAcceptingRoleReviewClient.analyze()` received on the second call: two
messages only, `[system, retry_turn]`, where `retry_turn`'s content is the
`turn_context_template` ("Your previous findings failed deterministic
grounding...") with no "Complete candidate README block catalog" text anywhere.

This retry compaction is intentional production design (token economy on retry),
not a bug. But `GroundedAcceptingRoleReviewClient`/`_blind_candidate_anchor` was
only ever written against the first-attempt message shape -- it has no branch for
`context_mode == "compact_grounding_retry"` at all, so any test scenario whose
first bounded-review attempt fails grounding validation (for whatever reason)
crashes the fixture on the retry rather than producing a second, corrected
response.

Not yet determined: why the FIRST bounded-packet attempt's fixture response
fails grounding validation in this specific test scenario (it does not in the 146
tests that already exercise `GroundedAcceptingRoleReviewClient` successfully,
none of which appear to reach a retry). That is the next thing a follow-up fix
would need to establish before extending the fixture.

## Why it was not fixed here

Two independent unknowns remain, each large enough to be its own task:
(a) why the first attempt's grounding validation fails for this test's specific
bounded packet, and (b) how to correctly reconstruct a schema-valid, grounded
response from only `grounding_retry_context()`'s compact reconciliation payload
(no catalog, no candidate text substring the current fixture parses) if the
first-attempt cause turns out to be legitimate rather than fixable at the fixture
level. Both require dedicated investigation separate from the `MAX_PATH` work
that surfaced them.
