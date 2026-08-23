# Integration guide (for Codex, after PF-03)

This module is intentionally **not wired into the runtime**. No registry entry, no CLI command, no
import from any pipeline module references it. That is by design (`NO INTEGRATION` in the task
brief) and is itself verified (`test_29a` proves the module's own import graph never reaches
`supervisor.*`, so nothing on the production path can accidentally start depending on it either).

## How to run it against a real PF-03 bundle pair, without trusting the runtime being verified

1. **Locate the two sealed bundle roots.** A first transaction's bundle and its immediate no-op
   replay's bundle both live under `runs/readme-poc/<org>__<repo>/<source_revision>/` in this
   repository's convention (see `paths.readme_poc_repository_dir`). PF-03's expected output is
   exactly this pair: a first bundle reaching `AGENT_APPROVED`/30-of-30, and the same bundle
   directory advanced in place to `NO_OP_PROVEN` after an immediate replay. **Snapshot the first
   bundle to a separate directory before the replay runs**, since the real pipeline updates the
   bundle in place rather than writing a second directory -- `attest_complete_transaction_noop`
   requires `first_bundle_root != replay_bundle_root` (`distinct_bundle_roots`) precisely because a
   caller handing it the same path twice would be a vacuous, meaningless attestation.

2. **Build a `ReplayAttestationContractV1`** describing the real bundle's artifact inventory, hash
   modes, identity bindings, provider-proof wiring, and product-effect expectations. Do not import
   this module's test file for that -- `tests/unit/test_sealed_transaction_replay.py::_golden_contract`
   is a complete worked example against the confirmed real bundle shape (manifest.json,
   source/*, facts/*, candidate/*, planning/*, review/*, receipts/*, both ledgers) and is safe to
   copy from, but a production contract should be authored directly against the real, current
   `manifest.json`/`sha256sums.txt` layout at integration time, since the real bundle may carry
   fields this synthetic fixture does not (or vice versa -- see KNOWN_LIMITATIONS.md for the two
   artifacts this test suite invented that have no real counterpart yet).

3. **Call the entrypoint** with the two real paths and the contract. It reads only; it never writes,
   calls a provider, or touches the target repository, so it is safe to run repeatedly, in CI, or
   against production evidence without any side effect.

4. **Inspect the result**, not the process's own exit code alone:
   - `proof.passed` -- the overall verdict.
   - `proof.findings` -- every drift finding, each with a stable `code` (e.g.
     `new_provider_call:authoring`, `identity_drift:facts_hash`, `model_drift:visitor_review`) and
     a `stage`. Treat `code` as the machine-stable contract for any downstream automation; `detail`
     strings are for humans and may be redacted/truncated.
   - `proof.earliest_affected_stage` -- the earliest of the 10 stages any finding touched, or
     `None` if nothing drifted.
   - `proof.provider_delta.accounting_certain` -- **must be checked before trusting any call-count
     field**. If `False`, every count on `provider_delta` is `None`, not `0` -- this is the
     fail-closed contract, not a bug. A caller that only checks `passed` already gets this right
     (uncertain accounting always makes `passed=False`), but any caller reading individual
     `provider_delta` fields directly must respect the same rule.
   - `proof.proof_hash` -- a stable, byte-identical citation for the whole proof, independent of
     JSON key/array ordering in either bundle and independent of volatile fields (run ids,
     timestamps, local paths). Suitable as a receipt to log or compare across repeated runs.

## Never trust the runtime being verified

The attestor's entire value depends on it never importing or invoking anything from the pipeline
it verifies. If a future change to this module ever needs a helper from `supervisor.*`,
`capabilities.*`, `llm.*_client`, or similar, that is a sign the change belongs in a different
module -- not a signal to widen this one's import allowlist. `test_29a` will fail loudly if that
line is crossed; do not weaken that test to make an integration convenient.

## Suggested (not implemented) next step

A `default_local_poc_replay_contract(*, contract_id, org_repo, source_revision)` factory, wiring
the contract for the real confirmed bundle shape, was designed but deferred (see
KNOWN_LIMITATIONS.md) since no real bundle pair existed to validate it against during this lane.
Adding it once a real PF-03 pair exists -- and validating the factory against that real pair as an
integration test in `tests/integration/` -- is the natural next step, and does not require touching
anything in this module's owned files beyond adding the one new function.
