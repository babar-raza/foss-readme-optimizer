# Q2 verdict: cells-python "API Reference 56 vs 130 public types" (2026-08-18)

The Decision #104 parity review left the root cause explicitly unconfirmed ("extraction gap vs
a more permissive aspose.org definition"). Settled offline against ground truth:

- The real package's curated public export (`aspose/cells_foss/__init__.py` `__all__`) contains
  **63 names** at the current baseline revision.
- Our extracted API facts contain **all 63** of those names (verified by direct membership
  check against the latest cells facts bundle) — **there is no extraction defect**.
- aspose.org's reference index (`content/reference.aspose.org/en/cells/python/_index.md`) lists
  **~130 rows** — deliberately documenting roughly 2× the curated export, including
  module-internal classes (XML loader/writer machinery) that the package does not export.
- The candidate's rendered "56" is therefore a *rendering/selection* choice from our complete
  63-name fact set, not missing knowledge.

## Disposition

Two separable follow-ups, neither an extractor fix:

1. **Rendering completeness (ours):** close the 63-vs-56 gap — the candidate's API Reference
   should carry the full curated export (or exclude with explicit per-name reasons). Same
   change family as the slides `prs.master_theme` terminology loss (see
   `slides-protected-terminology-triage.md`): the composition under-uses the complete fact set.
2. **Parity-bar decision (product-owner):** whether to match aspose.org's broader ~130-name
   inventory (documenting non-exported internals) or stand on the curated `__all__` as the
   verified public surface. The working-condition principle (present only verified public
   claims) supports the curated set; matching aspose.org would need a deliberate policy to
   document internals. Queue for the Decision #104 review lane rather than silently choosing.
