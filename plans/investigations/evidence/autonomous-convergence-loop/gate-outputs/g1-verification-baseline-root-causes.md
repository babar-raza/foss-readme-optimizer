# G1 — verification-baseline restoration: root causes and repairs

Baseline (HEAD `1d915e9b07b0`, before any change this session):
`5 failed, 5498 passed, 1 skipped` (`runs/acl-baseline-pytest.log`). The run's own metadata
records `dirty_tree: true` / `tree_changed_during_run: true` because repair work started while it
was still running, so that number is a diagnostic reading, not proof about a committed state. The
proof-eligible run is the clean-tree `run_official_checks.py` recorded separately.

Note this is already far better than the 2026-08-27 production-recovery sprint's `22 failed`;
most of that set was fixed between then and now by other work. Only the five below remained.

## RC-A — vendored check-battery pin drift (1 test)

`test_aspose_org_check_battery_source.py::test_vendored_check_battery_matches_its_content_addressed_manifest`

**Cause.** Commit `d8795bbdb` ("perf(validation): bound narration scans", 2026-08-28) edited
`vendored_asposeorg/.../readme_refresh_checks.py` and did not re-pin
`data/imported/aspose_org_check_battery_manifest.json`. Recorded
`ef3fafc84260…`, actual `21fbcd4a2f1b…`.

**Repair.** Re-pinned the file digest and `aggregate_sha256`, and recorded a
`local_adaptations` entry naming the commit, the date, and why the change is match-preserving
(per-pattern regexes sorted by `(start, pattern_index, end)` reproduce the combined regex's
leftmost-then-first-alternative choice; `consumed_until` reproduces its post-match scan advance).
This follows the manifest's own existing convention rather than silently overwriting a hash.

**Recurrence prevention — the more important half.** The drift was invisible to CI:
`validate_pinned_hashes.py` (the `pinned-hashes` CI job) reported **clean** throughout, because
this pin is deliberately excluded from its registry in favour of its own dedicated test. That
dedicated test ran only from `validate_pinned_hash_dedicated_tests.py`, which is pre-commit-only
**and** filters to files staged in the current commit — and the hook itself only landed on
2026-08-29, one day *after* the drift. So nothing could have caught it, and nothing would catch
the next one from an unhooked clone.

Added `--all` to `validate_pinned_hash_dedicated_tests.py` (runs every registered dedicated pin
test regardless of staging) and wired it into CI's `pinned-hashes` job. The staging-scoped default
remains the pre-commit path, which still catches drift one commit earlier than CI can.

## RC-B — `_inventory_valid` under-enumerates past Windows MAX_PATH (blocks 3 tests; fixing it resolved 1)

`test_supervisor_loop.py::TestBasicLoop::{test_local_poc_records_snapshot_and_profile_before_later_stages,
test_local_poc_repairs_revalidates_and_rereviews_before_accepting,
test_local_poc_byte_identical_repair_reroutes_before_rereview}`

**This one is a live product defect, not a stale test.** The 2026-08-27 sprint classified these
three as `TEST_ASSUMPTION_WRONG` (fixture contract drift, VER-012). That classification is wrong,
and the correction matters because the defect blocks the mission's central acceptance state.

**Observed.** All three fail with lifecycle stuck at `AGENT_APPROVED` instead of `NO_OP_PROVEN`.
Single-process instrumentation of one run:

```
[EV] AFTER refresh_sha256sums   inv=64  inv_cache=18  disk=46  cache_files=18
[EV] ENTER promote_approved_noop inv=64 inv_cache=18  disk=46  cache_files=18
     promote_approved_local_poc_noop -> promoted=False reusable=False
     decision_status=INVALIDATED earliest_affected_stage=CANDIDATE_GENERATED
     mismatch: artifact_inventory_invalid
```

`46 + 18 = 64`. The sealed inventory listed 64 artifacts; the validator's own walk saw 46; the
18 it missed were exactly the `review/bounded-packet-cache/*.json` entries, which were present on
disk the whole time. Nothing deleted them — they were never enumerated.

**Root cause.** `evidence/writer.py` seals *and* verifies through
`evidence/file_inventory.py::enumerate_files()`, which prefixes `\?\` on Windows and passes
`onerror=raise_walk_error` so a traversal failure raises. `supervisor/local_poc_cache.py::_inventory_valid()`
had hand-rolled a **second, independent** walk using `Path.rglob("*")`, which has neither
property: pathlib silently swallows the `os.scandir` failure Win32 raises at or beyond MAX_PATH.
The real bundle shape reaches that limit on repository-name length alone —
`<repo>/<40-char revision>/review/bounded-packet-cache/<64-hex>.json` measures 260 characters for
`aspose-note-foss__Aspose.Note-FOSS-for-Python` and 259 for `aspose-3d-foss__Aspose.3D-FOSS-for-Python`,
per `win_long_path`'s own docstring.

**Consequence.** On Windows, an intact approved bundle is reported `artifact_inventory_invalid`,
`evaluate_approved_local_poc_cache()` refuses reuse, and **`NO_OP_PROVEN` is unreachable for
exactly the repositories whose names are longest.** `NO_OP_PROVEN` is the mission's terminal
per-repository acceptance state, and this repository runs on Windows.

**Repair.** `_inventory_valid()` now reuses `enumerate_files()` — the same enumeration that sealed
the inventory — instead of walking the tree a second way. Traversal errors now fail closed rather
than masquerading as a content mismatch.

**Tests.** New `tests/unit/test_local_poc_cache_inventory_long_path.py`: one test proving a bundle
whose cache entries exceed MAX_PATH validates (with `verify_sha256sums` as the reference oracle),
and one negative control proving a tampered entry under the same long path is still rejected — so
the fix cannot degrade into a rubber stamp. Both are Windows-gated.

**Correction after independent verification.** As first committed these two tests passed standalone
and **failed inside the project's own `run_full_pytest.py`**. That runner deliberately passes a
short `--basetemp` (`%TEMP%/ra-p`), so the fixture's fixed 40+40 padding landed on exactly 260 and
its own `> 260` guard tripped. An earlier revision of this file claimed they matched
`test_local_poc_review_cache_preservation.py`'s precedent; they matched its `skipif` but not its
padding, which is the part that makes it work. The fixture now *derives* its depth from the
measured path length so it holds under any `basetemp`, and the guard is `>= 260` to match
`win_long_path`'s own "at or beyond 260". Verified passing under both a short and a long basetemp.

**Scope correction.** Repairing RC-B resolved one of the three `test_supervisor_loop.py` failures.
The other two advanced past their original assertion and then failed on a separate, pre-existing
cause (VER-012 reviewer-double drift), recorded below and in `logs/2026-08-29.md`. RC-A + RC-B +
RC-C therefore do not account for all five baseline failures on their own.

## RC-C — validator ignores the producer's `verified_equivalence` narrowing (1 test)

`test_verified_source_opening.py::test_verified_pdf_opening_keeps_source_and_audience_provenance_exact`
(tracked under VER-013)

**Observed.** `structured_fact_coordinates_exact failed`. Instrumented:

```
claim=claim:1351:2f02923bb13c9406 stage=source
  resolution=verified_equivalence  fact_ids=['product.limitations:repository-extension']
  record.accepted_fact_ids=['product.limitations:repository-extension']
  missing=[('product.capabilities:repository-extension', '/items/34d1050178ff2e21')]
```

**Root cause.** A producer/consumer divergence. `claim_accountability.py` deliberately narrows a
`verified_equivalence` claim's coordinates to the resolution's exact fact scope, with its own
comment: "Do not let broader contextual source binding inflate that subset and make the resulting
map fail its own exact-equivalence validation." `claim_accountability_validation.py` re-derives
expected coordinates from `structured_fact_coordinates` plus the complete-claim binder and applies
no such narrowing — so it demands a `product.capabilities:*` coordinate the producer was correct
to drop. The validator was doing precisely what the producer's comment warns against.

**Repair.** The validator now builds an equivalence fact-scope map from `source_claim_resolutions`
and applies the identical narrowing before the subset comparison. The producer is authoritative
here; the validator was the side that had drifted.
