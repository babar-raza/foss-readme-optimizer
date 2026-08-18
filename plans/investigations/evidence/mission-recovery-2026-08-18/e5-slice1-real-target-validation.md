# E5 slice 1 — real-target validation before merge (2026-08-18)

Before merging `mission-recovery/e5-dispositions` into main, validated the implementation
against the ACTUAL note-python blocking claim (`source:claim:4781:0d4d28fef68b38fd`) — not a
synthetic fixture — by calling `corroborate_claim_disposition` directly in the isolated
worktree, reading main's `runs/baseline/aspose-note-foss__Aspose.Note-FOSS-for-Python/README.md`
read-only (no writes to main).

## Result

The exact byte-recovered claim text (`Document("SimpleTable.one")` Quick Start code block)
corroborates as `excluded_with_reason` when the model cites
`unverifiable_fixture_dependency:SimpleTable.one` — `SimpleTable.one` is a `.one` test document
that genuinely does not ship with the installed package. **This is the S1 residue map's Lane C
canary, confirmed working before the code ever ran inside the live pipeline.**

Negative control: the same predicate citing a path that DOES ship with the package
(`__init__.py`, standing in for a real shipped source file) correctly stays unverified —
proving the fail-closed check is real, not a rubber stamp.

## Disposition

Branch rebased cleanly onto current main (no conflicts), full claim-suite gate reproduced
(371 passed / 1 skipped, matching the implementation agent's report exactly), and now this
targeted validation against the real blocking claim it was built to close. Approved for merge;
queued behind the live portfolio driver per the worktree-integration discipline (this branch
touches `verification/claim_disposition.py` and `readme/claim_accountability_llm_disposition.py`
— files the live process imports on every member).
