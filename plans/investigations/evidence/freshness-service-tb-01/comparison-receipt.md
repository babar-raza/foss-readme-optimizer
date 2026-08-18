# TB-01 Mermaid diff acceptance — comparison receipt

Diagram: cells/java candidate, `flowchart LR` (post `6587c3251`). Rendered via `mmdc`
(Chromium 152.0.7977.42, freshly installed this session) to `diagram-light.png` (white bg,
default theme) and `diagram-dark.png` (`#1e1e1e` bg, dark theme).

## Structural check (both themes)
- All 6 nodes present: INPUTS/I1, PRODUCT, CORE/C1/C2, OUTPUTS/O1.
- Edges complete: I1→PRODUCT→CORE→O1, C1~~~C2 spacer intact.
- No clipping, no overflow, no truncated labels.
- Subgraph nesting and `classDef` render without Mermaid errors in either theme.

## Readability check
- **Light theme: PASS.** All text high-contrast, fully legible.
- **Dark theme: FINDING.** Subgraph title labels ("Inputs & Formats", "Core Capabilities",
  "Outputs") render at very low contrast against the dark page background — the subgraph
  container styling is not dark-theme-aware. Node content inside the boxes remains legible; only
  the subgraph *titles* are affected. This is a pre-existing characteristic of the shipped
  Mermaid-generation code (`header_visual_mermaid.py` post-`6587c3251`), not introduced by this
  baseline refresh, and fixing it is a product-code change out of this card's scope (refresh
  stale test constants after confirming the underlying diagram change is legitimate). Recorded
  as a candidate BACKLOG item (GOV-014) for a future card, not blocking TB-01.

## Verdict
Diagram-shape change (`block-beta` → `flowchart LR`) is legitimate and structurally sound.
Candidate + document-plan hash constants refreshed to actual, independently-verified values
(re-derived from real pytest runs, NOT copied from any prior claim — see TB-01 fix commit).

## Second refresh (T10, same session) -- a different, unrelated cause

After landing T10's `src/readme_agent/links/anchor_destination_consistency.py`, these same 4
frozen constants (agentic-plan + 3x characterization plan hashes) broke AGAIN --
`document_template_hash()` (`src/readme_agent/readme/document_templates.py:109`) globs
`src/readme_agent/links/*.py` into the document composition contract's fingerprint by design,
so ANY new file in that directory changes it, whether or not the file is semantically about
rendering. This is the correct, intended behavior of that contract-fingerprint mechanism (the
same mechanism this plan's own §11 freshness model relies on) -- not a bug, and not the same
cause as the Mermaid change above. Investigated properly before re-patching: reproduced the
break in both serial and `-n 4` xdist modes (ruled out a parallelism/leak explanation first),
traced it to the exact glob via `grep DOCUMENT_CONTRACT_IMPLEMENTATION_GLOBS`, confirmed the
new values are stable across 2 independent runs, and confirmed each of the 4 values maps to its
own test unambiguously (ran each test individually, not just trusted output ordering). Refreshed
constants a second time to the newly-verified values. Candidate-byte hashes were unaffected both
times (only the plan/agentic-plan hashes, which is exactly what a contract-fingerprint bump
should touch and nothing else).
