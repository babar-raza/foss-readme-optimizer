# OPT-NOTE-LEDGER-ROOT-CAUSE — root-cause investigation

Read-only. Git HEAD verified at start and unchanged throughout:
`aa998102191c530af4dca3a6895d62a4027a613e` (matches the requested pin; `git status` was clean
before and after). No tracked file was edited, staged, or committed. All output lives under
`runs/owner_audit_staging/note-disposition-root-cause-aa9981021/` (gitignored).

## Executive summary

There are **two independent, unrelated defects**, not one:

1. **"Note rejects"** — `deterministic_verdict: "reject"` — is caused entirely by
   `document_validation.py`'s claim-accountability gate finding 2 unresolved
   (`blocking_claim_ids`) claims. This is unique to Note among the three calibration repos.
2. **`disposition_ledger_valid: false`** on **all three** repos (Note, Barcode, 3D) — including
   Barcode and 3D, whose `deterministic_verdict` is a clean `"accept"` — is a **systemic bug** in
   `commands_poc.py::build_source_disposition_ledger`'s heading-to-candidate-destination lookup.
   It has nothing to do with Note, nothing to do with imported-knowledge freshness, and nothing to
   do with claim accountability. Fixing (1) would not fix (2), and fixing (2) would not fix (1).

Do not read "Note rejects" and "all three show `disposition_ledger_valid: false`" as the same
phenomenon at different severities. They are produced by different functions, at different pipeline
stages, with different (and in the ledger case, identical-across-repos) evidence.

## Identity separation (as required)

| Repo | imported-knowledge repo SHA | sealed source README sha256 | current pinned source revision | freshness |
|---|---|---|---|---|
| Note | `6d97a522a9ed24708687911f1aabb76e2dea2da7` | `fd47d03c...82fdb71` | `41de2e8ab478b5aeff3663f7f7cbf83b19fdf676` | `stale_revision` |
| Barcode | `53f2c3350b8171f2c8275e7b1a178f218695ac45` | `4e311891...05c17` | `06eca5c01e13ed6d59a640f1cf330c1c5a57d151` | `stale_revision` |
| 3D | `ee05c1ba9153ef5916b7a108406c794f2e464d01` | `66ceadf1...a7cd01` | `ee05c1ba9153ef5916b7a108406c794f2e464d01` (**identical**) | `current` |

3D's imported-knowledge bundle SHA equals its current source revision — its bundle is *not*
stale — yet 3D still shows `disposition_ledger_valid: false` with the same error signature as
Note and Barcode. **This is the control case that rules out import staleness as a cause of the
ledger failure** (see Finding 2).

"Aspose candidate" / "optimizer candidate and run evidence": within this pipeline the only
candidate-bearing artifacts found are (a) the composed README candidate embedded in
`readme_document_plan`/`render["final_text"]` (optimizer-produced, the only candidate this
investigation traced) and (b) `runs/share/poc/<org>__<repo>/README.md` (the diagnostic runner's
share output). No separate "Aspose.com/Aspose.org" candidate artifact was located in the traced
evidence; if one exists elsewhere it was not exercised by this calibration pass and is reported
here as **not found**, not assumed absent.

## Finding 1 — why Note rejects

`runs/share/poc/aspose-note-foss__Aspose.Note-FOSS-for-Python/validation.json`:

```
"deterministic_verdict": "reject",
"deterministic_checks": { ..., "claim_accountability_complete": false, "aspose_checks": false, ... },
"deterministic_reason": "claim accountability has 2 blocking claim(s): candidate:claim:4579:7ff54c1da64deecb, source:claim:4064:7ff54c1da64deecb",
"independent_review_verdict": "ACCEPT",
```

Owning code: [document_validation.py:524-548](src/readme_agent/readme/document_validation.py#L524-L548)
calls `validate_claim_accountability_map` ([claim_accountability_validation.py](src/readme_agent/readme/claim_accountability_validation.py))
and folds `accountability.blocking_claim_ids` into `checks["claim_accountability_complete"]` and
`errors`. Barcode and 3D both show `claim_accountability_complete: true` and
`deterministic_verdict: "accept"` — Note is the only one of the three with unresolved blocking
claims. `aspose_checks: false` is common to all three and was **not** traced further within the
time-box (see What's missing).

A secondary, Note-specific signal in the same evidence set: `runs/share/poc/aspose-note-foss.../noop.json`
shows `"verdict": "RENDER_REPRODUCIBILITY_FAILED"` with `new_provider_call_count: 2` (Barcode and 3D
both show `RENDER_REPRODUCIBLE` with 0 new calls). This means Note's fresh-process recomposition made
2 new LLM calls that Barcode/3D's did not — plausibly downstream of the same unresolved claims
(the claim-disposition step re-invoking the LLM when accountability can't be closed
deterministically), but this causal link was **not confirmed** within the time-box.

**Root cause of "Note rejects" is not the disposition ledger.** It is 2 specific unresolved
claim-accountability records. Their exact text/byte-span content was not retrieved within the
time-box (see What's missing) — do not infer their content beyond the two IDs quoted above.

## Finding 2 — why all three show `disposition_ledger_valid: false`

Owning code: [commands_poc.py:96-222](src/readme_agent/commands_poc.py#L96-L222)
(`build_source_disposition_ledger`) and [commands_poc.py:282-300](src/readme_agent/commands_poc.py#L282-L300)
(`_disposition_acceptance`), invoked at [commands_poc.py:498-499](src/readme_agent/commands_poc.py#L498-L499)
and written to `runs/share/poc/<org>__<repo>/validation.json`.

All three repos show the identical error *shape* — `"retained unit without candidate destination: H<n>: '<heading>'"`
— for **every** heading whose disposed content was retained (`VERIFIED_MERGED`/`SUPERSEDED`):

| Repo | ledger errors | deterministic_verdict | claim_accountability_complete |
|---|---|---|---|
| Note | 16 | reject | false |
| Barcode | 3 | accept | true |
| 3D | 21 | accept | true |

The independence from Finding 1 is direct: Barcode and 3D pass claim accountability cleanly and
still fail the ledger identically to Note.

### Mechanism

For every `VERIFIED_MERGED`/`SUPERSEDED` ledger unit, [commands_poc.py:185-193](src/readme_agent/commands_poc.py#L185-L193)
does:

```python
target = ""
if chosen in {"VERIFIED_MERGED", "SUPERSEDED"}:
    heading = unit.get("heading_text", "").lstrip("#").strip()
    block_text = compiled_blocks.get(heading)
    if block_text and block_text in raw_candidate_text:
        target = heading
```

`heading` is the **source README's own literal heading text**, only stripped of a leading `#`
run and whitespace — no case or wording canonicalization. `compiled_blocks` is
`plan.get("compiled_slot_blocks")`, a dict populated by
[template_compiler.py:115](src/readme_agent/presentation/template_compiler.py#L115)
`compiled_slot_blocks()`, keyed **only by canonical, contract-normalized, top-level slot titles**
(e.g. `"Key Capabilities"`, `"Quick Start"`) — never by sub-heading text, and never in whatever
case the source repository happens to use.

Verified `compiled_slot_blocks` **is** present and correctly populated for all three repos
(pulled from the supervisor-lifecycle evidence saved alongside the same composition —
`runs/readme-poc/<repo>/<sha>/superseded/<hash>/planning/readme-document-plan.json`):

- Note: 13 keys, e.g. `"Key Capabilities"`, `"Quick Start"`, `"Documentation & Resources"`
- Barcode: 12 keys, same title-case pattern
- 3D: 11 keys, e.g. `"Documentation and Resources"` (note the wording differs slightly from Note's `&` — confirming these keys are template-contract text, not copied from any one repo's source)

So the candidate-content-provenance data (stage 5) is intact. The bug is purely in the **lookup**,
which fails two ways simultaneously:

1. **Granularity mismatch.** `build_source_disposition_ledger` opens one ledger unit per heading
   at *any* depth ([commands_poc.py:121-141](src/readme_agent/commands_poc.py#L121-L141): `if kind == "heading": ... current = {...}` fires for H1/H2/H3 alike). `compiled_slot_blocks` only
   has entries for top-level contract slots. Any H3+ sub-heading — e.g. 3D's
   `"### Scene graph (`aspose.threed`)"`, Note's `"### Save Embedded Images to Disk"` — can
   *structurally never* be a key in `compiled_slot_blocks`, because that content is part of its
   parent slot's compiled block, not a slot of its own. This alone accounts for the large majority
   of errors in Note (14/16) and 3D (15/21), and both of Barcode's H3 errors.
2. **Case/wording mismatch.** For genuine top-level H2 slot headings, the lookup still fails
   whenever the *source repository's own spelling* differs from the *contract's canonical title*
   — e.g. 3D's source literally says `"## Key capabilities"` and `"## Quick start"` (sentence
   case), while `compiled_slot_blocks` is keyed `"Key Capabilities"` / `"Quick Start"` (title
   case). `str.lstrip("#").strip()` does nothing to reconcile this. This accounts for 3D's
   remaining errors (`At a glance`, `Key capabilities`, `Quick start`, `Additional examples`,
   `API reference`, `Documentation & resources`, `Scope and limitations`, `Development and
   testing` — 8 of its 21) and both repos' `"## Navigation"` error (`"Navigation"` is an
   auto-generated heading, never a `compiled_slot_blocks` key at all, so it fails outright
   regardless of case).

A `## Navigation` and (for 3D) the H1 title are further edge cases: they are not contract "slots"
at all (auto-generated / not part of the `sections` dict `compiled_slot_blocks()` iterates), so
they can never resolve under the current design even in principle — a third, narrower gap in the
lookup's scope, distinct from (1) and (2).

### Control case ruling out staleness

3D's imported-knowledge bundle is **current** (`freshness: "current"`, bundle SHA == source
revision — see identity-separation table above), unlike Note/Barcode's `stale_revision`. 3D still
fails the ledger with the identical error shape. This directly answers the investigation's
"is it stale evidence?" question: **no** — freshness of the imported-knowledge corpus is orthogonal
to and does not affect the disposition-ledger defect.

### Ruling out the other candidate causes

- **Missing equivalence linkage / source-placement loss**: no — `compiled_slot_blocks` is present
  and its block text is genuinely present in the final candidate (stage 5 intact); the bug is in
  the ledger's own bookkeeping, not in what the composer actually produced or where content landed.
- **Acceptance fail-open behavior**: no — the opposite. The diagnostic runner correctly fails
  *closed* (`disposition_ledger_valid: false`, `acceptance_authority: false`), and the one real
  promotion gate that reads this field also fails closed (see below). This is a false negative
  inside a fail-closed check, not a fail-open gap.
- **Bad identity normalization**: **yes** — this is the accurate characterization. The lookup
  compares a source-side heading identity against a contract-normalized candidate-side identity
  without normalizing either side to a common form, and never resolves a nested heading to its
  enclosing slot's identity.

## Is this the same code the freshness-service lane already touched?

**Yes — direct overlap, not a fresh area.** `plans/investigations/evidence/freshness-service-t5/closeout.md`
(2026-08-15, duplicated under `freshness-service-final-2026-08-15/t5-closeout.md`) documents a
prior fix ("T5") to this *exact* defect class: it added `compiled_slot_blocks()`, threaded
`compiled_slot_blocks` through `ReadmeDocumentPlanV1`/`VerifiedTemplateCompilationV1`, and wired
`build_source_disposition_ledger`'s `target` lookup to it — explicitly to fix "a plain string
mismatch" between the source heading's literal `"##"` prefix and the bare contract heading,
"fixed with `heading.lstrip("#").strip()`" — the exact line still present today at
[commands_poc.py:190](src/readme_agent/commands_poc.py#L190).

The gap: T5's own regression tests
([tests/unit/test_template_compiler_slot_blocks.py](tests/unit/test_template_compiler_slot_blocks.py))
use a synthetic fixture whose section headings are *already spelled identically* to their contract
titles (`"Installation"` → `"Installation"`, etc.) and contain no nested H3 sub-headings. Neither
the case/wording-drift failure mode nor the sub-heading-granularity failure mode this calibration
run exposes on real Note/Barcode/3D READMEs is exercised by T5's tests, nor (per its own closeout
narrative) its single live-pilot re-run. **The freshness-service lane owns this code and left it
partially fixed; this is a continuation of that lane's work, not a new area.**

## Blocking vs. diagnostic

- **Diagnostic only, within `commands_poc.py` itself**: `validation.json` explicitly carries
  `"acceptance_authority": false` and an `acceptance_exclusion` string stating the poc runner
  "bypasses the mission graph, durable lifecycle, recovery, and the complete canonical supervisor
  transaction." `disposition_ledger_valid` never touches the mission graph or durable lifecycle
  directly.
- **Blocking, one call site**: [scripts/governance/promote_working_condition_exceptions.py:136-146](scripts/governance/promote_working_condition_exceptions.py#L136-L146)
  `_validate_bundle` raises `ExceptionAcceptanceError` when `disposition_ledger_valid is not True`
  or `disposition_ledger_errors` is non-empty. Confirmed by repo-wide grep (`src/`, `scripts/`,
  `tests/`) that this is the **only** other reader of the field. As of this calibration pass, this
  gate would refuse to promote **all three** repos — including Barcode and 3D, whose deterministic
  verdict is otherwise a clean, uncontested accept.

## First incorrect transition

`src/readme_agent/commands_poc.py::build_source_disposition_ledger`, lines 185-193 (the `target`
assignment block quoted above under Finding 2 → Mechanism). This is where a unit that was
genuinely, correctly disposed `VERIFIED_MERGED`/`SUPERSEDED` is nonetheless assigned `target = ""`
because the lookup key doesn't match, which `_disposition_acceptance` (lines 282-300) then reports
as an error, flipping `ledger_valid` to `False`.

## Smallest generic repair (not proposed as a Note-specific conditional; not implemented here)

The lookup at commands_poc.py:185-193 needs to become identity-aware instead of literal-string:

1. Canonicalize both sides before comparing (the same normalization `template_compiler.py`
   itself uses to derive a contract slot's canonical title from its slot key — not a
   Note-specific string transform, applies uniformly to every repo/heading).
2. For a heading deeper than the top level, resolve to its nearest ancestor heading that *is* a
   contract slot before doing the `compiled_slot_blocks` lookup, then confirm the sub-heading's
   own text is a substring of that ancestor's compiled block (preserving the existing "proven by
   substring match against the compiler's own output, never guessed" guarantee for the
   parent-level check, while correctly attributing nested content to its enclosing slot).

**Invalidation radius**: confined to `commands_poc.py::build_source_disposition_ledger`'s target
assignment and `_disposition_acceptance`'s consumption of `target` — a purely diagnostic
computation with `acceptance_authority: false`. It does not touch `compiled_slot_blocks` itself
(already correct, per T5's own tests), candidate composition, or any acceptance semantics outside
this one field. Downstream blast radius is exactly the two consumers identified above: (a)
`validation.json`'s `disposition_ledger_valid`/`disposition_ledger_errors` fields recompute, and
(b) `promote_working_condition_exceptions.py`'s gate, which would then correctly distinguish
Barcode/3D (would newly pass, once the ledger reflects reality) from Note (would still correctly
fail — Finding 1 is untouched by this repair). No existing test asserts the current (broken)
`disposition_ledger_valid: false` as expected behavior — `tests/unit/test_promote_working_condition_exceptions.py`'s
fixture already hard-codes `disposition_ledger_valid: True` — so this repair carries no known
test-suite regression risk within what this investigation examined.

## What's missing (reported, not guessed)

- The literal text/byte-span content of Note's 2 blocking claim IDs
  (`candidate:claim:4579:7ff54c1da64deecb`, `source:claim:4064:7ff54c1da64deecb`) was not located
  within the time-box (not present in the superseded `candidate/claim-map.json`; likely lives
  inside `readme_document_plan.claim_accountability`, not separately pulled).
  `claim_accountability_validation.py::validate_claim_accountability_map`'s internal logic for
  deciding `approval_eligible`/`blocking_claim_ids` was located but not read line-by-line.
- `facts.content_assurance == "repository_verified"` was confirmed directly from evidence only for
  Note (`product-facts.json`); for Barcode/3D it is inferred from `compiled_slot_blocks` being
  non-empty in their saved document plans (which requires that gate to have been true), not
  independently re-read from their own `product-facts.json`.
  a. `aspose_checks: false` (common to all three) was not traced to its owning check module.
- Whether the "five-bucket" `readme_reconciliation.py::build_readme_reconciliation_report`
  (stage 6) runs anywhere in the *supervisor* lifecycle for these three repos (confirmed only that
  it is not imported by `commands_poc.py`, the diagnostic runner actually exercised here).
- Stage 9 (cache/no-op binding) was read from `commands_poc.py` source only; Note's
  `RENDER_REPRODUCIBILITY_FAILED` / 2-new-provider-calls anomaly (Finding 1, secondary signal) was
  not causally traced to the claim-accountability gap — flagged as a plausible link, not confirmed.
- `runs/readme-poc/<repo>/diagnostics/` directories exist for all three but are dated 2026-08-19
  (the prior, Docker-blocked attempt), not today's run; not read in detail.

## Evidence index (primary files read)

- `runs/share/poc/aspose-note-foss__Aspose.Note-FOSS-for-Python/validation.json`
- `runs/share/poc/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/validation.json`
- `runs/share/poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/validation.json`
- `runs/readme-poc/aspose-note-foss__Aspose.Note-FOSS-for-Python/41de2e8ab478b5aeff3663f7f7cbf83b19fdf676/{manifest.json,knowledge-application.json,source/revision.json,superseded/f82701b645a37e59/{superseded.json,planning/readme-document-plan.json}}`
- equivalent paths for Barcode (`06eca5c0.../superseded/8f9985d5.../`) and 3D (`ee05c1ba.../superseded/721b58c0.../`)
- `src/readme_agent/commands_poc.py`, `idea_candidate.py`, `document_renderer.py`,
  `document_plan_finalizer.py`, `document_plan.py`, `document_validation.py`,
  `claim_accountability_validation.py`
- `src/readme_agent/presentation/template_compiler.py`, `verified_template_document.py`,
  `verified_template_runtime.py`
- `scripts/governance/promote_working_condition_exceptions.py`
- `tests/unit/test_template_compiler_slot_blocks.py`
- `plans/investigations/evidence/freshness-service-t5/closeout.md`
- `plans/backlog-post-poc.md` (git log context for the 2026-08-20 calibration commit)

Full path/hash detail in `SOURCE_INVENTORY.json`; per-stage trace in `TRACE_MATRIX.json`; a
minimal regression-test specification for Finding 2 is in `RED_TEST_PLAN.md`.
