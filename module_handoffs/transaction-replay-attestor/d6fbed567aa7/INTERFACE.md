# Public interface

Module: `src/readme_agent/verification/sealed_transaction_replay.py`

## Entrypoint

```python
def attest_complete_transaction_noop(
    *,
    first_bundle_root: Path,
    replay_bundle_root: Path,
    expected_contract: ReplayAttestationContractV1,
) -> CompleteTransactionNoOpProofV1
```

Pure, read-only, total (never raises for any bundle-content issue -- only a malformed *contract*
raises `pydantic.ValidationError`, and only at `ReplayAttestationContractV1` construction time,
before the attestor ever runs).

## Contract-side models (caller builds one `ReplayAttestationContractV1` per attestation)

- `ReplayAttestationContractV1` -- the whole declaration: `org_repo`, `expected_source_revision`,
  `artifacts`, `identity_bindings`, `output_equivalence_artifact_ids`, `provider_proof`,
  `product_effects`, plus non-semantic/lifecycle-effect allowlist overrides and size bounds.
- `DeclaredArtifactV1` -- one artifact: `artifact_id`, `relative_path` (POSIX-only, validated),
  `hash_mode` (`raw_sha256` | `crlf_normalized_sha256` | `canonical_json_sha256`), `kind`
  (`json_object` | `json_array` | `jsonl_llm_ledger` | `text` | `binary`), `level` (`REQUIRED` |
  `OPTIONAL` | `NOT_APPLICABLE`), `stage` (one of the 10 drift stages), `scope` (`both` |
  `first_only` | `replay_only`), `compare_for_delta` (bool, default `True` -- set `False` for
  artifacts that legitimately gain bookkeeping content during a true no-op, e.g. `manifest.json`,
  the cumulative ledger, and receipts).
- `IdentityBindingSpecV1` -- binds an `IdentityComponentV1` (one of ~37 named components covering
  source/facts/prompt/model/candidate/review/rubric/ledger identity) to a JSON pointer inside one
  declared artifact.
- `ProviderProofContractV1` -- which two artifacts are the "first" and "replay" LLM call ledgers,
  which artifact/pointer carries each bundle's *declared* accounting summary, and the allowed
  replay dispositions (default: `cache_reuse` only).
- `ProductEffectExpectationV1` -- one of the 8 `ProductEffectV1` literals (`readme_write`,
  `commit`, `branch`, `push`, `pull_request`, `publication`, `duplicate_lifecycle_effect`,
  `target_tree_change`) bound to a pointer and a comparison mode.

Helper factory: `default_local_poc_replay_contract(*, contract_id, org_repo, source_revision)` --
NOT present in the shipped module (deferred; see KNOWN_LIMITATIONS.md). Callers currently build a
`ReplayAttestationContractV1` directly; `tests/unit/test_sealed_transaction_replay.py::_golden_contract`
is a complete worked example against the confirmed real bundle shape.

## Proof-side models (the return value)

`CompleteTransactionNoOpProofV1` -- the top-level verdict:

| field | meaning |
|---|---|
| `passed: bool` | overall verdict |
| `checks: dict[str, bool]` | every named check, pass/fail |
| `failures: tuple[str, ...]` | human-readable failure strings (redacted) |
| `findings: tuple[ReplayDriftFindingV1, ...]` | machine-readable `{code, stage, detail}` records |
| `earliest_affected_stage` / `affected_stages` | drift classification across the 10-stage order |
| `first_identity` / `replay_identity: SealedTransactionIdentityV1` | resolved identity component digests per bundle |
| `first_inventory` / `replay_inventory: ReplayArtifactInventoryV1` | per-bundle artifact hashes, missing/undeclared/unsafe paths |
| `artifact_delta: ReplayArtifactDeltaV1` | byte/semantic equality classification per compared artifact |
| `provider_delta: ProviderLedgerDeltaV1` | independently recomputed ledger accounting, per-role new-call counts |
| `effect_delta: ProductEffectDeltaV1` | proven-absent / unproven / violated per product effect |
| `proof_hash: str` | 64-hex canonical hash of the whole proof (see `canonical_proof_hash`) |

`canonical_proof_hash(proof) -> str` independently recomputes `proof.proof_hash` for verification.
`canonical_json_sha256(value) -> str` is the shared canonical-JSON hashing primitive.

## Stage vocabulary (`ReplayStageV1`, in order)

`SOURCE < KNOWLEDGE < CONFIGURATION < AUTHORING < CANDIDATE < VALIDATION < REVIEW < ACCEPTANCE < EFFECTS < SEALING`

## What it never does

No write, no subprocess, no network, no import of `supervisor.*`/`capabilities.*`/`gitsafety.*`/
`specialists.*`/`state.*`/`llm.*_client`. Verified by `test_29a/b/c` (static AST import-allowlist,
runtime monkeypatch negative controls, and a check that no forbidden module object is bound in the
module's own namespace).
