# Red-test plan — disposition-ledger heading-lookup defect

Scope: Finding 2 only (`disposition_ledger_valid: false` common to all three calibration repos).
Finding 1 (Note's claim-accountability rejection) is a separate, unexamined mechanism and is
**not** covered here — no test below is Note-specific; each targets the general lookup defect in
`commands_poc.py::build_source_disposition_ledger`, matching the investigation's instruction not
to propose a Note-specific conditional.

All tests are specified as **currently failing (red)** against the code at commit
`aa998102191c530af4dca3a6895d62a4027a613e`. None were written or executed by this investigation
(read-only). Target file: `tests/unit/test_source_disposition_ledger.py` (new) or as an addition to
`tests/unit/test_template_compiler_slot_blocks.py` if a maintainer prefers to keep the two lookup
sides co-located — either target is compatible with the design below since both import the same
`compiled_slot_blocks()` used by `commands_poc.py`.

## RT-1 — case/wording drift on a genuine top-level slot

**Claim under test**: a `VERIFIED_MERGED` unit whose disposed content the composer genuinely
placed into a real contract slot must resolve to a non-empty `target`, even when the *source*
repository spells that heading's case/wording differently from the contract's canonical title.

**Setup**: construct a minimal `render` dict (matching `commands_poc.py::build_source_disposition_ledger`'s
inputs) where:
- `snapshot`'s source README contains a heading spelled `"## Key capabilities"` (sentence case, as
  real Note/3D source repositories do — see `runs/share/poc/aspose-3d-foss.../validation.json`
  error `"H2: '## Key capabilities'"`).
- The composed candidate's `readme_document_plan.compiled_slot_blocks` contains the canonical key
  `"Key Capabilities"` (title case) whose block text is present verbatim in `render["final_text"]`.
- The claim-accountability records mark this section's source span as `accepted_fact`/`survives=True`
  (→ `VERIFIED_MERGED` per `_map_accountability_disposition`), so the unit's `chosen` disposition
  is `VERIFIED_MERGED` regardless of the bug under test.

**Assert**: the resulting ledger unit for `"H2: '## Key capabilities'"` has non-empty `target` and
`_disposition_acceptance` reports it as valid, i.e. `_disposition_acceptance(ledger) == (True, [])`
for this unit's contribution (no `"retained unit without candidate destination"` error for it).

**Currently**: fails — `target == ""` because `compiled_blocks.get("Key capabilities")` misses the
key `"Key Capabilities"`.

## RT-2 — sub-heading (H3) content whose parent slot is genuinely retained

**Claim under test**: an H3 sub-heading nested inside a top-level slot that the composer genuinely
retained must not be reported as an unresolved destination merely because
`compiled_slot_blocks` has no entry at H3 granularity.

**Setup**: same shape as RT-1, but the extracted unit is `"H3: '### Native and System Requirements'"`
nested under an H2 `"## Dependencies"` slot whose compiled block text (keyed `"Dependencies"` in
`compiled_slot_blocks`) contains the literal H3 heading and its body verbatim (mirrors
`runs/share/poc/aspose-barcode-foss.../validation.json`'s error
`"H3: '### Native and System Requirements'"`, and Note's `"### Save Embedded Images to Disk"`).

**Assert**: the H3 unit resolves to a non-empty `target` (naming its enclosing slot, e.g.
`"Dependencies"`), and is not reported by `_disposition_acceptance` as missing a destination.

**Currently**: fails — `compiled_blocks.get("Native and System Requirements")` can never hit,
because `compiled_slot_blocks()` is keyed only at top-level slot granularity
([template_compiler.py:115](src/readme_agent/presentation/template_compiler.py#L115)); no key at
that granularity exists by design, not by accident.

## RT-3 — regression guard: a unit that is genuinely dropped still reports correctly

**Claim under test**: the fix for RT-1/RT-2 must not make `_disposition_acceptance` lenient for
units that really are unaccounted for. A heading with no accountability record and whose label does
not appear anywhere in the candidate must still resolve to `UNVERIFIABLE_DROPPED`/`NON_CONTENT`
with a reason, exactly as today.

**Setup**: a unit whose heading text does not appear in `raw_candidate_text` at all and has no
overlapping `source_records`.

**Assert**: `chosen == "UNVERIFIABLE_DROPPED"` (or `"NON_CONTENT"` for an empty shell) and
`_disposition_acceptance` does **not** report a "retained unit without candidate destination"
error for it (that error class only applies to `VERIFIED_MERGED`/`SUPERSEDED`) — this test exists
to prove the repair is additive to the matching logic, not a general loosening of
`_disposition_acceptance`'s rules.

**Currently**: passes today (included as a guard so a future fix cannot regress it silently, per
the requirement that a repair's invalidation radius be checked, not just its target defect).

## RT-4 — end-to-end: a real per-repo `validation.json` shape reaches `disposition_ledger_valid: True`

**Claim under test**: once RT-1/RT-2 pass, re-running `build_source_disposition_ledger` +
`_disposition_acceptance` against the actual Barcode 2026-08-20 calibration render (the smallest of
the three error sets — 3 errors, all covered by RT-1/RT-2's two failure modes) yields
`disposition_ledger_valid: True` and `disposition_ledger_errors: []`, matching what
`promote_working_condition_exceptions.py::_validate_bundle` requires for promotion.

**Setup**: replay using the frozen evidence already captured in this bundle's
`SOURCE_INVENTORY.json` (`runs/share/poc/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/validation.json`
error list: `"## Navigation"`, `"### Required Package Dependencies"`,
`"### Native and System Requirements"`) as the fixture's expected-error baseline.

**Assert**: after the fix, 2 of the 3 (the two real contract-adjacent headings) resolve; `"##
Navigation"` is expected to remain unresolved under the minimal fix described in `REPORT.md`
(Navigation is auto-generated, never a `compiled_slot_blocks` key) — this test should assert that
remaining gap explicitly rather than silently expect full closure, so a partial fix doesn't get
mistaken for a complete one. If a maintainer chooses to also cover `Navigation`/title-level
headings, this assertion should be updated alongside that broader fix, not loosened separately.

## Explicitly out of scope for this test plan

- Nothing here touches Finding 1 (claim-accountability blocking IDs) — that is a different function
  (`claim_accountability_validation.py::validate_claim_accountability_map`) with its own,
  unexamined internal logic (see REPORT.md "What's missing").
- Nothing here proposes special-casing `org_repo == "aspose-note-foss/..."` or any repo name — all
  four tests parametrize over synthetic/generic heading and slot data, matching the instruction not
  to propose a Note-specific conditional.
