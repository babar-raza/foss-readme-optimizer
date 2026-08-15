# T3 — vendored check battery + section/global mapping

**Status: SUBSTANTIAL PROGRESS, not fully complete.** Recorded honestly, not overstated.

## What is genuinely done and verified

- The missing transitive import (`api_table_dupes.py`) was found and vendored (T1B),
  making `readme_refresh_checks.py` importable for the first time since it landed in this
  repo.
- **A real, working registry** (`src/readme_agent/validation/aspose_checks/__init__.py`)
  that loads the vendored module via explicit, fixed path indirection (never depends on
  aspose.org's original package layout existing anywhere), and classifies **all 89**
  `check_*` functions — the count is *derived* by introspection each time, never hardcoded,
  per this plan's own resolution 7.
- **Classification** (severity: hard_gate/heuristic; scope: section/document_global) is
  mechanically derived from the vendored module's own consistent docstring conventions
  ("Hard gate" / "Heuristic, non-blocking..."), not hand-guessed — including correctly
  handling a check whose docstring explains it was *downgraded* from a hard gate (classified
  by which term the docstring states first, i.e. current status, not history), and failing
  closed to `hard_gate` for the one check with no docstring at all.
  - Result: 61 hard_gate / 28 heuristic; 50 section-scoped / 39 document-global.
- **12 tests, all passing**, including **5 real end-to-end invocations** of actual vendored
  check functions (`check_required_sections`, `check_heading_title_case`,
  `check_no_excluded_domain_links`, `check_enterprise_edition_naming`,
  `check_diagram_shape`) against real markdown input — proving the vendored code is not just
  importable but genuinely callable and produces sensible findings.

## What is NOT done (honest gap, not silently dropped)

- **Fail-closed fixtures per individual check** — the plan's full T3 scope calls for one per
  check (89 of them); this session built 5 representative smoke tests proving the invocation
  pattern is sound, not full per-check fixture coverage. Writing and verifying 89 individual
  fixtures with the same rigor applied elsewhere this session would be its own multi-day
  effort.
- **A drift test vs `docs/readme-process.md`** — that document doesn't exist yet in this
  repo; T3's own scope includes creating it, which was not attempted.
- The section/scope classification above is a first, mechanically-derived pass reviewed for
  a handful of representative cases (spot-checked, not individually verified against all 89
  check bodies) — it should be treated as a strong starting point, not a final, individually
  human-reviewed contract.

## Downstream effect

`T4` (merged factpack) does not strictly depend on this registry's completeness and could
proceed in parallel. `T14` (section registry) and everything past it in the plan's gate chain
remains unattempted this session — the true remaining scope (T4, T14, T5–T9, T7A-F,
TP-11A/B, TW-02, TU-01, TG-06A/B, TF-01, T11, T13, TG-07, T12, TW-04, TW-05, TG-08) is
realistically many further sessions of comparable work, not a remaining "final stretch."
