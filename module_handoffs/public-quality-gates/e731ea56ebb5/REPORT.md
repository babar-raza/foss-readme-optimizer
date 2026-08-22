# Public-candidate quality gate — handoff report

## Root problem

Owner audits of shipped README candidates (`plans/investigations/owner_audit/**`,
2026-08-19/20) found three recurring, machine-detectable defect classes that reached delivery
without a deterministic gate catching them:

1. **Same-document capability contradictions** — a method or format described as working in one
   section while a limitations section says it raises `NotImplementedError` or is unsupported (3D
   `Mesh.union`/`NurbsSurface.to_mesh`; BarCode symbology/backend claims).
2. **Internal process narration leaking into public prose** — "verified against", "exercised in an
   isolated environment", provenance/reviewer/reconciliation language that belongs in evidence, not
   in customer-facing copy.
3. **Malformed, duplicated, or empty/placeholder prose** — mechanically corrupted inflections
   (`supports supportsing`), templated near-duplicate bullets, and sections that can only be filled
   by fabrication (the PSD README-only case).

This module is a standalone, non-LLM, deterministic detector for all three classes, plus two
narrower net-new capabilities the brief asked for: claim grounding against explicit structured
negative/unresolved facts, and always-advisory structural size/density outliers.

## Design: reuse first, tiered confidence for what's genuinely new

Before writing new detection logic, I read `readme/presentation_lint.py` and its four sub-modules
in full and found they **already** deterministically catch classes 2 and 3 above —
`internal_assurance_commentary`/`generic_preservation_heading`/`api_reference_internal_assurance`
for leakage, `semantic_duplicate`/`api_reference_tautological_description`/
`api_reference_low_information_description`/`api_reference_malformed_terminology` for malformed/
duplicated prose (one of that module's own test fixtures is literally
`"Supports ising byte array and toing dict."` — the exact `supports supportsing` shape named in
this task's brief). AGENTS.md is explicit: *"No duplicate or overlapping capability without a
documented reason."* So this module **composes** `lint_readme_presentation()`'s typed findings for
those two categories (via `_REUSED_LEAKAGE_RULE_IDS`/`_REUSED_MALFORMED_RULE_IDS`, defended by a
test that asserts those rule IDs still exist upstream) rather than re-deriving phrase lists, and
spends its own original logic on what nothing in the repo currently does: cross-section
contradiction detection and claim grounding against structured negative facts.

Cross-section contradiction detection is inherently regex-and-heuristic without an LLM — a real
ceiling on precision and recall, not a bug to code around. Rather than pretending one heuristic can
be both, findings are tiered by evidence strength and only the higher tiers block:

- **Tier A — structured evidence** (`claim_grounding_negative_fact`): only runs when the caller
  supplies `ProductFactsV2`/`ReadmeClaimAccountabilityMapV1`. Compares prose against facts whose
  `field == "product.limitations"` or `verification_state in {"conflicting","blocked","missing"}`.
  This is the most durable path because it's anchored on `fact_id`/`verification_state`, not on the
  candidate's specific wording — stable even if regenerated candidate text is reworded between
  runs (candidate generation upstream is not deterministic at the wording level; the underlying
  facts are).
- **Tier B — exact code symbol** (`contradiction_capability_symbol`): the same backtick-quoted
  identifier appears with a positive cue in one place and `NotImplementedError`/"not supported" in
  another. Exact-token matching, high precision.
- **Tier C — phrase-level** (`contradiction_capability_phrase`): no shared code symbol; matched via
  `capability_semantics.same_public_capability` plus a locally-defined read/write direction check
  (import vs. export are different operations — this is what makes that check pass). Blocking only
  when both sides share a strong discriminator token (an acronym/format name like "COLLADA");
  otherwise advisory. A vague match with no anchor is exactly the "merely searches for raw
  keywords" failure mode the brief warns against — a gate that cries wolf on vague matches trains
  callers to ignore it.
- **Scope-qualifier rule** (B and C): a negative statement narrowed by "through the public API" /
  "in this build" / "in this edition" / "on this platform" that the positive statement doesn't also
  carry is not treated as a contradiction — two compatibly-scoped true statements, not a defect
  (the audit's own COLLADA internal-exporter-implemented-vs-public-route-unavailable case is the
  canonical example of this being *correct*, not a missed defect).

## Invariants

- **Determinism**: `evaluate_public_candidate_quality` is a pure function (no filesystem/clock/
  random access). Findings are sorted by `(section_path, span.start, span.end, check_id)`;
  `finding_id` is a content-only fingerprint of `check_id` + that finding's own locations (never a
  global counter or whole-document hash), so editing one section never changes finding IDs anchored
  elsewhere. `report_hash` is validated by a `model_validator` that recomputes it from the report's
  own `model_dump(exclude={"report_hash"})`.
- **Honest "not evaluated"**: `claim_grounding_negative_fact` is omitted from `checks_run` entirely
  (not run-with-zero-findings) when no structured facts/claims are supplied.
- **Fail-loud reuse**: `test_reused_presentation_lint_rule_ids_still_exist` asserts the rule IDs this
  module depends on are still produced by `lint_readme_presentation` — a rename/removal upstream
  fails this module's CI instead of silently degrading leakage/malformed-prose coverage to zero
  (the audits' own root-cause pattern for the disposition-ledger fail-open bugs was exactly a check
  silently returning nothing instead of failing loud).
- **Versioned heuristics**: `PUBLIC_QUALITY_CHECKS_VERSION` + `compute_checks_source_hash()` (hashes
  the whole module's source, filtering only the self-referential recorded-hash line) mirror
  `validation/registry.py`'s `VALIDATION_RULESET_VERSION` tripwire — a deliberate heuristic edit
  must bump the version and update the recorded hash in the same commit.

## Tests and results

24 tests in `tests/unit/test_public_candidate_quality.py` (22 from the initial implementation,
covering every required red test from the brief plus an adversarial/false-positive set and two
regression-control tests — reused-rule-id tripwire, heuristic-version tripwire — plus 2 more added
after a pilot rerun found a coverage gap, see `PILOT_RERUN.md`). See `TEST_RESULTS.json` for exact
counts.

**Manual precision dry-run** (not a committed test — a validation step against real data): ran the
evaluator, read-only, against the three real committed candidates named in the brief
(`plans/investigations/evidence/level8-portfolio-readme-proposals-2026-07-25/aspose-{3d,barcode,
note}-foss-for-python/candidate-readme.md`). This surfaced two genuine false-positive classes
(an "other than PDF" exception clause being ignored, and conditional "if `X` is installed/
unavailable" prose being read as a firm claim) which were fixed with generic rules before
finalizing — see `WORKLOG.md`'s implementation log for the full trace. After the fixes, all three
real candidates produce zero `cross_section_contradiction` findings, while the reused
`malformed_low_information_prose` check still correctly catches real, legitimate duplication
defects on two of the three (matching the audit's documented "API surface documented three
separate, overlapping times" finding).

**Follow-up pilot rerun** (`PILOT_RERUN.md`): formalized the above into a rigorous before/after
comparison against a precisely reconstructed pre-fix code snapshot, diffed by each finding's
unique `finding_id`. Confirmed 9→0 `cross_section_contradiction` findings on the Note candidate
with 0 findings added anywhere and all 9 removed findings manually verified as false positives —
and, separately, found that the original 22 tests would not have caught either bug on their own
(21/22 still passed against the reconstructed pre-fix code). Closed with two dedicated regression
tests, each verified red against the pre-fix reconstruction and green against the fix.

## What was deliberately not integrated

- No edits to `plans/**`, `AGENTS.md`, `docs/**`, `.github/**`, any state-machine/mission-control
  module, candidate-generation call site, portfolio orchestration, or CLI registration.
- No `__init__.py` edit to register the module.
- No new facts/candidate/claim-accountability schema — every structured input is one of this repo's
  existing types (`ProductFactsV2`, `ReadmeClaimAccountabilityMapV1`, `StructuredFactCoordinateV1`).
- No rubric scoring, hard-disqualifier computation, or check-classification logic — this module
  produces evidence a rubric criterion or gate could consume, not a verdict.

## Known limitations

See `KNOWN_LIMITATIONS.md` for the full, itemized list (recall bounds, precision-over-recall
tradeoff on Tier C, uncalibrated structural thresholds, the wording-vs-semantics determinism
caveat, and the Windows MAX_PATH artifact encountered while running the narrow regression suite
inside this lane).
