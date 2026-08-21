# OPT-CANDIDATE-ASPOSE-PARITY-AUDIT

Direct, candidate-byte-level quality audit of the latest Stage-5 optimizer README candidates
for three Python products, scored against
`plans/investigations/owner_audit/aspose_candidate_rubric/RUBRIC_30.md`. Read-only. No tracked
file was edited, no commit was made, no pipeline/Qwen/Docker command was run, and no candidate
was regenerated.

- **Repository pin (this workspace):** `aa998102191c530af4dca3a6895d62a4027a613e`
- **Aspose.org checkout (read-only reference):** `D:\onedrive\Documents\GitHub\aspose.org`
- **Time-box:** 45 minutes (recon + three parallel per-product deep audits + assembly)
- **Output directory:** `runs/owner_audit_staging/candidate-aspose-parity-aa9981021/`

## What "latest Stage-5 candidate" resolved to

This repository has no literal "Stage 5" label. The freshest, most fully processed optimizer
output for all three products is `runs/share/poc/<repo>/README.md` plus its sibling
`dispositions.json`, `noop.json`, `validation.json`, and `UPSTREAM-DEFECTS.md` — all five files
for all three products were written today (2026-08-20, 10:35–10:38, minutes before this
workspace's pinned commit), by the committed `readme-agent poc` runner. This audit treats that
directory as the "Stage-5 candidate" and its sibling files as the "exact run evidence." This
interpretation and its basis are recorded in `INGEST_MANIFEST.json`.

## The four identities, kept separate

| Product | Sealed pre-refresh source README | Current published README | Aspose.org canonical candidate | Optimizer Stage-5 candidate |
|---|---|---|---|---|
| Aspose.3D FOSS for Python | `plans/investigations/evidence/full-registry-github-survey/aspose-3d-foss__Aspose.3D-FOSS-for-Python--README.md` (189 lines) | `runs/work/aspose-3d-foss__Aspose.3D-FOSS-for-Python/README.md` @ `ee05c1ba…` | `D:\onedrive\...\reports\repo-presenter-regen-full\3d\python\readme.md` | `runs/share/poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/README.md` |
| Aspose.BarCode FOSS for Python | `plans/investigations/evidence/full-registry-github-survey/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python--README.md` (215 lines) | `runs/work/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/README.md` @ `06eca5c0…` | `D:\onedrive\...\reports\repo-presenter-regen-full\barcode\python\readme.md` | `runs/share/poc/aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/README.md` |
| Aspose.Note FOSS for Python | `plans/investigations/evidence/full-registry-github-survey/aspose-note-foss__Aspose.Note-FOSS-for-Python--README.md` (478 lines) | `runs/work/aspose-note-foss__Aspose.Note-FOSS-for-Python/README.md` @ `41de2e8a…` | `D:\onedrive\...\reports\repo-presenter-regen-full\note\python\readme.md` | `runs/share/poc/aspose-note-foss__Aspose.Note-FOSS-for-Python/README.md` |

Exact SHA-256 for every file above is in `INGEST_MANIFEST.json`.

**Evidence-integrity caveat (not a candidate defect):** `plans/investigations/owner_audit/sealed_replay_quality/REPLAY_FIXTURES.json`
declares a different SHA-256 than what the sealed pre-refresh README files above actually hash
to, for all three products. Line counts and prose content match that report's own
characterization of the pre-refresh README exactly (189 / 215 / 478 lines), so this audit
treats the file content as correct and flags only the fixture's recorded hash as stale. See
`INGEST_MANIFEST.json` → `evidence_integrity_findings`.

## Scores

| Product | A (8) | B (5) | C (7) | D (5) | E (5) | **Total (30)** | Hard disqualifiers | Accepted 30/30 |
|---|---|---|---|---|---|---|---|---|
| Aspose.3D FOSS for Python | 5 | 1 | 4 | 2 | 2 | **14** | 2 | No |
| Aspose.BarCode FOSS for Python | 5 | 1 | 3 | 3 | 3 | **15** | 3 | No |
| Aspose.Note FOSS for Python | 4 | 0 | 6 | 5 | 0 | **15** | 3 | No |

No candidate reaches acceptance. Every product carries at least one **hard disqualifier**
(rubric §"Hard disqualifiers"), which makes numeric subtotal moot for acceptance regardless of
the score. Full per-criterion rows, evidence spans, and Aspose comparisons are in
`CANDIDATE_SCORE_MATRIX.json`.

## Hard disqualifiers, by product

### Aspose.3D FOSS for Python (14/30, 2 disqualifiers)
1. **Contradicted API claim (#1).** The "API Method Index" lists `Mesh.union`/`do_boolean`/
   `difference`/`intersect`, `NurbsCurve.evaluate`, and `NurbsSurface.to_mesh` as ordinary
   working members — while the same document's own "Scope and Limitations" section says these
   exact members raise `NotImplementedError`. A reader following the API reference is told
   the opposite of what the limitations section (in the same file) says.
2. **Blocking check failed, promotion continued anyway (#3).** `validation.json` records
   `disposition_ledger_valid: false` with 21 concrete errors for this exact candidate hash, but
   the promotion/status computation in `commands_poc.py::run_poc_for_repo` never consults
   `ledger_valid`, and the portfolio `RESULTS.md` reports this product `DELIVERED … none`.

Also independently found: a content-free Quick Start (`scene = Scene()` and nothing else), the
public API surface documented three separate, overlapping times, an orphaned dangling bullet in
Key Capabilities, and a Mermaid diagram where 6 of 8 input/output nodes are unwired.

### Aspose.BarCode FOSS for Python (15/30, 3 disqualifiers)
1. **Material contradicted capability claim (#1).** The opening line describes the product as
   Code-128-only, while it actually supports 7 symbologies including QR. "Scope and Limitations"
   separately claims "only the SVG backend is implemented for Code 128/Code 39" — directly
   contradicted by the candidate's own `to_png()` examples a few sections earlier, and by the
   real source (`_internal/renderers/png.py`).
2. **Blocking check failed / error envelope while promotion continued (#3).** `validation.json`
   shows `disposition_ledger_valid: false` (3 unresolved errors) and `aspose_checks: false`, yet
   `deterministic_verdict: "accept"` and `independent_review_verdict: "ACCEPT"`. Worse,
   `dispositions.json` marks the H1 title, Key Capabilities, and API Reference sections
   `UNVERIFIABLE_DROPPED` while all three are verbatim present in the shipped candidate — a
   fabricated disposition, not merely a missing one.
3. **Old-README content silently dropped (#5).** The disposition ledger was built only against
   the 262-line *current published* README, never against the true 215-line sealed pre-refresh
   original. That original's Error Handling section and its detailed Supported-Symbologies input
   table vanish from the candidate with no ledger record of any kind.

### Aspose.Note FOSS for Python (15/30, 3 disqualifiers)
1. **Contradicted API/limitations claim (#1).** `License.SetLicense`, `Metered.SetMeteredKey`,
   and `Document.DetectLayoutChanges()` are documented as functional API members. The immediate
   predecessor README (identity 2, same revision) explicitly discloses all three as no-op/stub
   in this FOSS edition; the optimizer candidate drops that disclosure while keeping the
   functional-sounding description, in both the API reference and Scope and Limitations.
2. **Blocking check failed, evidence contradicts the delivered status (#3).** `validation.json`
   records `deterministic_verdict: "reject"` (`claim_accountability_complete: false`, 2 named
   unresolved blocking claims) and `disposition_ledger_valid: false` (16 errors); `noop.json`
   records `RENDER_REPRODUCIBILITY_FAILED` (2 unexpected LLM calls during a supposed no-op
   replay). Despite this, `runs/share/poc/RESULTS.md`'s top, hand-curated, product-owner-facing
   summary table marks this exact repo **`DELIVERED` / `none`** — directly contradicting both
   the bundled evidence and that same file's own stated definition of "DELIVERED" a few lines
   above it, and contradicting its own auto-appended diagnostic log lower in the same file
   (`DIAGNOSTIC_VALIDATION_reject`).
3. **Old-README content silently dropped (#5).** The "Extract Attached Files" code example,
   present in the current published README, has no equivalent anywhere in the 687-line candidate
   and is not named in `UPSTREAM-DEFECTS.md` as a disclosed block — it simply vanished. The CI
   badge is dropped from the header with zero accounting record; no badge/media disposition
   ledger exists in the delivery path at all.

## Cross-product patterns

- **The disposition ledger fails its own validity check on all three products** (21 / 3 / 16
  unresolved errors respectively), yet in no case does that failure block delivery or the
  `DELIVERED` labeling. This is the single most consequential systemic gap: the tool's own
  preservation proof is broken, and nothing downstream reacts to that.
- **Two of three products ship a direct in-document contradiction** between the API
  reference/capability prose and the Limitations section of the *same file* (3D: NotImplementedError
  methods; BarCode: PNG backend; Note: license/metering/layout-detection stubs).
- **The portfolio-level `RESULTS.md` summary table is not reconciled against per-run evidence.**
  For Note this produces a direct falsehood visible to the product owner (`DELIVERED`/`none`
  against a `reject` verdict); for 3D the same disconnect exists between `RESULTS.md` and
  `validation.json`.
- **Badge/media and code-example dispositions have no dedicated ledger anywhere in the delivery
  path** (`src/readme_agent/commands_poc.py::build_source_disposition_ledger` only tracks
  heading-level units), unlike Aspose's own canonical directories, which ship four separate
  category-specific ledgers (content/structure/code-example/badge) per product.
- **Aspose's own canonical candidates are not spotless either**: their stored example-verification
  runners mark execution-dependent claims `BLOCKED-WITH-REASON: TOOLCHAIN-UNAVAILABLE` rather
  than proving runtime execution, so Aspose calibrates disclosure-of-block, not proof-of-run —
  this audit did not give Aspose a free pass on that basis, and neither should future scoring.

## Causal ownership and repair classification

23 candidate backlog rows across the three products are in `CAUSAL_OWNER_BACKLOG.json`, each
tied to a specific module/function where one was identifiable within the time budget (most
converge on `src/readme_agent/commands_poc.py`'s disposition-ledger and promotion-status logic,
and `src/readme_agent/presentation/verified_template_*` composers). A minority of rows could not
be traced to one exact function in the time available and say so explicitly rather than
guessing — see `causal_module` values beginning `"not found"` or `"likely …, not conclusively
isolated"` in `CANDIDATE_SCORE_MATRIX.json`.

Repair classes recorded per row: most fixes are `deterministic_code` (make the disposition
ledger's fail-closed check actually block delivery, add missing dispositions ledgers, fix the
RESULTS.md/status reconciliation); a smaller set are `qwen_prompt_review` (carry an already-known
stub/no-op fact through to the API reference and limitations prose); none required new
`factual_input` — the facts needed to fix every found gap already exist in this repository's own
evidence (the immediate-predecessor README, source code, or the tool's own fact store).

## Per GOV-014 / backlog-ticket-discipline

These are non-blocking findings from a read-only audit, not fixes. They are logged as open
`BACKLOG-ASPOSE-PARITY-*` rows in `CAUSAL_OWNER_BACKLOG.json` for owner triage; nothing in this
repository was changed to produce this report.

## Known gaps in this audit

- No network/registry verification of the `Mesh.union`/PNG-backend/etc. runtime claims was
  performed beyond static source inspection (consistent with the "no Docker/Qwen" constraint);
  where a claim could only be settled by execution, the per-criterion row says so.
- A handful of `causal_module` fields are marked "not conclusively isolated within the time
  budget" rather than a guessed path — see `CANDIDATE_SCORE_MATRIX.json` for the exact list.
- This audit did not re-verify Aspose.org's own `last-verified.json` hashes against Aspose.org's
  git history beyond checking internal consistency with the sibling `readme.md` on disk.
