# Known limitations

## No real PF-03 bundle pair existed at build time

The PF-02 bundle at
`runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/ee05c1ba9153ef5916b7a108406c794f2e464d01/`
stops at `DETERMINISTIC_VALIDATED` (no `review/final-verdict.json`, no `review/no-op-proof.json`).
The only `NO_OP_PROVEN` example bundle found predates `stage_receipts`,
`candidate_stage_dependency_key`, and the LLM call ledger entirely. Every test fixture here is
therefore synthetic but structurally faithful to the confirmed real shape, not a captured real
pair. **Attesting a real PF-03 pair remains an integration-time test** -- see INTEGRATION.md.

## Two artifacts in the test fixtures are forward-looking inventions

- `review/rubric-evaluation.json` -- no real bundle today persists a rubric-scoring artifact to
  disk; `supervisor/portfolio_proof_engine/rubric_criteria.py::evaluate_all_criteria` computes the
  30-criterion rubric on the fly from the rest of the bundle rather than writing it out. This
  fixture file represents what such an artifact would look like if PF-03 starts persisting one
  (matching `RubricCriterionResultV1`'s shape). A real integration should either wire the identity
  bindings for `rubric_identity`/`final_verdict_identity` to whatever the real rubric evidence
  turns out to be, or drop this artifact from the contract if no such file materializes.
- `effects/product-effect-ledger.json` -- similarly invented, to give the product-effect proof an
  affirmative evidence surface beyond `review/no-op-proof.json`'s `patch_created`/
  `duplicate_bundle_created` booleans. A real integration can likely rely on
  `intake/preflight.json`'s `target_remote_effects_allowed`/`target_local_effects_allowed` flags
  (confirmed present in real bundles) instead, and drop this fixture-only artifact.

Neither invention affects the module's correctness -- the contract is fully caller-declarative, so
a production contract is free to reference only artifacts that actually exist in real bundles.

## `default_local_poc_replay_contract` factory was designed but not implemented

The plan called for a public factory wiring a contract against the real bundle shape by default.
Deferred because validating such a factory meaningfully requires a real bundle to validate it
against, which didn't exist. `tests/unit/test_sealed_transaction_replay.py::_golden_contract` is a
complete, tested worked example of the same shape and is the reference to build the factory from.

## `_MANDATORY_REQUIRED_COMPONENTS` is deliberately narrow

Only `repository_identity`, `source_revision`, `facts_hash`, `candidate_hash` are enforced as
mandatory identity bindings. `artifact_inventory_digest` and `llm_ledger_boundary` were removed
from that set during implementation (see REPORT.md bug #1) because their underlying content
legitimately grows between a first transaction and its replay. A contract author who wants
additional bindings enforced (prompt/template/reviewer-standard/etc.) must declare them explicitly
with `level="REQUIRED"`; the module will not infer that they should be mandatory.

## Provider-proof ledger scope defaults to "cumulative"

`ProviderProofContractV1.replay_ledger_scope` defaults to `"cumulative"`, meaning the primary
provider-proof source of truth is the append-only, whole-revision-history ledger
(`llm-call-ledger.jsonl`), not the narrower current-transaction-scoped ledger
(`candidate/current-transaction-llm-call-ledger.jsonl`) that some real bundles also carry. The
narrower ledger, when present, is not independently cross-checked by this module -- a caller who
wants that cross-check declared it as an additional artifact and adds their own comparison, or
extends `_build_provider_delta`. This was a deliberate scope trim, not an oversight: the cumulative
ledger alone is sufficient to prove "replay added zero new provider_call records," which is the
module's actual mandate.

## Receipt-inventory (`receipts/*.json` `artifact_inventory[]`) cross-checking was trimmed

The design allowed for cross-checking declared artifact hashes against BOTH `sha256sums.txt` and
any `receipts/*.json` artifact-inventory blocks. Only the `sha256sums.txt` cross-check is
implemented (`ReplayArtifactInventoryV1.hash_declaration_mismatches`,
`uncovered_paths`/`orphan_inventory_paths`) since it is the universal, always-present self-declaration
mechanism in every sealed bundle; the receipts-specific cross-check was not needed to satisfy any
of the 29 mandated tests and was left out to keep the module's scope bounded. Nothing prevents
adding it later as a strict superset of the existing behavior.
