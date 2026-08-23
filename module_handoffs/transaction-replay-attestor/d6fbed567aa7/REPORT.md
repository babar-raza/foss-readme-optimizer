# OPT-STANDALONE-TRANSACTION-REPLAY-ATTESTOR -- Report

## Summary

Built `sealed_transaction_replay.py`: a standalone, read-only attestor that independently proves,
from two sealed evidence bundles alone, that a replay transaction was an exact no-op of the first
-- same inputs, identical semantic outputs, zero new author/factual-review/visitor-review/repair
provider calls, and no product effect. It never runs, calls, or imports the pipeline it verifies.

No real PF-03 bundle pair (a completed transaction plus its immediate no-op replay) exists in this
repository yet, so the test suite is built on synthetic-but-structurally-faithful fixtures, exactly
as the task brief anticipated. Real PF-03 attestation remains an integration-time exercise -- see
INTEGRATION.md.

## What was verified

- **Base upstream SHA**: `d6fbed567aa7d99dd0e065944e3694cb6ebd5ced` (captured via `git ls-remote
  origin refs/heads/main` before any lane work began).
- **Current upstream main at handoff time**: `8252bfe648c4bf79fd7b736069f7fd503fb5b74e` -- upstream
  moved during this lane's work. Per the isolation directive, this was recorded but never
  fetched/merged/rebased into the lane; see BASE_AND_DRIFT.json.
- **Branch**: `claude/standalone-transaction-replay-attestor-d6fbed567aa7`, pinned at BASE_SHA plus
  two commits (see COMMITS.txt).
- **Commits**: (1) contracts + fixtures + tests (red -- fails to import without the module), (2)
  the attestor implementation (green -- all 41 tests pass), (3) this handoff documentation.
- **Tests**: 41/41 pass, covering all 29 mandated items plus 12 additional negative-control /
  robustness cases discovered necessary during implementation (see TEST_RESULTS.json).
- **Push**: not yet performed as of this report -- pending an explicit go-ahead, per the standing
  instruction to confirm before any push to a shared remote. All recovery artifacts (patches,
  bundle, combined diff) are prepared under `$LANE_ROOT/handoff/` regardless.

## Files changed (owned paths only)

- `src/readme_agent/verification/sealed_transaction_replay.py` (new, 2206 lines)
- `tests/unit/test_sealed_transaction_replay.py` (new, 1407 lines)
- `tests/fixtures/sealed_transaction_replay/{README.md,source-README.md,candidate-README.md,candidate-README.patch}` (new)
- `module_handoffs/transaction-replay-attestor/d6fbed567aa7/**` (this directory)

No other file was read-write touched. No `AGENTS.md`, `plans/**`, `docs/**`, `.github/**`, CLI,
existing supervisor/cache/no-op/portfolio module, existing evidence, product repository, or
graph/state file was modified. The concurrent, unrelated in-progress edits observed in the shared
working directory (`local_poc_review_evidence.py`, `local_poc_snapshot_evidence.py`,
`local_poc_superseded.py`, a new `local_poc_failure_recovery.py`) were left untouched -- this lane's
isolated clone was bootstrapped from `origin`, not the dirty working tree, so they never entered
this lane's history at all.

## Real bugs found and fixed during implementation (worth flagging to a reviewer)

Building the module against a smoke test, then against the full 29-test suite, surfaced seven
design gaps that would not have been visible from the design pass alone -- each is a genuine
correctness issue, not a cosmetic fix:

1. **`llm_ledger_boundary`/`artifact_inventory_digest` are not cross-bundle-invariant.** An earlier
   draft made both mandatory `identity_bindings` requiring cross-bundle equality; but a legitimate
   no-op's ledger and inventory content *grow* (new cache-reuse records, a new NO_OP_PROVEN
   receipt), so a naive equality check would fail every real no-op. Fixed by dropping both from
   `_MANDATORY_REQUIRED_COMPONENTS` -- their proofs are handled by dedicated mechanisms instead
   (inventory self-declaration cross-checking, ledger superset/temporal/scope coherence).
2. **New `cache_reuse` records were being counted against the zero-new-provider-call budget.**
   Every reused call legitimately appends a new `cache_reuse` ledger record in the replay -- only
   `disposition == "provider_call"` should count toward a role's "new calls" total. Fixed in
   `_build_provider_delta`'s axis-tallying loop.
3. **A disallowed disposition (an unexpected new `provider_call`) was folded into "accounting is
   uncertain"** rather than "accounting is certain, and here specifically is the violation" --
   which meant the very scenario the module exists to catch (a new author call during a replay)
   produced a generic `provider_ledger_missing` finding instead of the specific
   `new_provider_call:<role>` finding. Fixed by removing the disposition check from the
   `accounting_certain` formula (it remains a separate, still-fail-closed check).
4. **Reused-ledger-record drift (model/sampling) was undetected.** The original design only
   compared aggregate ledger coherence; it had no mechanism to distinguish "the same reused call's
   model changed" from "the same reused call's sampling/request changed" from generic corruption.
   Added explicit classification in the ledger-superset comparison, emitting
   `model_drift:<role>`/`sampling_drift:<role>` findings.
5. **The whole-bundle file-set diff (`first_only_paths`/`replay_only_paths`) didn't know about
   declared artifacts.** Any artifact intentionally present in only one bundle (a replay-only
   `no-op-proof.json`, or a first-bundle-only optional artifact that was legitimately dropped)
   tripped `undeclared_difference`. Fixed by exempting every declared artifact path (any
   scope/level) from that diff -- presence/absence of a *declared* artifact is governed precisely
   by its own `level`, not by the raw file-set comparison, which now only watches for genuinely
   *undeclared* asymmetric files.
6. **`raw_digests` broke reorder-invariance for `canonical_json_sha256`-mode artifacts.** The raw
   byte digest was stored unconditionally for every artifact, including ones whose declared hash
   mode is deliberately reorder/formatting-invariant (e.g. `manifest.json`). Reordering its JSON
   keys therefore changed the embedded raw digest and, with it, the proof hash -- exactly what
   requirement 8 ("stable output ordering/hash") forbids. Fixed by only populating `raw_digests`
   for `raw_sha256`/`crlf_normalized_sha256` artifacts; the artifact-delta comparison falls back to
   the (already order-independent) canonical digest for the rest.
7. **`contract_digest` was sensitive to declaration list order.** `artifacts`/`identity_bindings`/
   `product_effects` are declarations, not sequences, but `json.dumps(..., sort_keys=True)` only
   canonicalizes object key order, never array element order. Fixed with
   `_canonical_contract_digest`, which sorts each list by its natural key before hashing.

All seven are documented inline in the module where they matter (see the comments at
`_MANDATORY_REQUIRED_COMPONENTS`, the axis-tallying loop, `accounting_certain`'s assembly, the
ledger-superset loop, `raw_digests` population, and `_canonical_contract_digest`).

## Confirmation

- Nothing was registered or called from runtime; the module is provably import-isolated and
  side-effect-free (`test_29a/b/c`).
- No no-op/PF-03 evidence file was read for anything other than the read-only exploration that
  informed this design (`runs/readme-poc/.../ee05c1ba.../`, read-only, never modified).
- No merge, rebase, cherry-pick, or PR was created.
- No push to `main` occurred, and no push of this branch has occurred yet (pending confirmation).
