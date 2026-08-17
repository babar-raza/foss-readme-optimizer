# Candidate quality gap list: our generated candidates vs. aspose.org's real corpus

Direct, side-by-side comparisons of our own actually-generated, currently-approved candidates
against aspose.org's real `repo-presenter-regen-full` candidate for the *same product*, done
2026-08-17 to find concrete, fixable presentation/content gaps for a future pass. Ongoing —
add a new dated section per candidate reviewed rather than rewriting prior findings.

## PDF-Python (`aspose-pdf-foss/Aspose-PDF-FOSS-for-Python`)

Ours: `runs/readme-poc/aspose-pdf-foss__Aspose-PDF-FOSS-for-Python/537b8273b185.../candidate/README.md`
(current, generated 2026-08-17 during today's post-fix portfolio run).
Theirs: `D:\onedrive\...\aspose.org\reports\repo-presenter-regen-full\pdf\python\readme.md`.

### Real gaps, roughly ranked by impact

1. **Key Capabilities bullets are much thinner than aspose.org's.** Ours: one line per capability
   (e.g. "Render pages to PNG or TIFF - Produce PNG and TIFF image output from individual pages.").
   Theirs: 3-5 dense lines per capability naming multiple specific methods, behaviors, and edge
   cases (e.g. the equivalent bullet covers `Page.render()`/`Page.save_as_image()`, states "no
   third-party rasterization library required," and lists exactly what the renderer honors: real
   glyph outlines, soft masks, blend modes, axial/radial/mesh shadings). **Likely root cause**:
   the claim-accountability gate (see `claim-accountability-blocking-analysis.md`) requires
   whole-claim substring coverage against known fact phrases — the *richer* the claim, the more of
   it needs mechanical backing, so composition is probably trending toward the shortest claim that
   still passes rather than the most informative one. Worth confirming by checking whether a
   richer capability sentence was drafted and then trimmed, or never attempted.
2. **FIXED 2026-08-17.** ~~No dedicated `## Dependencies` section.~~ Ours used to fold dependency
   info into prose inside `## Installation` (a flat "Required runtime dependencies declared in
   pyproject.toml: ..." sentence, plus an "Optional capability" bullet list with no explanation of
   what each extra *does*). Theirs has a full dedicated section with `### Required Package
   Dependencies` / `### Optional Dependencies` subheadings, each dependency getting its own bullet
   with a one-clause explanation of what it enables (e.g. "`uharfbuzz` >=0.37 — enables the
   `text-layout` extra (HarfBuzz-driven complex-text shaping)."). This was a structural,
   template-contract gap — every real aspose.org candidate researched today has this section as
   its own H2. **Fix**: added `"dependencies"` to `TemplateSlot` and `templates/readme/
   repository-presentation-v1.json` (`section_order`/`headings`, `template_version` 1.19.0 →
   1.20.0); `verified_template_draft.py` now composes `dependencies_section` from the
   already-existing `dependency_markdown()` (required, from `python.distribution.
   runtime_dependencies`) and `scenario_dependency_markdown()` (optional, from `installation.
   capability_dependencies`/`installation.optional_extras`) into `### Required Package
   Dependencies` / `### Optional Dependencies` subheadings under a dedicated `## Dependencies`
   slot, instead of merging that text into `## Installation`; `verified_template_provenance.py`'s
   independent verifier updated to match. No new fact extraction was needed — `python.distribution`
   already carried the required-dependency list. Covered by a new regression test,
   `test_dependencies_section_renders_separately_from_installation`, asserting the content now
   lands in `draft.sections["dependencies"]` and no longer appears in `draft.sections
   ["installation"]`. **Follow-on hardening found and fixed the same pass, mirroring the T5-R1
   `api_method_index` precedent (commit `669a227a5`) exactly**: a new template slot isn't just a
   renderer change — `verified_template_provenance.py`'s `_CLAIM_LEVEL_SLOTS` didn't include
   `"dependencies"`, so its content would have silently skipped claim-accountability analysis
   entirely (a real accountability regression vs. when the same text lived inside `installation`,
   which is claim-level); added `"dependencies"` to `_CLAIM_LEVEL_SLOTS`, a canonical-reconstruction
   branch in `_canonical_structural_section`, and the matching canonical-match fact-id fallback
   (mirroring `additional_examples`'s). Separately, the committed `templates/readme/
   section-registry-v2.json` (T14) hand-drifted from the live contract once the new slot existed;
   regenerated via a new `scripts/retrofits/regenerate_section_registry_for_dependencies_slot.py`
   (16 entries now; the 12 previously-`unmapped_section_checks` T3 dependency-heading checks —
   `check_dependency_disposition_reconciliation` etc. — now map cleanly onto the new slot). New
   regression test `test_dependencies_section_receives_exact_h3_lineage_no_orphan_content`
   (mirroring the existing `test_canonical_compiler_h2_and_fact_renderer_h3_have_exact_lineage`)
   proves the independent provenance verifier grounds every claim in the new section against real
   accepted facts, not just that the composer renders the right text. Full unit suite (~3,890
   tests) confirmed no new failures beyond the pre-existing, unrelated baseline (isolated via a
   `git stash` before/after comparison, since one flaky order-dependent test made a naive full-run
   diff misleading). **Attempted but blocked**: real end-to-end re-verification via
   `--bounded-verified-canary` against `aspose-pdf-foss/Aspose-PDF-FOSS-for-Python` (AGENTS.md rule
   15) — hit the pre-existing, already-documented `local_poc` origin-backed state-backend bug in a
   new, concrete way (see the addendum in `local-poc-state-backend-uses-origin-not-local.md`,
   "New concrete manifestation, 2026-08-18"); not worked around. Portfolio-wide coverage impact
   also not yet measured, for the same reason.
3. **API Method Index content is nearly empty (3 methods) vs. aspose.org's comprehensive Detailed
   Member Reference (grouped into ~7 functional areas).** Ours: `Document.load_from`, `Document.
   open_streaming`, `PdfLoadLimits.unlimited` — three methods, no grouping. Theirs: a full
   per-area breakdown (Document Lifecycle, Pages And Content, Text Extraction And Editing, Forms
   And Annotations, Security And Signatures, Low-Code Plugins, Fonts) with real method signatures
   throughout. Given `detect_api_public_surface` (today's fix) already resolves real per-method
   data (`ApiSurfaceClassV1.methods`/`.properties`, confirmed populated in `composer_factpack.py`),
   this looks like a rendering/selection gap downstream of the fact, not a missing-data gap — the
   presentation layer isn't yet drawing on the richer method data the fact now carries. **Note**:
   this is about content *richness* only — the section's *placement* as its own top-level H2 (as
   opposed to nesting inside the collapsed API Reference block) is deliberate, tested design (see
   correction under 3D-Python/Slides-Python below), not a gap.
4. **Documentation and Resources is thin (2 bullets: API reference + issue link).** Real
   aspose.org candidates typically also link a getting-started guide and a how-to/FAQ page
   (`docs.aspose.org/pdf/python/`, `kb.aspose.org/pdf/python/`). Possibly correct-and-intentional
   if those specific pages don't exist for this fork (the system should never link a URL it can't
   verify) — worth confirming whether the gap is "correctly withheld, unverified" or "never
   attempted."
5. **Intro paragraph's second sentence is near-content-free.** "It is designed for developers
   using Python." is close to tautological for a Python library and doesn't match aspose.org's
   practice of using every intro sentence to carry real information (license terms, Python version
   floor, `py.typed` marker, core dependency count, maturity/alpha status). Small, cheap fix
   opportunity if there's a template slot generating filler when no better claim was available.
6. **Enterprise-edition paragraph doesn't enumerate specific added capabilities.** Ours: "For
   requirements beyond the FOSS scope described above, explore the full-featured Aspose.PDF
   Enterprise Edition." Aspose.org's convention (documented in `aspose-corpus-contract-synthesis.
   md` §3) is always "these limitations don't apply to [Enterprise Edition], which adds X, Y, Z" —
   a direct, itemized resolution of the specific limitations just listed. Ours states the pointer
   but not the payoff.
7. **Badge set diverges without an obvious reason.** Ours: Version, Platform, Requires, License,
   Contributors (5). Theirs: CI, Python 3.11+, License (3). Two specific differences worth
   checking: (a) ours has no CI badge even though this repo has a real `.github/workflows/ci.yml`
   (confirmed cross-referencing the Development and Testing section, which lists CI-relevant test
   files) — a real, verifiable badge our system isn't adding; (b) ours adds "Version: 0.1.0a0" and
   "Platform: Python" badges aspose.org's convention doesn't use anywhere in the 31-candidate
   corpus — not wrong, just off-template.

### What's genuinely at parity or better

- **API Reference type-table coverage is now excellent** (174 types across 18 real namespaces,
  correctly grouped, real descriptions) — this is the direct, confirmed payoff of today's
  `detect_api_public_surface` fix and is comparable in rigor to aspose.org's own candidate.
- Installation, Quick Start, and Additional Examples sections are structurally sound and roughly
  comparable in content depth.
- The `## Security` section (a real, present section addressing untrusted-PDF-input handling) is a
  genuine plus not templated as prominently in aspose.org's own candidate.

## 3D-Python (`aspose-3d-foss/Aspose.3D-FOSS-for-Python`) — cross-check, confirms systemic pattern

Ours: `runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/ee05c1ba9153.../candidate/README.md`
(current, generated 2026-08-17 during today's post-fix portfolio run, 98KB).

Quick structural check against the same gap categories found in PDF-Python — **two of three
confirmed systemic, one corrected as a false alarm**:

- **FIXED 2026-08-17 (was: no dedicated `## Dependencies` section)** — section list used to jump
  `## Installation` → `## Quick Start` directly, same as PDF-Python. Not product-specific; see the
  fix writeup under PDF-Python item 2 above.
- **CORRECTED, not a gap: `## API Method Index` as its own top-level section.**
  `verified_template_api_method_index.py`'s own docstring and the test
  `test_api_reference_uses_complete_catalog_without_dumping_every_member_row` confirm the narrow,
  maintainer-mentioned-methods-only scope and the separate top-level placement are both deliberate,
  tested design — not an accidental deviation from aspose.org's nested-inside-API-Reference layout.
  Struck from the gap list; the only real remaining API Method Index concern is content richness
  (see PDF-Python item 3 above).
- **Key Capabilities bullets are thin** — three consecutive one-line bold-lead bullets (e.g.
  "**Create 3D primitives including Box, Cylinder, Sphere...** - Build reusable scene geometry
  from the listed primitive types."), matching PDF-Python's pattern exactly.

**One sharper insight from this cross-check**: immediately after the three thin, freshly-composed
bullets, a fourth bullet appears that's genuinely rich and specific — "Export the same `Scene`
model back out to OBJ, STL, GLTF/GLB, or 3MF with `Scene.save(...)` (COLLADA import is supported;
COLLADA export is not currently reachable through the public API — see Scope and limitations)."
This reads like preserved/bound *original source* prose (it cites a specific real behavioral
caveat, not just a capability name), not synthesized capability text. **This narrows gap #1**:
the thinness isn't a blanket capability-writing weakness — it's specific to *freshly-composed*
capability bullets (ones with no original-README claim to bind to and preserve), consistent with
the claim-accountability coverage mechanism trending toward the shortest claim that still clears
its bar when there's no existing rich source text to anchor to.

## Slides-Python — third confirmation, same two structural gaps

Quick structural check only (`runs/readme-poc/aspose-slides-foss__Aspose.Slides-FOSS-for-Python/
ffaf6355.../candidate/README.md`, the last approved candidate before today's fresh upstream commit
moved this repo to a new, currently-blocked revision — see the main final report). Same section
list shape as the other two: `## Installation` → `## Quick Start` directly (**Dependencies gap,
now FIXED 2026-08-17** — see PDF-Python item 2), and `## API Method Index` as its own top-level
section (**corrected as intentional design, not a gap** — see 3D-Python above). Three for three on
the Dependencies gap confirms it was pipeline-wide, not product-specific noise, and it was the
highest-confidence, most tractable item on this list — a missing section generator, not a
fact-availability or claim-accountability question.

## Next candidates to review (not yet done)

- Once any non-Python candidate reaches `AGENT_APPROVED` for the first time (none has yet — see
  the main final report), compare it against its aspose.org sibling too. Everything above is
  Python-only so far; whether these same two structural gaps (and the thin-bullet pattern) also
  hold for other platforms is still an open question.
- `aspose-words-foss/Aspose.Words-FOSS-for-Python` vs `words/python/readme.md`
- Once any non-Python candidate reaches `AGENT_APPROVED` for the first time, compare it against its
  aspose.org sibling too — this file has no cross-platform comparison yet.
