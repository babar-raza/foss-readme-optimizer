# T4 — merged factpack + evidence views

**Status: SUBSTANTIAL PROGRESS, not fully complete.** Recorded honestly.

## What is genuinely done and verified

Investigated importing the vendored orchestration module (`readme_refresh_run.py`) wholesale
and found it pulls in `session_identity`, `advisory_lock`, `core.fs` — real orchestration
machinery (locking, atomic writes, session identity) this repo already owns an equivalent for.
Correctly did NOT import that, matching this plan's own capability-reuse table ("port only
detector logic").

Instead, extracted and adapted **4 of the 11** `_detect_*` functions
(`src/readme_agent/facts/aspose_detectors.py`) as standalone, typed (pydantic) functions taking
an explicit `data_root: Path` parameter instead of the vendored module's global
`configure()`-injected `_repo_root` state:

- `detect_archetype` — tested against real `data/imported/data/diagram_archetypes.json`.
- `detect_seo_keywords` — tested against real `data/imported/keywords/cells.json`, including
  the platform-then-family fallback (found real data has entries for all 7 real platforms, so
  the fallback test uses a genuinely-absent hypothetical platform to exercise it for real).
- `detect_install_info` — tested against real `data/imported/data/package_registry.json`;
  **found and fixed a real type mismatch**: the vendored code's `candidate` field is an untyped
  dict in practice (Maven group_id/artifact_id/version/repo_sha), not the scalar my first draft
  assumed — caught immediately by the pydantic model raising on the real data, not silently
  accepted.
- `detect_license_file` — the widened MIT-preamble match (the real TC-HARDEN-20 fix) preserved
  verbatim and proven with both a positive fixture (`"The MIT License (MIT)"` preamble) and a
  negative one (Apache-2.0 correctly excluded).

**10 tests, all passing**, testing against the real imported corpus wherever real data exists
(only `detect_license_file`'s positive/negative cases use synthetic fixtures, since no real
product clone-cache exists in this repo).

## What is NOT done (honest gap)

- **7 of 11 detectors not extracted**: `_detect_capability_dependencies`,
  `_detect_enterprise_link`, `_detect_homepage_link`, `_detect_available_badges` (has its own
  language-version-template table), `_detect_dependency_claims`, `_detect_dev_test_artifacts`,
  `_detect_archetype_entry_raw`.
- **No `ComposerFactpack` merge with `ProductFactsV2`** — this repo's own richer fact type was
  not wired to consume these detector outputs.
- **No `EvidenceGroundedRenderViewV2`** (closing RC1) and **no per-source
  staleness/coverage finding surfaces** (U7) — neither attempted.

## Downstream effect

`T14` (section registry) depends on both `T3` and `T4`; neither is complete, so `T14` and
everything gated behind it remain out of reach this session.
