# T2 — golden-authority retirement (harvest first)

**Scope note**: `golden-sample/` at the repo root and its two referencing root docs
(`CLAUDE-CODE-DIRECTIVE-v2-AUTONOMOUS.md`, `KICKOFF-PROMPT.md`) belong to a separate,
currently-active POC-freeze governance track (2026-08-09 product-owner freeze:
"root directive files + golden-sample override plans/"; that freeze explicitly says
"no contract edits, no new machinery"). This retirement is scoped to the
**freshness-service plan's own composition machinery only** — it does not modify, retire,
or supersede `golden-sample/` for the separate POC track, and does not touch either root
directive file.

## What "retired" means here

Within this plan (§8, resolution "Golden authority retires immediately"): once the
freshness-service composition engine exists (T3's vendored 81-check battery + T14's
section-registry + the imported 31-repo corpus), it is the sole authority for structure and
acceptance. `golden-sample/README.golden.md` is never read at runtime by that machinery.

## Verification (2026-08-15)

Grepped `src/`, `scripts/`, and every `.yml`/`.sh` for `golden-sample` — the only Python
match is `tests/unit/test_repository_text_normalization.py`, which references an unrelated
path (`plans/investigations/evidence/presentation-golden-sample-v1/README.md`, a different
fixture) not the `golden-sample/` directory. **No production code path in this repository
currently reads `golden-sample/` as an authority.** The freshness-service plan therefore
retires it as a forward-looking authority without any code change being required — there
is nothing live to unwire.

## Harvest

The three files in this directory (`GOLDEN-SAMPLE-NOTES.md`, `README.golden.md`,
`dispositions.golden.json`) are preserved byte-identical copies of the source, kept as
calibration/style reference material for T6 (calibration harness) and T14 (section
registry) once built: concrete shape rules (brief+details pattern, one-details-block-max,
Mermaid compaction ceilings, "no silent drops," Enterprise Edition naming) worth
harvesting into the corpus rather than discarding.

## Drift test

`tests/unit/test_golden_sample_not_an_authority.py` asserts no `src/`/`scripts/` Python
file imports or opens a path containing `golden-sample/` (the retirement claim above,
made mechanically checkable rather than just asserted in prose).
