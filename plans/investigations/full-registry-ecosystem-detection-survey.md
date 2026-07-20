# Full-Registry Ecosystem-Detection Survey — Wave 3 hardening

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: `tools/survey_full_registry_ecosystem_detection.py` — clones the baseline of all 25
> real `data/products.json` entries (every mode, per decision 24/`PIL-011`'s research-scope
> carve-out; read-only `clone_baseline()` throughout, never a work clone, never a push) and runs
> `profile.detector.build_profile()` against each, real repo, real filesystem.

## Why this exists

Wave 3 shipped with all six `ecosystems/*.py` platform parsers proven against synthetic
fixtures and one live capability test (a single Java repo). The user asked for the whole
registry to be used to prove, validate, and harden that work — not just re-confirm the three
already-known-good Java pilots. This is that: the first time the five newly-added platforms
(Python, .NET, TypeScript, Go, C++) were run against real, previously-unseen data at scale.

## First run: 2 real bugs found, not zero

| # | Repo | Finding |
|---|---|---|
| 1 | `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` | **Crash**: `AttributeError: 'list' object has no attribute 'get'`. Its `pyproject.toml` uses `[tool.setuptools]` `packages = [...]` (a flat list) — the ported code only handled the nested `[tool.setuptools.packages.find]` `include = [...]` shape aspose.org's reference happened to use for its own tested repos. |
| 2 | Every `.NET` repo (5/5), plus `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` | **Systemic miss**: `expected_platform_detected=False` for 100% of `.NET` entries and 1 `cpp` entry. Root cause: `inspection/file_inventory.py`'s `_find_manifest_paths()` only checked the repo root (`Path.glob()` for the `.csproj` wildcard, direct `repo_path / pattern` existence check for literal filenames like `CMakeLists.txt`) — but every real `.NET` repo in this registry puts its `.csproj` under `src/<Project>/`, and this `cpp` repo puts its `CMakeLists.txt` under `<Project>/`. Neither is a root-level file. This is not a `.NET`-only bug — it's a detection-design gap that happened to be invisible for the Java/Python repos already checked only because *their* manifests happen to sit at the root. |

Full raw results: `plans/investigations/evidence/full-registry-ecosystem-survey/survey-results.json`
(first run overwritten by the confirming rerun below — the failure signatures are preserved in
this document and in the regression tests that now assert the fixed behavior).

## Fixes

1. **`ecosystems/python.py`**: `canonical_package` extraction now checks both the nested
   `packages.find.include` shape and the flat `packages = [...]` shape, `isinstance`-guarded
   rather than assuming one. Regression test:
   `tests/unit/test_ecosystems.py::TestPythonParser::test_extracts_canonical_package_from_flat_packages_list`.
2. **`inspection/file_inventory.py`**: `_find_manifest_paths()` rewritten from N root-only
   checks to **one bounded `os.walk`** across the whole tree, skipping common noise directories
   (`.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.tox`, `dist`, `build`, `target`).
   Deliberately a single walk, not one `rglob` per (ecosystem, pattern) pair — an earlier design
   sketch using per-pattern `rglob` would have made the tree-walk cost scale with the number of
   registered ecosystems (12 patterns across 6 platforms today), multiplying the exact
   performance problem the survey's own timing data (`aspose-page-foss` at ~175–185s, a
   ~1 GB / 2500-file repo) already showed matters. The single-walk version short-circuits once
   every registered `(ecosystem, pattern)` has a match or the tree is exhausted. Regression
   tests: `tests/unit/test_inspection.py::TestFileInventoryManifests::test_finds_nested_csproj_not_just_root`,
   `::test_finds_nested_cmakelists_not_just_root`, `::test_skips_noise_directories`.
3. **`profile/detector.py`**: `CMakePresets.json` / `CMakeUserPresets.json` added to the known-
   non-manifest exclusion list — a real CMake companion config file the survey found correctly
   flagged as `unresolved` (not a bug, `ECO-003` working as designed) but worth quieting since
   it's a well-known, common file, not a genuine signal of an unsupported ecosystem.

## Confirming rerun: 25/25 clean

```
25/25 repos profiled without a crash
```

Every entry now shows `expected_platform_detected=True` (or `None` for platforms outside the
`java`/`net`/`python`/`typescript`/`go`/`cpp` set — none exist in this registry today) and the
Python crash is gone. This confirming run still reported `unresolved manifests recorded for 1
repos` — `aspose-email-foss/Aspose.Email-FOSS-for-Cpp` → `['CMakePresets.json']` — because the
`CMakePresets.json` exclusion (fix 3 below) was added *after* this run, not before it; re-checked
directly against the same already-cloned repo afterward (not a fresh assumption):
`build_profile()` now returns `unresolved_manifests == []` for it. The survey script was not
rerun a third time purely to refresh one already-explained, already-reverified line — rerunning
the full 25-repo survey a third time to update cosmetic output would not have changed the
conclusion, only cost more clone time.

## Regression proof: the 3 real enabled pilots are unaffected

`inspection/file_inventory.py`'s rewrite is load-bearing for the *shipped* pipeline too
(`orchestrator.inspect_repo`/`generate_repo` both call it), not just the new profiling
capability — so it earned the same byte-for-byte proof as Wave 3's own original refactor:

| Pilot | facts_hash | manifest | gap_report | validation_report.json | diff.patch | New commits |
|---|---|---|---|---|---|---|
| `3d/java` | identical | identical | identical | identical | identical | none |
| `cells/java` | identical | identical | identical | identical | identical | none |
| `pdf/java` | identical | identical | identical | identical | identical | none |

All three: `STALE_NONCOMPLIANT` before and after (unchanged — 3d's pre-existing
`commercial_mention_discipline` failure; cells/pdf's `idempotency` mismatch from Wave 3's
`runtime_min_version` addition, both already-known, already-explained states, not new). `llm_called:
None` for all three — zero LLM calls, zero mutation, matching every prior verification pass in
this project's history.

## Summary

1. **What improved**: all six ecosystem parsers are now proven against real, previously-unseen
   registry data, not just synthetic fixtures and one Java repo — closing the honest gap flagged
   at the end of Wave 3's own summary ("not yet proven against a real non-Java repo"). Two real
   bugs (one crash, one systemic 100%-miss detection gap affecting every `.NET` repo in the
   registry) were found and fixed, each with a regression test that fails on the pre-fix code.
2. **What did not improve**: `aspose-page-foss`'s ~175–185s profiling latency (large repo, ~1 GB,
   2500+ files) is unchanged by the noise-dir-skip fix — the single-walk redesign still has to
   traverse the *entire* tree for a single-ecosystem repo, since 5 of 6 registered ecosystems'
   patterns never resolve and the walk can only stop early once every pattern is either found or
   the tree is exhausted. Not a regression (it was already this slow, or slower, before today),
   but not fixed either — an honest, open item.
3. **Regressions introduced**: none found. The 3 real enabled pilots are byte-for-byte identical
   across every field checked (facts_hash, manifest, gap_report, validation_report, diff.patch,
   commit history).
4. **Production-readiness**: the detection *mechanism* (finding and parsing manifests) is now
   solidly proven across the real registry's actual diversity, for all six platforms. Two things
   still gate a broader claim of "production-ready for any repo": (a) the `aspose-page-foss`-class
   large-repo latency, which could matter if this profiling capability runs unattended, frequently,
   or against much larger third-party repos outside this registry; (b) this survey exercised
   *detection and parsing*, not the live package-registry resolution path
   (`ecosystems/resolver.py`), which remains Maven-only and untested against any of the newly-
   detected platforms — a separate, already-documented Wave 3 scope boundary, not reopened here.

## Next production-grade actions

- If unattended/frequent execution against large repos becomes a real requirement (Wave 5+), add
  a depth or file-count bound to `_find_manifest_paths()`'s walk, accepting a documented, small
  risk of missing a very deeply-nested manifest in exchange for a hard latency ceiling — not done
  here since no current caller needs that guarantee yet, and guessing a bound without a real
  latency requirement to size it against would be exactly the kind of premature engineering this
  project avoids.
- Extend `ecosystems/resolver.py` beyond Maven Central (PyPI first, matching the registry's own
  10-of-25 Python-platform weight) once a wave actually needs live install-path resolution for a
  non-Java platform — explicitly out of scope for this hardening pass, which was about detection
  and parsing correctness, not live resolution.
