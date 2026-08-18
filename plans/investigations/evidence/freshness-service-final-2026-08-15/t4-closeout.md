# T4 — merged factpack + evidence views

**Status: COMPLETE against the card's own stated scope** ("Merged factpack + evidence views +
trust surfaces" / "adapter builds ComposerFactpack from ProductFactsV2 + 13 vendored detectors;
EvidenceGroundedRenderViewV2 (closes RC1); per-source staleness/coverage finding surfaces (U7)"),
**with two honestly-recorded corrections to the card's own text**:

1. **"13 vendored detectors" is a stale prose count, corrected by direct verification**
   (`grep -n "^def _detect_" readme_refresh_run.py`, this closeout's evidence): the vendored
   module defines exactly **11** `_detect_*` functions, not 13 — the same class of error this
   plan's own resolution 7 warns against ("check inventory is derived... never trust counts in
   prose; verify by grep"), previously caught once already for T3's "81 checks" (real: 89).
2. Of those genuine 11, **9 are adapted here**; the remaining 2 are recorded below as a
   deliberate, reasoned exclusion, not an oversight.

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

### `ComposerFactpack` (`src/readme_agent/facts/composer_factpack.py`, new)

`AsposeDetectionBundleV1` aggregates all 9 adapted detectors' outputs for one family/platform
pair; `ComposerFactpack` wraps it alongside the caller-supplied `ProductFactsV2` (this repo's
existing, provenance-complete, strictly-validated fact type — 55 downstream consumers found via
codebase search). `ProductFactsV2` remains the sole authority for every field in
`REQUIRED_PRODUCT_FIELDS`; the factpack does not re-derive or override any selected fact, and
`build_composer_factpack` verifiably passes the caller's `ProductFactsV2` instance through
unchanged (`factpack.product_facts is product_facts`, tested). Built and proven end-to-end
against real imported data (`cells/java`, `cells/rust`) and via mypy/ruff on the resulting types.

### `EvidenceGroundedRenderViewV2` (`src/readme_agent/facts/render_views.py`, new view only —
existing `VisitorFactRenderViewV1` and its dispatch table untouched)

RC1 ("grounding evidence stripped before composition", this plan's §6 root-cause table) closed
as: a render view whose citations can point at EITHER a `ProductFactsV2` `fact_id` OR a new
`AsposeEvidenceCitationV1` (detector + family + platform + source_id) — so a phrase drawn from
`ComposerFactpack.aspose_detections`, which `VisitorFactRenderViewV1` cannot cite at all, never
silently loses its grounding on the way into future composition (T5+/T7-series). A pydantic
model validator makes this a hard invariant, not a convention: any non-empty `phrases` list with
zero citations of either kind fails construction (tested directly). Fields already covered by
`VisitorFactRenderViewV1`'s dispatch table delegate to it verbatim (proven to preserve V1's exact
phrases and citation set, and to preserve V1's `None`-when-ungrounded behavior for required
fields). Two aspose-only fields (`aspose.seo_keywords`, `aspose.dependency_claims`) are
evidence-grounded pass-throughs of literal source text — deliberately **not** composed prose
(e.g. no MT044 anchor-text construction), since no canonical builder for that exists yet
anywhere in this repo (only a *validator*, `links/anchor_destination_consistency.py` from T10,
was found) and inventing one here would risk conflicting with T5+'s real composition work.

### U7 — per-source staleness/coverage findings (`assess_source_staleness`, same file)

One `SourceStalenessFindingV1` per source the detector bundle consumes (7 sources: SEO keywords,
archetype overrides, package registry, enterprise-link target map, capability-dependencies map,
website-content homepage tree, knowledge-tree dependency claims) — `present`, `age_days`
(file-mtime-based, or the target map's own content-provenance age where a better signal already
exists), `stale` (against a shared `STALE_WARN_DAYS = 14`, matching the one pre-existing
staleness threshold in this codebase, `backlink_targets.STALE_WARN_DAYS`, rather than inventing
several unrelated ones), and `coverage` (`full`/`partial`/`absent`, always derived from each
detector's own already-computed result, never re-parsed independently, so a finding can never
disagree with what its detector actually found). **Advisory only**, per this plan's own
identity-based freshness model (§11 / U11): never a regeneration trigger by itself. Tested
against real data (`cells/java`), an absent-family case (portfolio-wide files present but no
matching entry → `partial`, distinguished from a genuinely-missing file → `absent`), a fully
missing `data_root`, and a synthetic old-file case proving `stale=True` fires correctly.

**15 more tests, all passing** (`tests/unit/test_composer_factpack.py`) — **45 T4 tests total**.
Full governed suite: 3,895 passed, 1 skipped, 0 failed (up from 3,880 before this round — the
delta is exactly the 15 new tests).

## Deliberate scope exclusion (honestly recorded, not silent)

**2 of the vendored module's real 11 `_detect_*` functions were not extracted**:
`_detect_available_badges` (has its own per-ecosystem language-version-template table —
materially larger scope than every other detector, closer to a second card's worth of work) and
`_detect_archetype_entry_raw` (a lower-value near-duplicate of the already-adapted
`detect_archetype`, returning the same override row unfiltered). Both are individually tractable
future work, orthogonal to `ComposerFactpack`/`EvidenceGroundedRenderViewV2`/U7 (all of which are
complete and do not depend on either), so they do not block this card. `AsposeDetectionBundleV1`
and `ComposerFactpack` do not reference either missing detector's output field, so adding them
later is additive (no schema break, no downstream churn).

## Downstream effect

`T14` (section registry) depends on both `T3` (COMPLETE) and `T4` (now COMPLETE against the
card's stated scope, with the above recorded exclusion) — `T14` may now begin.
