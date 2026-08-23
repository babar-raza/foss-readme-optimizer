# Drift stage matrix

The 10-stage order (`ReplayStageV1` / `STAGE_ORDER`), verbatim from the task brief:

1. `SOURCE`
2. `KNOWLEDGE`
3. `CONFIGURATION`
4. `AUTHORING`
5. `CANDIDATE`
6. `VALIDATION`
7. `REVIEW`
8. `ACCEPTANCE`
9. `EFFECTS`
10. `SEALING`

`earliest_affected_stage = min(findings, key=stage order)` if any finding exists, else `None`.
`affected_stages` is every distinct stage touched, stage-ordered. This mirrors the existing
`local_poc_cache._earliest_affected_stage` pattern (including its fail-closed default: a finding
code without an explicit stage mapping is not possible in this module -- every `record(...)` call
site names an explicit stage -- but the pattern is deliberately the same defensive shape).

## Finding code -> stage, as actually emitted

| Finding code | Stage | Emitted when |
|---|---|---|
| `identity_drift:<component>` | per `_COMPONENT_STAGE[component]` (see TRANSACTION_IDENTITY_MATRIX.md) | a bound identity component's digest differs between bundles |
| `semantic_artifact_changed` | the artifact's declared `stage` | a `compare_for_delta=True` artifact changed beyond the allowlist |
| `undeclared_difference` | `SEALING` | the raw file sets of the two bundles differ outside declared/non-semantic paths |
| `new_provider_call:<axis>` | `AUTHORING` (authoring axis) or `REVIEW` (factual_review/visitor_review/repair axes) | a new `provider_call`-disposition ledger record appears for that axis |
| `model_drift:<axis>` | `AUTHORING` or `REVIEW` per axis | a reused (shared call_id) ledger record's `model` changed while `prompt_sha256` stayed the same |
| `sampling_drift:<axis>` | `AUTHORING` or `REVIEW` per axis | a reused ledger record's `request_sha256` changed while `prompt_sha256` and `model` stayed the same |
| `unmapped_job` | `AUTHORING` | a new ledger record's `job` is not in `KNOWN_PROVIDER_JOB_AXES` or the contract's `additional_known_jobs` |
| `provider_ledger_missing` | `SEALING` | `accounting_certain` is `False` (ledger missing/unparseable/non-EXACT/incoherent) |
| `provider_accounting_not_exact` | `SEALING` | declared accounting fields disagree with independently recomputed values, or a ledger load error occurred |
| `product_effect_observed` | `EFFECTS` | a product-effect expectation resolved to a violating value |
| `effect_evidence_missing` | `EFFECTS` | a required product-effect pointer did not resolve (never treated as "proven absent") |
| `escaping_symlink` | `SEALING` | a symlink was found anywhere in a declared artifact's path chain, or a non-regular/oversize file was declared |
| `missing_required_artifact:<artifact_id>` | `SEALING` | a `REQUIRED` artifact is absent in a bundle |
| `unexpected_semantic_artifact:<path>` | `SEALING` | a file on disk is neither declared nor on the non-semantic allowlist |
| `duplicate_declaration` | `SEALING` | the bundle's own `sha256sums.txt` declares one relative path twice with conflicting digests |
| `artifact_hash_mismatch` | the artifact's declared `stage` (promised byte-identity failures) or `SEALING` (self-declaration mismatches) | a recomputed digest disagrees with either the bundle's own declaration or a promised byte-identical peer |
| `inventory_incomplete` | `SEALING` | a declared artifact fails structured schema validation (malformed JSON, unparseable ledger, etc.) |

## Note on `CONFIGURATION` vs `VALIDATION` for "check drift"

The task's own stage list separates "3. Prompt/template/configuration" from "6. Validation/checks"
-- this module resolves that split by binding a check's *definition* (`check_implementation_hash`,
`check_classification_hash`, `validator_identity_hash`) to `CONFIGURATION` (it's about which
tooling/config ran, same category as prompt/template versioning) and a check's *execution evidence*
(`deterministic_validation_hash`, `check_evidence_hash`, `claim_evidence_hash`,
`disposition_evidence_hash`, `reconciliation_evidence_hash`) to `VALIDATION` (what that run actually
produced). Test 17 as shipped exercises the `CONFIGURATION` surface (`check_implementation_hash`);
the `VALIDATION` surface (`deterministic_validation_hash`) is exercised separately by test 18's
sibling case and by the general identity-comparison machinery, but does not have its own dedicated
"check drift" test -- a reasonable follow-up if stricter per-surface coverage is wanted.
