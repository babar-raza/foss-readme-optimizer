# Current five blocks matrix

**GENERIC MODULE PROVEN; CURRENT FIVE BLOCKS REQUIRE INTEGRATION-TIME QUALIFICATION.**

## Why the exact five receipts are not in this handoff

PF-01's closeout checkpoint
(`plans/investigations/evidence/portfolio-proof-knowledge-acceptance-20260821/checkpoint.json`,
committed to git) records a summary count: `"external_fact_blocks": 5`, from a portfolio
sweep whose full README states these were "five source/package/example failures"
classified as narrow `infra_external` fact blocks. The detailed, per-repository receipts
behind that count live only in `runs/readme-poc/portfolio-summary.json`.

That path is `.gitignore`d (confirmed: `git ls-files runs/` returns nothing from the main
working tree). This lane was built via `git clone --no-checkout <upstream-url>` --
a fresh clone pulls only tracked, committed content. Confirmed directly in this lane:
`runs/` does not exist in the clone at all. **The exact five receipts were therefore
never available inside this isolated lane, by construction, before any work began.**

## What this means

Nothing in this handoff should be read as "the five PF-01 blocks are now resolved." No
repository name, failure message, or receipt from that sweep was invented, guessed, or
approximated to fill this gap -- per the task's explicit instruction, none of that
happened here.

## What was built instead

A fully generic module, proven against **13 synthetic scenarios** (one per
`ExternalFactBlockClassV1` value) in the 52-test suite -- every scenario is clearly a
constructed, generic example (see the module docstring and
`test_generic_fixtures_here_are_synthetic_and_never_claimed_as_a_real_pf01_receipt` in
`tests/unit/test_external_fact_block_resolution.py`), never a reproduction of a real
receipt.

## Distinguishing generic coverage from real-receipt coverage

| | Generic fixture coverage (this handoff) | Real PF-01 five-block coverage |
|---|---|---|
| Source | Hand-constructed `ExternalFactBlockV1`/`AvailableFactEvidenceV1` literals in the test file | `runs/readme-poc/portfolio-summary.json` (gitignored, not in this lane) |
| Proves | The resolver's logic is correct for every block class and ladder tier | Nothing about the actual five repositories/failures |
| Status | Done, 52/52 passing | Not attempted -- data was never available to attempt it |

## What integration-time qualification means

Before this module is used to make any real claim about the five PF-01 blocks, whoever
integrates it (Codex, after PF-03, per the task brief) must: (1) obtain the real
receipts from `runs/readme-poc/portfolio-summary.json` or wherever the live pipeline
currently produces them, (2) translate each receipt's actual diagnostic signal onto this
module's `_DIAGNOSTIC_CODE_TO_BLOCK_CLASS` vocabulary (or extend that table if none of
the 12 existing codes fit), (3) construct real `AvailableFactEvidenceV1` catalogs from
whatever evidence genuinely exists for each of those five repositories, and (4) run
`resolve_external_fact_block()` against that real data to see what it actually reports
-- which may or may not match the sweep's original "narrow infra_external" framing once
run through this stricter, evidence-tiered ladder.
