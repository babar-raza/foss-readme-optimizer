# OPT-STANDALONE-EXTERNAL-FACT-BLOCK-RESOLUTION -- handoff report

## Summary

A standalone, non-integrated module that deterministically resolves one structured
external fact block against a caller-supplied catalog of available evidence and the
current external-dependency fingerprint. It decides which of `assert` / `qualify` /
`omit` / `block` / `not_applicable` is permitted, citing the evidence that justifies it,
and reports whether a future retry would be worthwhile. It is a generic sibling to the
narrow, product-specific `infra_external` classification already embedded in
`facts/deterministic_truth_salvage.py` -- not a replacement for it, and not wired to it.

## Base / drift / branch

See `BASE_AND_DRIFT.json`. Base SHA `d6fbed567aa7d99dd0e065944e3694cb6ebd5ced`, branch
`claude/standalone-external-fact-block-resolution-d6fbed567aa7`. Upstream `main` had
drifted by exactly one unrelated commit (`16113ac6f` -- an evidence-supersession
recovery fix) by the time this handoff was written; that commit touches none of this
lane's owned paths. No rebase/merge was performed, per the isolation contract.

## Commits

See `COMMITS.txt`. Three commits: (1) contracts + taxonomy + a deliberately failing
test run (the resolver function did not exist yet), (2) the resolver implementation
with all 52 tests passing, (3) this handoff documentation.

## Files changed

See `CHANGED_FILES.txt`. Exactly two owned source/test files, both new:
`src/readme_agent/facts/external_fact_block_resolution.py` (597 lines) and
`tests/unit/test_external_fact_block_resolution.py` (794 lines). A subsequent
PLAN-THEN-EXECUTE audit pass (commit `fadc997e`) found and fixed one real code
duplication (two near-identical tier-7 terminal-block constructions), which is why the
line count differs slightly from the original 588 recorded when this report was first
drafted -- see `COMMITS.txt` for the full 4-commit history and `KNOWN_LIMITATIONS.md`
for the corrected note on the plan's original 300-360-line estimate.

## Interface

See `INTERFACE.md` for the full model/function surface. One public function,
`resolve_external_fact_block()`, plus one classification helper,
`classify_external_fact_block_class()`, and 7 frozen pydantic models (2 of the 7 are
implemented as bare `Literal` type aliases rather than wrapper models -- see
`INTERFACE.md` for why).

## Taxonomy, ladder, wording

See `BLOCK_TAXONOMY.md`, `RESOLUTION_LADDER.md`, `AUTHORIZED_WORDING_MATRIX.md`.

## Dependency invalidation / retry

See `DEPENDENCY_INVALIDATION.md`.

## Exact-five-blocks coverage

**GENERIC MODULE PROVEN; CURRENT FIVE BLOCKS REQUIRE INTEGRATION-TIME QUALIFICATION.**
See `CURRENT_FIVE_BLOCKS_MATRIX.md` for why the real PF-01 receipts were unavailable
inside this isolated lane and what that does and doesn't mean for the module's
correctness.

## Tests

52/52 passing. See `TEST_RESULTS.json`. `ruff check`, `ruff format --check`, and `mypy`
all pass on both files; `git diff --check` reports no whitespace issues.

## Known limitations

See `KNOWN_LIMITATIONS.md`.

## Security / redaction

See `SECURITY_AND_REDACTION.md`.

## PLAN-THEN-EXECUTE mission audit (post-handoff)

A separate mission bound this session plan file as sole authority (scope explicitly
confined to this module -- integration remains out of scope) and independently
re-verified every plan claim against live repository/lane state rather than trusting
this report: reran all 5 plan-declared verification commands fresh (all pass), confirmed
all 16 changed files are exactly the owned paths and no prohibited path was touched,
confirmed `facts/__init__.py` is still empty, confirmed nothing anywhere imports the new
module, and reconciled all 26 mandatory test items against the real test file
(26/26 mapped to passing tests, plus 2 bonus structural-validator tests). One real
finding: the module's actual line count (588) exceeded the plan's own 300-360 estimate.
Investigation found one genuine code duplication (not mere verbosity) and fixed it
(commit `fadc997e`); no other redundancy was found on full re-read. See
`KNOWN_LIMITATIONS.md` item 6 for the full account.

## Integration

See `INTEGRATION.md`. Nothing in this change set registers, wires, imports from, or is
imported by any existing pipeline code. No fact-readiness, gating, supervisor, or CLI
file was touched. No network, provider, or filesystem action was taken by the module
itself (verified by an automated test that scans the module's own source for forbidden
tokens). No PR was opened, main was not pushed to, and nothing was merged or rebased.
The five real PF-01 `infra_external` blocks are not claimed to be resolved by this
change -- only that a generic, tested mechanism now exists for a later integration pass
to qualify them against.
