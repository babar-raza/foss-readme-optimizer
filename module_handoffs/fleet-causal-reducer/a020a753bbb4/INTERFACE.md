# Public interface — `failure_causal_reducer.py`

Module: `src/readme_agent/supervisor/portfolio_proof_engine/failure_causal_reducer.py`

## Entry point

```python
def reduce_fleet_failures(
    *,
    observations: Sequence[FailureObservationV1],
    dependency_snapshot: DependencyFingerprintSnapshotV1 | None = None,
) -> FleetCausalReductionV1
```

Pure and read-only. No filesystem, network, or state-mutation side effects.

## Models

All models are frozen Pydantic (`ConfigDict(extra="forbid", frozen=True)`), `schema_version: Literal[1] = 1`.

### `FailureObservationV1`
Embeds `receipt: ProofStageReceiptV1` wholesale (reused, not duplicated). Additional fields:
`family`, `blocked_category: BlockedCategory | None`, `causal_component`, `structured_error_code`,
`gate_or_check_id`, `structured_error_args: tuple[tuple[str,str],...]`, `dependency_fingerprint:
dict[str,Any] | None`, `exception_type`, `evidence_ref` (path-traversal-guarded), `observed_at`,
`last_observed_at`, `attempt_count`, `pipeline_source`, `known_reproducibility_verdict`. Read-only
properties `org_repo`/`stage`/`ecosystem` proxy the embedded receipt. Validator requires
`receipt.status == "FAILED"`.

### `DependencyFingerprintSnapshotV1`
`by_org_repo: dict[str, dict[str, Any]]`, `global_dependencies: dict[str, Any] | None`,
`captured_at`. Method `current_for(org_repo) -> dict[str, Any]` merges global + per-repo. Caller
computes this externally (e.g. from `local_poc_cache.current_blocked_decision_dependencies()`); the
reducer never computes it itself.

### `CausalFailureFingerprintV1`
`level: FingerprintLevelV1` (7 values), `stage`, mirrored structured fields (visible regardless of
which tier fired), `fingerprint_hash: str` (the clustering key).

### `RepresentativeProofCaseV1`
`org_repo`, `observation` (embedded `FailureObservationV1`), `selection_reason`,
`evidence_completeness_score`.

### `CausalFailureClusterV1`
26 fields covering everything the task's OUTPUT section requires: `cluster_id`, `fingerprint`,
`classification`, `classification_reason`, `confidence`, `member_org_repos`, `member_count`,
`distinct_ecosystems`, `distinct_pipeline_sources`, `earliest_shared_stage(_rank)`,
`evidence_completeness`, `changed_dependency_keys`, `dependency_changed`, `repos_blocked`,
`single_repair_multi_repo`, `deterministic`, `minimal_proof_possible`,
`classification_actionability_rank`, `recommended_repair_scope`, `required_closure_evidence`,
`inclusion_reason`, `exclusion_reason`, `estimated_retries_avoided`, `priority_rank`,
`representative`.

### `FleetCausalReductionV1`
`generated_at`, `input_observation_count`, `input_org_repo_count`, `clusters` (tuple order **is**
priority ranking), `minimal_proof_cohort`, `unresolved_org_repos` (always `()`),
`classification_counts`, `total_estimated_retries_avoided`.

## Literal type aliases

- `FailureClassificationV1` — 9 values: `shared_code_defect`, `ecosystem_adapter_defect`,
  `repository_evidence_defect`, `infra_external`, `transient_provider`,
  `corrupt_or_stale_evidence`, `input_contract_mismatch`, `candidate_specific_rejection`, `unknown`.
- `FingerprintLevelV1` — 7 values: `corrupt_or_stale_evidence`, `error_gate_check_code`,
  `stage_causal_component`, `structured_semantic_args`, `ecosystem_toolchain_provider`,
  `dependency_fingerprint`, `normalized_diagnostic`.
- `ConfidenceV1` — `high` | `medium` | `low`.
- `ReproducibilityVerdictV1` — `RENDER_REPRODUCIBLE`, `RENDER_REPRODUCIBILITY_FAILED`,
  `NO_OP_PROVEN`, `TRANSACTION_NO_OP_PROVEN`, `UNKNOWN` (reused codebase vocabulary, not invented).
- `EvidenceCompletenessV1` — `complete` | `partial` | `none`.
- `RecommendedRepairScopeV1` — `shared_module`, `ecosystem_adapter`, `single_repository_evidence`,
  `external_dependency_wait`, `provider_retry_after_change`, `manual_classification_required`.

## What is NOT exported / NOT public

No `__all__` and no re-export from `portfolio_proof_engine/__init__.py` (deliberately not edited —
Codex owns wiring). Every private helper is leading-underscore (`_build_fingerprint`, `_classify`,
`_build_cluster`, `_deduplicate`, `_sort_key`, etc.) and not part of the supported interface; import
only the 6 public models, the 6 public Literal aliases, and `reduce_fleet_failures`.
