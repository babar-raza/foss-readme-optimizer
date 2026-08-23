# Transaction identity matrix

Every `IdentityComponentV1` and the stage it belongs to (`_COMPONENT_STAGE` in the module -- the
module owns this mapping, not the caller, so a contract cannot mis-declare a component's stage and
defeat drift classification). Mandatory components (must be declared `REQUIRED` in every contract,
enforced at contract-construction time) are marked with `*`.

| Stage | Components |
|---|---|
| `SOURCE` | `repository_identity`\*, `source_revision`\*, `source_readme_digest`, `source_tree_inventory_digest`, `family_platform` |
| `KNOWLEDGE` | `facts_hash`\*, `knowledge_identity`, `protected_content_hash` |
| `CONFIGURATION` | `prompt_registry_hash`, `prompt_hashes_by_id`, `prompt_dependency_hashes`, `template_contract_hash`, `presentation_contract_hash`, `check_implementation_hash`, `check_classification_hash`, `validator_identity_hash`, `reviewer_standard_hash`, `reviewer_schema_hash` |
| `AUTHORING` | `provider_model_route`, `sampling_parameters` |
| `CANDIDATE` | `candidate_hash`\*, `candidate_stage_dependency_key`, `patch_digest`, `document_plan_hash` |
| `VALIDATION` | `claim_evidence_hash`, `disposition_evidence_hash`, `reconciliation_evidence_hash`, `check_evidence_hash`, `deterministic_validation_hash` |
| `REVIEW` | `factual_review_identity`, `visitor_review_identity` |
| `ACCEPTANCE` | `rubric_identity`, `final_verdict_identity`, `acceptance_binding` |
| `EFFECTS` | `effect_inventory_digest` |
| `SEALING` | `artifact_inventory_digest`, `llm_ledger_boundary` |

## Why `artifact_inventory_digest`/`llm_ledger_boundary` are not mandatory

Both live at `SEALING` but are deliberately excluded from `_MANDATORY_REQUIRED_COMPONENTS` (see
REPORT.md bug #1 / KNOWN_LIMITATIONS.md): their underlying content legitimately *grows* between a
first transaction and its immediate no-op replay (new cache-reuse ledger records, a new
`NO_OP_PROVEN` receipt), so requiring cross-bundle digest equality on either would fail every real
no-op. Their proofs are handled by dedicated, more precise mechanisms instead:

- **Inventory boundary**: `ReplayArtifactInventoryV1.hash_declaration_mismatches` (recomputed
  digest vs. the bundle's own `sha256sums.txt` declaration, per artifact) plus
  `undeclared_semantic_paths`/`uncovered_paths`/`orphan_inventory_paths`.
- **Ledger boundary**: `ProviderLedgerDeltaV1.ledger_superset_ok`/`ledger_temporal_ok`/
  `ledger_scope_ok` -- every first-bundle ledger record must appear byte-identical in the replay
  ledger, every genuinely new record must carry an allowed disposition, occur strictly after the
  first bundle's latest record, and stay within the declared `org_repo`/`source_revision` scope.

## Digest-shaped components

`_DIGEST_COMPONENTS` (must resolve to a 40-64 char lowercase hex string, or the component is
`malformed`, not merely absent): `source_revision`, `source_readme_digest`,
`source_tree_inventory_digest`, `facts_hash`, `prompt_registry_hash`, `template_contract_hash`,
`presentation_contract_hash`, `check_implementation_hash`, `check_classification_hash`,
`validator_identity_hash`, `reviewer_standard_hash`, `reviewer_schema_hash`, `candidate_hash`,
`candidate_stage_dependency_key`, `patch_digest`, `document_plan_hash`,
`deterministic_validation_hash`, `protected_content_hash`.

## How comparison works

For every declared, non-`NOT_APPLICABLE` component: resolve its bound JSON pointer inside its
declared artifact in both bundles; canonically hash the *resolved value* (not the value itself --
`SealedTransactionIdentityV1.component_digests` stores digests only, bounding proof size and never
leaking artifact content); compare the two digests. Any mismatch produces an
`identity_drift:<component>` finding at the component's fixed stage. All mismatches are reported;
`earliest_affected_stage` is the minimum stage across every finding, mirroring the existing
`local_poc_cache._earliest_affected_stage` pattern.
