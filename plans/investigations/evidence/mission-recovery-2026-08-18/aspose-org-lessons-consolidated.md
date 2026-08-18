# Consolidated aspose.org investigation — 2026-08-19 (operator-directed)

Directive: "investigate how aspose.org solved all those problems which you are not able to
solve... there is nothing blocked there so learn from it and move forward." This is the
consolidated record of what was found, fixed, and learned across four rounds of direct
investigation into aspose.org's real, live `reports/repo-presenter-regen-full/**` corpus.

## Lesson 1 (landed, live-proven): existence-only evidence for named fixtures

`code-example-dispositions.json` for note-python (unit c0001) verifies
`doc = Document("SimpleTable.one")` as `verified_against_source`/`clone_cache_path` citing
`testfiles/SimpleTable.one` — **with no `evidence_quote` field at all.** The file genuinely
exists (confirmed in both clone caches). Root cause on our side: `repository_file_listing()`
filtered to a source-extension allowlist that hid this real fixture from the model entirely.
Fixed (`04ad3e669`): list every real file (minus VCS/cache/build noise); a claim naming a real,
existing file it can't quote (binary fixture) corroborates by existence + the claim text
already naming that exact filename. Live-proven: the model now correctly cites
`testfiles/SimpleTable.one` and corroboration accepts it — closing gate 1 for this exact claim.

## Lesson 2 (delegated, in flight): API-shape evidence via `evidence_note`

barcode-python unit u0017 (the `generate()` symbology entry-point bullet) verifies via
`evidence_note: "generate(symbology, data, *, encode=None, render=None) confirmed public."` —
a structured confirmation against a real function signature, never a text quote. Confirmed the
same pattern generalizes (font-python u0004/u0008/u0027, same shape). We already extract this
exact fact (`ApiSurfaceMemberV1.signature`); the gap is `claim_disposition_check` has no path
to consult it. Design spec written and delegated to an isolated worktree lane
(`mission-recovery/api-surface-evidence`) — in progress.

## Lesson 3 (architectural, most important): disposition IS the render

Investigating why note-python stayed blocked even after lesson 1 fixed its exact claim
surfaced the deepest lesson: **our pipeline has two claim-accountability gates, and only the
first is LLM-assisted.** `specialists/readme_factuality.py::evaluate_candidate_factuality()`
(gate 2, mandatory, always runs after gate 1 passes) rebuilds the document plan a second time
WITHOUT `llm_disposition_client`/`repository_root`/`disposition_ratchet_path` — a deliberate,
independent, LLM-free re-verification (matching VER-001: never trust the model's own say-so).
**A claim accepted only through the LLM-disposition path always passes gate 1 and always
re-derives as unaccounted-for at gate 2** — confirmed live: note's claim showed
`claim_conflicts=0` at gate 1 and `protected_losses=1` at gate 2 citing the identical claim id.

Cross-checking aspose.org's own Key Capabilities dispositions for slides-python confirmed
exactly why they never hit this problem: **their disposition and their render are the same
act.** When a unit is `merged_reframed`/`merged_verbatim`, the reframed text — dense with real
class/property/method names — IS what ships in `readme.md`. There is no separate "the LLM
approved this claim" step floating free of what the candidate actually contains. Slides'
`u0010` (Themes/`master_theme`) is `disposition: excluded` precisely BECAUSE the real content
(`ColorScheme`, `FontScheme`, `Theme`, `Presentation.master_theme`, `MasterThemeManager`) is
already woven, richly, into their Key Capabilities bullet — satisfying any later mechanical
re-check trivially, by construction.

**This directly explains every outcome observed this session**: page-python (Lane A, pure
deterministic rendering) reached full `AGENT_APPROVED` because the claim's assertion is
literally, mechanically present in the candidate. barcode/note (E5, LLM disposition alone)
never reached full approval, because gate 2 can't see an LLM's classification, only text.

## What this means going forward

E5 (LLM disposition) is real and useful — as a **triage/narrowing tool**, not a standalone
closure mechanism. The single reliable path to full closure, matching aspose.org's own
architecture exactly, is: **make the composed candidate's real content dense and specific
enough (real class/property/method names, real examples) that original claims become
genuinely, mechanically redundant** — Lane A/B's rendering-fix pattern, generalized. This also
reframes Decision #104's "thin Key Capabilities" finding (Q1) as the SAME defect as the
claim-accountability blocking pattern (S1), not a separate quality issue — both are downstream
of composition under-using the fact set that's already fully extracted and available.

## Immediate next steps (queued, not yet done)

1. Verify the API-surface-evidence lane against BOTH gates once it lands (per lesson 3) — if it
   only clears gate 1, it needs a companion Lane-B-style composition enrichment to fully close
   barcode-python.
2. note-python's actual completion requires composing the SimpleTable.one example (or a
   reframed equivalent) into the rendered Quick Start section — a genuine composition change,
   not a disposition acceptance. Scoped but not implemented this round.
3. `document_validation.py`'s `redundant_with_candidate` mechanical path (used identically at
   both gates, since gate 2 reuses the same renderer) is the real, LLM-free lever — richer
   Key-Capabilities/API-Reference composition is what makes claims redundant BY CONSTRUCTION,
   the same way aspose.org's own dense bullets do.
