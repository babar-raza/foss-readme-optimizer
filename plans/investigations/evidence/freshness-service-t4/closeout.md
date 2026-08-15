# T4 — merged factpack + evidence views

**Status: SUBSTANTIAL PROGRESS, not fully complete.** Recorded honestly.

## What is genuinely done and verified

Investigated importing the vendored orchestration module (`readme_refresh_run.py`) wholesale
and found it pulls in `session_identity`, `advisory_lock`, `core.fs` — real orchestration
machinery this repo already owns an equivalent for. Correctly did NOT import that, matching
this plan's own capability-reuse table ("port only detector logic").

Instead, extracted and adapted **9 of the 11** `_detect_*` functions
(`src/readme_agent/facts/aspose_detectors.py`) as standalone, typed (pydantic) functions taking
explicit parameters instead of the vendored module's global `configure()`-injected state:

- `detect_archetype`, `detect_seo_keywords`, `detect_install_info`, `detect_license_file` — all
  tested against the real imported corpus; found and fixed a real type bug (install-info
  `candidate` is a structured dict, not a scalar).
- `detect_enterprise_link` — the MT044 bridge-disclosure rule, proven against a genuine real
  bridge case (`cells/python`'s `python-net` compound segment). Found and fixed a real T1A
  execution gap (`data/backlinks/*.yaml` was authorized but never enumerated) plus a namespace-
  package path bug and a float/int type bug.
- `detect_dev_test_artifacts` — a pure filesystem scan; both of its documented real-world fixes
  (case-insensitive `Agents.md` discovery, `.pytest_cache/` exclusion despite containing "test"
  as a substring) verified working via synthetic fixtures.
- `detect_capability_dependencies` — reads `data/diagram_capability_dependencies.json`; tested
  against a real traced product (`barcode/python`, 4 real pipeline edges) and confirmed the
  `None` ("never traced") vs `()` ("confirmed independent") distinction is preserved, matching
  the vendored logic's own documented contract.
- `detect_homepage_link` — honest scope-limited adaptation: `content/products.aspose.org/` was
  never imported (TD-01's lean-import scope excluded the website-content tree), so `verified` is
  always `False` in this repo today; proven against real data (`cells/java`) that the URL is
  still correctly constructed even though verification can't succeed, and proven via a synthetic
  fixture that `verified` flips `True` once the evidence file is present — confirming this is a
  real, correct scope gap, not a latent bug.
- `detect_dependency_claims` — reads `knowledge/{family}/{platform}/merged/claims.json` +
  `model.yaml`; tested against real data (`cells/rust`, 7 real `kind: dependency` claims among a
  larger mixed-kind set, plus real `repo_sha` regex extraction) and against synthetic fixtures
  for the regex-extraction and malformed-JSON graceful-degradation paths.

**30 tests, all passing** (20 from the first 6 detectors + 10 for these 3).

## What is NOT done (honest gap)

- **2 of 11 detectors not extracted**: `_detect_available_badges` (has its own
  per-ecosystem language-version-template table — materially larger scope than the other
  detectors), `_detect_archetype_entry_raw` (a lower-value near-duplicate of
  `detect_archetype`).
- **No `ComposerFactpack` merge with `ProductFactsV2`** — this repo's own richer fact type was
  not wired to consume these detector outputs.
- **No `EvidenceGroundedRenderViewV2`** (closing RC1) and **no per-source
  staleness/coverage finding surfaces** (U7) — neither attempted.

## Downstream effect

`T14` (section registry) depends on both `T3` (now COMPLETE) and `T4` (still in progress);
`T14` and everything gated behind it remain out of reach until T4 is also complete.
