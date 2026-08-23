# Dependency invalidation / retry design

Structurally replicates the invalidation *pattern* already proven in
`src/readme_agent/supervisor/blocked_decision_cache.py::evaluate_blocked_decision_cache`
(compare stored vs. current dependency state, fail open -- ambiguity always favors
allowing a retry, never suppressing one) using this module's own
`ExternalDependencyFingerprintV1` type. Nothing is imported from `supervisor/`.

## Causally-relevant fields, per block class

| `block_class` | Causally relevant fields |
|---|---|
| `repository_clone_failure` | `source_revision`, `repository_remote_fingerprint` |
| `git_lfs_object_unavailable` | `source_revision`, `git_lfs_endpoint_fingerprint` |
| `package_registry_unavailable` | `package_registry_snapshot_hash`, `network_policy_fingerprint` |
| `package_version_unresolved` | `package_registry_snapshot_hash`, `dependency_manifest_hash` |
| `toolchain_unavailable` | `toolchain_fingerprint` |
| `dependency_resolution_failure` | `dependency_manifest_hash`, `package_registry_snapshot_hash` |
| `example_runtime_unavailable` | `execution_environment_fingerprint`, `toolchain_fingerprint` |
| `source_package_mismatch` | `source_revision`, `package_registry_snapshot_hash` |
| `network_rate_limited` | `network_policy_fingerprint` |
| `corrupt_local_cache` | `local_cache_fingerprint` |
| `unsupported_platform_verifier` | `execution_environment_fingerprint`, `toolchain_fingerprint` |
| `external_authentication_unavailable` | `authentication_context_fingerprint`, `network_policy_fingerprint` |
| `unknown` | **all** fields (fail-open: the cause itself is unclassified) |

`corrupt_local_cache` and `network_rate_limited` are deliberately disjoint single-field
sets -- a changed network field never triggers a "retry worthwhile" signal for a
cache-corruption block, and vice versa (test:
`test_corrupt_local_cache_and_network_rate_limited_have_disjoint_causally_relevant_fields`,
`test_a_changed_network_field_does_not_recommend_retry_for_a_corrupt_cache_block`).

Whenever the winning ladder tier's `evidence_kind == "verified_imported_knowledge"`,
`imported_knowledge_revision` is added to the relevant set regardless of `block_class`,
since that evidence's own freshness is always relevant to that specific resolution.

## `resolution_hash`

sha256 of a sorted-key, tight-separator canonical JSON payload of
`{org_repo, block_source_revision, block_class, claim_kind, <relevant fields only>}`,
mirroring `facts/acceptance_contract.py::FactAcceptanceContractV1.canonical_hash()`'s
pattern (computed inline with `hashlib`/`json`, not a shared helper -- this matches how
`facts/protected_content.py::_hash` also hashes inline). Including `block_class` and
`claim_kind` in the payload means a reclassification counts as "changed" even when every
fingerprint field is byte-identical.

## `previous_resolution` is informational only

`resolve_external_fact_block()` always computes a fresh result from `block` /
`available_evidence` / `current_dependencies`; it never short-circuits from
`previous_resolution`'s stored wording or citations. `previous_resolution` is used only
to set `fingerprint_changed_since_previous_resolution`:

- `None` if there is no `previous_resolution`, or it is for a different `block_id`
  (treated identically -- fail-open, never a hard error).
- `resolution_hash != previous_resolution.resolution_hash` otherwise.

`retry_recommended = wording_mode != "assert" and fingerprint_changed is not False` --
once a resolution reaches `assert`, retry is never recommended regardless of fingerprint
state (there is no stronger outcome left to chase). Wall-clock age never enters this
calculation: `ExternalDependencyFingerprintV1` deliberately has no timestamp field, so
"time passed" alone can never flip `retry_recommended`.

## `resume_predicate`

A human-readable string built from one of four fixed templates depending on
`wording_mode` and `fingerprint_changed`: already-strongest-possible (assert),
changed-so-retry-warranted, unchanged-so-no-productive-retry, or
first-resolution-recorded. Always names the exact causally-relevant fields involved.
