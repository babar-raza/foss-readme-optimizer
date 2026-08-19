# Upstream-drift coverage gap: vendored pipeline scripts are untracked

`scripts/data-refresh/detect_aspose_upstream_drift.py` (Phase-3 machinery, 2026-08-18) only
compares `data/imported/**` (knowledge bundles, registries, keywords) against the live
aspose.org upstream. Re-run today (2026-08-19) confirms the already-known gap persists and
upstream continues to move: `drift-20260819-054518.json` — upstream HEAD `6297b36f99f8`
(different from 08-18's `4f991f7a03c4`, so real upstream commits landed in between) — still
shows the identical **18/18 knowledge bundles drifted, 28/28 data files drifted** as 08-18's
report. Not a new finding; re-confirmed with fresh evidence and a newer upstream HEAD.

## New finding: the detector has no coverage for `src/readme_agent/vendored_asposeorg/**`

That directory is a second, entirely separate import surface — real Python implementation
vendored directly from `D:/onedrive/Documents/GitHub/aspose.org/scripts/pipeline/**` (the
`readme-refresh` skill's own check battery and dependency extractor), actively imported by
`validation/aspose_checks/__init__.py` (T3, wraps every vendored `check_*` function) and
`facts/aspose_detectors.py` — not vestigial, not dead code. The detector script never looks at
this directory at all.

Manual `diff -rq` against the live upstream tree found real, substantial divergence:

- `commands/foss/dependency_extract.py`: upstream is 975 lines, our vendored copy 777 — a
  near-total rewrite. Upstream's current docstring documents a **real, dated incident** (MT041,
  2026-08-14, "Thirty-First incident"): a generated cells/rust README claimed "no external
  runtime... needed" while the product's own `Cargo.toml` declares 7 real runtime crates — a
  same-document contradiction. Upstream's fix consumes real `kind: "dependency"` claims from
  `knowledge/{family}/{platform}/merged/claims.json` that nothing previously read. Whether our
  vendored copy predates this fix (and so is exposed to the same class of bug) or diverged for
  a different, deliberate local reason has **not been determined** — this note stops at
  detection, per the same discipline the existing drift tool documents for data files.
- `commands/foss/readme_refresh_checks.py` also differs (this is the exact module T3 wraps
  mechanically for every `check_*` function — our whole vendored check battery).
- `commands/foss/readme_refresh_run.py` also differs.
- `lib/api_table_dupes.py`, `lib/backlink_targets.py` also differ.
- Upstream has gained `commands/foss/upstream_issue_workflow.py` entirely — not vendored at
  all, unclassified.
- The vendoring is already deliberately narrow (confirmed: upstream's `commands/` also has
  `content/`, `diagnostics/`, `enrichment/`, `governance/`, `healing/`, `kilocode/`,
  `knowledge/`, `launch/`, `migration/`, `ops/`, `websites/`, `DOMAINS.md` — none vendored,
  correctly, per "do not port unrelated Aspose.org website machinery").

## Directly relevant to today's work

One drifted data file, `api_reference_class_exclusions.json` (impact: "API Reference
exclusions"), is the upstream sibling of the exact `presentation_exclusions` mechanism this
session's `verified_template_api_reference.py` fix (2026-08-19, Q2 closure) reads from
`api.public_surface.coordinate_catalog.presentation_exclusions` to decide which extracted
classes are real public surface vs. internal noise.

**Checked directly**: `diff` against `D:/onedrive/.../aspose.org/data/api_reference_class_exclusions.json`
shows byte-identical content (all 3 font-python entries match exactly; the reported "drift" is
CRLF-vs-LF line endings only). Confirms this file was not the cause of anything this session's
API-reference fix touched, and rules out the hypothesis that upstream had already excluded/
included something differently for the repos this session worked with. Font-python is the only
family represented in this file at all — it carries no cells-python entries, consistent with
`FormulaEvaluator` (cells-python) not being an `presentation_exclusions` question in the first
place: it is genuinely absent from the top-level `aspose.cells_foss` package's own exports
(exported only at the `aspose.cells_foss.formula_evaluator` submodule level), not wrongly
excluded by either side's exclusion list.

## Disposition

Detection only, matching the existing tool's own stated policy ("Applying any update is a
separate, deliberate step that must run the parity suites for every impacted concern and must
never overwrite local Qwen-specific adaptations blindly"). Not attempting a reconciliation here
— the existing 28-file/18-bundle data drift alone is already a properly scoped, undertaken-later
initiative; the vendored-scripts gap found here should be triaged the same way, ideally by
extending `detect_aspose_upstream_drift.py`'s coverage to `vendored_asposeorg/**` with its own
semantic-impact classification, rather than a one-off manual diff each time.

## Next diagnostic (queued, not started)

1. Extend the detector's scope (or add a sibling script) to hash-compare
   `src/readme_agent/vendored_asposeorg/**` against the live upstream tree, same pattern as the
   existing `data/imported/**` comparison.
2. Diff `api_reference_class_exclusions.json` (ours vs. upstream) specifically, since it is
   directly load-bearing for today's Q2 fix's correctness.
3. Determine whether `dependency_extract.py`'s MT041 fix (real manifest-file dependency
   consumption) is already present in our vendored copy under a different shape, or genuinely
   missing — before assuming either direction.
