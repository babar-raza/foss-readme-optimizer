# POC FREEZE DECLARATION

**Authority: product owner (Babar). This document overrides AGENTS.md process ceremony,
plans/GOVERNANCE.md, and the mission-guard machinery for the duration of the freeze.
It does not override the safety invariants listed at the bottom — those stay absolute.**

## Why this exists

Between 2026-07-17 and 2026-08-09 this project produced complete README candidates for
PDF, Page, Note, and Aspose.3D Python (see `runs/readme-poc/`), then repeatedly
re-declared them "not current" through fact/acceptance contract revisions. Raw historical
reach hit 20/31 FACTS_READY and 9/31 NO_OP_PROVEN; contract-valid reach is 1/0/0/0.
The machinery invalidates its own output faster than it produces it. This freeze ends that.

## Frozen until 12/12 Python READMEs are human-accepted

1. **Contracts are final.** No revision to the fact contract, acceptance contract,
   requirement catalog, decision ledger, evidence schemas, or manifest formats.
   The contracts as of the freeze commit are the POC contracts. A defect found in a
   contract is recorded in `plans/backlog-post-poc.md` and worked around, not fixed.
2. **No new machinery.** No new guards, canaries, claims, leases, fingerprints,
   evidence types, snapshot formats, recovery paths, migration steps, or state
   versions. No refactors. No file splits. No renames.
3. **Mission-guard machinery is out of scope.** The Level-8 graph, durable claims,
   execution-focus binding, approach budgets, and `mission_execution_guard.py` are
   neither obeyed nor edited during POC runs. The straight-line runner (see
   TWEAKS-AND-RUNNER-SPEC.md) bypasses them. Do not "fix" the guard so it can be
   obeyed — bypass is the design.
4. **No process documents.** No new plans, waves, handovers, investigations,
   reconciliations, or status regenerations. Log one line per completed README in
   `logs/<date>.md` and nothing else.
5. **Regression response is bounded.** If a run fails: fix the single causal bug with
   the smallest possible diff, re-run that repo, move on. Two failures on the same
   repo → skip it, record one backlog line, continue with the next repo. Never respond
   to a failure by hardening machinery.

## The only success metric

A README candidate file, produced by the pipeline with the four approved tweaks
applied, delivered to `runs/share/poc/<org__repo>/README.md` and shown to the product
owner. Twelve such files (all admitted Python repos) = POC complete. Nothing else —
no test count, no evidence completeness, no contract validity, no state version —
counts as progress.

## Safety invariants that stay absolute (unchanged)

- No push to any product repository remote. Clones stay push-neutered.
- No PR, no remote write, no default-branch write of any kind.
- `data/products.json` remains the hard allow-list.
- No credentials in logs or evidence.
- LLM never supplies URLs, package coordinates, or facts — deterministic code does.

## Expiry

The freeze lifts when the product owner declares Gate-B review of the 12 Python
candidates complete. Post-freeze, backlogged contract fixes may resume — after the
POC exists, not before.
