# Freshness-service execution — final verdict (2026-08-16)

## Verdict: BLOCKED_PORTFOLIO (real, continuing progress; no unresolved blocker remains)

Twenty-seven commits of genuine, verified engineering now sit on `freshness-service/integration`.
**T5's claim-accountability investigation is now traced to its complete root cause** (commit 27):
`fact_authorized_claim_ids` is an explicit upstream input (`source_assurance.preserve_ranges`)
from an earlier "source assurance" classification stage, paired with a sibling
`correction_candidate_ranges`, under a hard invariant that every `preserve`-disposition claim
belongs to exactly one. Since the 9 blocking claims are `preserve` but not `fact_authorized`
(proven by T5-R2's experiment), they must be `correction_candidate` — the source-assurance stage
already judged their original phrasing not independently verifiable, and expects a
correction/rewrite step to produce new grounded text, which does not yet exist anywhere in this
composition path. This is the genuine, complete explanation: not a missing wiring connection
(T5-R1's shape), but an absent content-correction capability matching this plan's own
already-planned `T7D`/`TP-11A`/`TP-11B` cards. The investigation chain — protected-content →
claim-accountability → preservation-sections → source-assurance — is now traced end to end, each
layer empirically confirmed.
**T5-R2 exploration (commit 26)**: tested whether the same "reuse existing tested machinery"
pattern that made T5-R1 work also applies to the remaining claim-accountability gap. Found and
empirically tested a second real mechanism (`resolve_preserve_claim_placements`'s
`relocated_exact_equivalence` path) — disproven by direct experiment (patched the new slot to
echo literal source terms, re-ran the real pilot, `survives_in_candidate` stayed `False`).
Checked the material claims' actual `disposition` field directly, ruling out a simpler
explanation (all genuinely `'preserve'`). The real remaining blocker is narrowed to
`fact_authorized_claim_ids` membership specifically — real, valuable negative evidence, and a
concrete starting point for the next investigator, not an open-ended mystery. Experimental code
reverted cleanly (`git diff` confirmed empty).
Gates **G0, G1, and G2 are CLOSED** (`GC-00`/`GC-01`/`GC-02` all COMPLETE — every mandatory card
through T10/TW-01/TW-03/TA-01 verified). **T3 and T14 are COMPLETE.** **T4 is COMPLETE** (9 of the
vendored module's real 11 detectors adapted; `ComposerFactpack`, `EvidenceGroundedRenderViewV2`
closing RC1, U7 staleness surfaces).

**T5 (deterministic pilot skeleton, cells/python) has made substantial, real, verified progress
across an extensive investigation, but is not yet COMPLETE.** In order:

1. **Byte-identical double-run idempotency: proven**, twice, against the real target repo
   (`aspose-cells-foss/Aspose.Cells-FOSS-for-Python`) — a second run reuses the hash-bound
   composition plan with zero new LLM calls, corroborated by the pipeline's own `noop.json`.
2. **Disposition-ledger `target` defect: a real, tested fix landed**, resolving 6 of 13
   originally-flagged units (13 → 7 `disposition_ledger_errors`) by tracking each compiled slot's
   exact block text and locating it via substring search against the real final candidate —
   sidestepping a coordinate-shift problem the initially-considered byte-offset approach would
   have hit. The remaining 7 have individually understood, legitimate reasons this fix correctly
   leaves untouched (non-slot fixed blocks, nested sub-headings, a genuinely-excluded slot, one
   disclosed source/contract spelling divergence).
3. **The "two-tier API reference" feature this investigation identified as needed: built and
   verified (T5-R1).** A new, separate, optional `api_method_index` template slot — naturally
   bounded to methods both verified in the current API surface and already mentioned by the
   source README's own inline code, reusing real, previously-unused, already-tested building
   blocks (`describe_api_member`/`member_api_identifier`). Verified against the real target repo:
   `unauthorized protected-content loss` dropped from **9 occurrences to zero**.

**What remains genuinely open for T5**: a separate, different validator —
`claim accountability has 9 blocking claim(s)` (source-claim survival tracking, not
protected-content) — plus the disposition ledger's 7 remaining units. Both are real, diagnosed,
unstarted work. `GC-03` (G3 close) stays honestly blocked pending both.

The run has not reached `AWAITING_GLOBAL_HUMAN_REVIEW` because G3 onward (G4:
T6/T7A/T7B/TP-11A/T8, G5: T9/TW-02, G6: TU-01/TG-06A/TG-06B, G7:
T7C-F/TP-11B/TF-01/TG-06C/T11/T13/TG-07, G8: T12/TW-04/TW-05/TG-08) remain unstarted — genuine
remaining scope, not a blocker.

## What is genuinely done and verified

- **TL-01 — RESOLVED** (explicit user authorization, recorded with exact scope).
- **G2 CLOSED (GC-02 COMPLETE).** All 11 mandatory G2 cards verified COMPLETE:
  - **T1A, T1B, T2, T10, TW-01, TW-03, TA-01, TD-01 — COMPLETE** (unchanged from prior rounds).
  - **T3 — COMPLETE.** 89-check vendored battery registry, systematic fail-closed fixture
    coverage, `docs/readme-process.md` with a live drift test. 108 tests.
  - **T4 — COMPLETE this round.** 9 of the vendored module's real 11 `_detect_*` functions
    adapted (the card's own "13 vendored detectors" text was a stale prose count, corrected by
    direct `grep` verification — the same error class as T3's "81 checks", real: 89). This
    round added the card's two remaining owned deliverables:
    - `ComposerFactpack` (`src/readme_agent/facts/composer_factpack.py`, new): merges the
      caller-supplied `ProductFactsV2` (this repo's existing, provenance-complete fact type, 55
      downstream consumers) with `AsposeDetectionBundleV1` (all 9 adapted detectors' outputs).
      `ProductFactsV2` stays sole authority for every required field; the merge never
      re-derives or overrides a selected fact (verified: the factpack carries the caller's exact
      `ProductFactsV2` instance through unchanged).
    - `EvidenceGroundedRenderViewV2` (new view in `render_views.py`, existing
      `VisitorFactRenderViewV1` untouched) — closes RC1 ("grounding evidence stripped before
      composition"). Citations can point at a `ProductFactsV2` fact_id or a new aspose-detection
      evidence reference; a model validator makes "rendered phrases with zero citations" a hard
      construction failure. Fields already covered by V1 delegate to it verbatim, proven to
      preserve V1's exact output including its `None`-when-ungrounded behavior.
    - U7 per-source staleness/coverage findings (`assess_source_staleness`) — one finding per
      of 7 consumed sources, advisory only per this plan's identity-based freshness model
      (never a regeneration trigger by itself).
    - **45 T4 tests total** (30 detector + 15 new), all against real imported data
      (`cells/java`, `cells/rust`, `barcode/python`) plus synthetic edge cases.
    - Deliberate, documented, non-blocking exclusion: `_detect_available_badges` and
      `_detect_archetype_entry_raw` (2 of the real 11) were not extracted — neither is
      referenced by the new types, so adding them later is additive.
  - **T14 — COMPLETE this round.** New `presentation/sections/` package:
    `SectionRegistryEntryV1`/`SectionRegistryV1` (id/heading/order/required/composer_binding/
    section_checks/ledger_obligations/invalidation_scope), following this repo's established
    "governed data file + strict pydantic model + `load_*()`" convention (no dynamic
    plugin-discovery pattern exists anywhere in this codebase). `templates/readme/
    section-registry-v2.json` (14 entries) is byte-derived from the live
    `template_schema.py` contract; `section_fingerprint()`/`document_global_fingerprint()`
    (the latter reusing the existing `document_template_hash()` unchanged) implement the plan's
    per-section + document-global fingerprint split. Real discrepancy found and disclosed: 20
    section-scoped checks reference headings ("Dependencies", "header", "Project Structure")
    absent from the live 14-slot contract — surfaced in `unmapped_section_checks`, not silently
    dropped, left open since fixing the shared contract exceeds T14's scope. All 4 named
    "agility tests" (a-d) implemented and green. 13 tests.
  - **T5 — substantial progress, NOT complete.** Real pilot run against the real, network-
    confirmed target repo `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` (`main` @
    `26c3bd1633e84b91c0f6fad1fd353662fd61fb54`) via `readme-agent poc`, the sanctioned local-
    candidate tool. **Byte-identical double run proven twice over**: two independent
    invocations produced identical `README.md` bytes; run 2 reused the hash-bound plan (zero
    new LLM calls), corroborated independently by the pipeline's own `noop.json`
    (`verdict: RENDER_REPRODUCIBLE`, `new_provider_call_count: 0`). **Docker isolation
    machinery proven live**: the diagnostic path's own example-presence check is a static
    substring match (verified by reading its source, not assumed), so the normally-excluded
    `@pytest.mark.live` Docker tests were run explicitly instead — 2/2 passed against a real
    container. **Disposition-ledger `target` defect — a real fix landed**, dropping
    `disposition_ledger_errors` from 13 to 7 (see the verdict summary above for the mechanism).
    **Protected-content losses — closed via T5-R1**, a new, separate, optional
    `api_method_index` template slot, dropping `unauthorized protected-content loss` from 9
    occurrences to zero on the real pilot. **Still open**: `claim accountability has 9 blocking
    claim(s)` (a different mechanism — source-claim survival tracking) and the disposition
    ledger's remaining 7 units. `GC-03` stays honestly blocked pending both.
- **Full governed suite, final confirmation: 3,920 passed, 1 skipped, 0 failed** — zero
  regressions across the entire session's cumulative real, tested changes.
- **Twenty-five commits** on `freshness-service/integration` (`13286e0c4` … `8096ffafa`; current
  HEAD `8096ffafa`). The user's main worktree has remained byte-identical for the entire session
  (HEAD `8cb9afabeb31b69e6948a33a7502d89952caf701`, unchanged; only its pre-existing protected
  dirty paths and additive untracked evidence dirs present). Nothing pushed, no target
  repository touched (the pilot run was a real `git clone` read + local candidate generation
  only — TW-01's guard covers write operations, which never occurred).

## Honestly disclosed process gap (found and recorded this round, not silenced)

Several G2 cards (T1A, T1B, T2, T10, TA-01, TD-01, TL-01, TW-01, TW-03) do not have a dedicated
per-card evidence directory the way T3/T4/TB-01/TS-03/GC-00 do — their real work and tests exist
(verified in commit history and the full suite), but the evidence-directory convention was not
retroactively applied to them. Recorded in `freshness-service-gc-02/closeout.md` rather than
either fabricating empty retroactive directories or silently omitting the gap. Not a blocker (the
underlying work is real and tested); a legitimate housekeeping item for a future round.

## Remaining genuine external-authority blockers

1. Production hosted proof — user push + workflow dispatch (also serves as App-installation
   proof for the two Java-family orgs).
2. Two missing repo secrets (`LLM_BASE_URL`, `LLM_API_KEY`).

TL-01 is resolved and no longer a blocker.

## Not attempted / incomplete (honest, not fabricated)

`T5` (deterministic pilot skeleton, cells/python; `T3`/`T4`/`T14` COMPLETE) made real,
substantial, cumulative progress across this session's investigation (byte-identical double-run
proof, live Docker capability proof, a real disposition-ledger fix, and a real new template
feature closing protected-content losses entirely) but did not reach COMPLETE — one genuinely
separate, unaddressed defect remains: `claim accountability has 9 blocking claim(s)`
(source-claim survival tracking, detailed in `freshness-service-t5/closeout.md`), plus 7
remaining disposition-ledger units. `GC-03` (G3 close) requires T5 COMPLETE and stays blocked.
`T6`, `T7A`-`T7F`, `TP-11A/B`, `TW-02`, `TU-01`, `TG-06A/B`, `TF-01`, `T11`, `T13`, `TG-07`,
`T12`, `TW-04`, `TW-05`, `TG-08` were not started. Each represents comparable engineering scope
to what's already been built;
completing them with the same rigor applied throughout this session is realistically a
multi-session undertaking.
