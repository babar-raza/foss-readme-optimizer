# Causal fingerprint specification

## Cascade (first-available-wins; `stage` is always in the hash payload at tiers 1-6)

| tier | level | fires when | hashed payload | ecosystem/pipeline in hash? |
|---|---|---|---|---|
| 0 | `corrupt_or_stale_evidence` | unparseable timestamp, or `dependency_fingerprint == {}` when present | `{"level": "corrupt_or_stale_evidence"}` (constant — every corrupt observation fleet-wide shares one cluster) | no (no stage either) |
| 1 | `error_gate_check_code` | `structured_error_code` or `gate_or_check_id` set | `{stage, structured_error_code, gate_or_check_id}` | no |
| 2 | `stage_causal_component` | `causal_component` set (tier 1 absent) | `{stage, causal_component}` | no |
| 3 | `structured_semantic_args` | `structured_error_args` non-empty (tiers 1-2 absent) | `{stage, structured_error_args}` | no |
| 4 | `ecosystem_toolchain_provider` | `ecosystem`/`blocked_category`/`exception_type` set (tiers 1-3 absent) | `{stage, ecosystem, blocked_category, exception_type, pipeline_source}` | **yes, from here on** |
| 5 | `dependency_fingerprint` | fleet-shared-key diff vs snapshot non-empty (tiers 1-4 absent) | `{stage, changed_dependencies, pipeline_source}` | yes |
| 6 | `normalized_diagnostic` | guaranteed fallback | `{stage, normalized_diagnostic, pipeline_source}` | yes |

Hash function: `canonical_sha256` from `readme_agent.supervisor.portfolio_scheduler.contracts`
(`sha256(json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=False))`) — the
repo's one existing canonical-hashing primitive, reused verbatim, never reimplemented.

**Why ecosystem/pipeline_source are excluded from tiers 1-3 but included from tier 4 on**: a
genuinely shared *structured* cause (matching error code, causal component, or semantic args) is
legitimately cross-ecosystem/cross-pipeline evidence of one real shared defect — forcing ecosystem
into the hash there would fragment a true `shared_code_defect` into several
`ecosystem_adapter_defect` clusters. Once no structured signal exists, ecosystem/pipeline are the
*only* remaining evidence, so excluding them there would risk merging unrelated repos by
coincidence. This same principle, already established for `ecosystem` in the original module
design, was extended to `pipeline_source` because this repo's fleet currently runs failures through
three non-reconciled pipelines (zero-provider qualification, `commands_poc` delivery, the
`local_poc` supervisor seam) whose weak-signal failures should never silently merge just because
they share a stage and an exception type.

## Normalizer (`_normalize_diagnostic_text`, tier 6 only)

Order: `redact_secret_like_values` (reused from `evidence/redaction.py`) → CRLF/CR→`\n` → strip
ISO-8601 timestamps, UUID-shaped IDs, `run-`-prefixed IDs, temp/home-dir path prefixes,
attempt/retry counters, bare `<n>s` durations → collapse whitespace → `[:500]` cap.

Never strips (no pattern in the normalizer targets these, by construction): error/gate/check codes,
stage names, exception/module/function identifiers, ecosystem strings, 64-hex sha256 values, bare
git SHAs, dependency-fingerprint values (never routed through this function — tier 5 hashes the raw
dict, not free text), check IDs/semantic args (own structured tiers, never normalized).

## Classification decision table (ordered, first match wins)

| # | classification | condition |
|---|---|---|
| 0 | `unknown` (opaque-bulk override) | `level == "normalized_diagnostic"` and `member_count >= 5` and no member has any structured field at all → forces `confidence="low"`, `recommended_repair_scope="manual_classification_required"` |
| 1 | `corrupt_or_stale_evidence` | `level == "corrupt_or_stale_evidence"` |
| 2 | `input_contract_mismatch` | `gate_or_check_id`/`structured_error_code` (case-insensitive) in `{validation_rejected, schema_mismatch, contract_hash_mismatch, facts_hash_mismatch, candidate_hash_mismatch}` |
| 3 | `infra_external` | unanimous infra exception/`blocked_category=="infra_external"` and `dependency_changed is False` |
| 4 | `transient_provider` | unanimous infra-with-dependency-changed, or a timeout/rate-limit/truncation-shaped exception name |
| 5 | `shared_code_defect` | tier ∈ {1,2,3} and `len(distinct_ecosystems) >= 2` |
| 6 | `ecosystem_adapter_defect` | tier ∈ {1,2,3} and `len(distinct_ecosystems) < 2` |
| 7 | `repository_evidence_defect` | tier ∈ {4,5,6} and `stage` ∈ facts/input-family stages |
| 8 | `candidate_specific_rejection` | tier ∈ {4,5,6} and `stage` ∈ candidate/review-family stages and `member_count == 1` |
| 9 | `unknown` (default) | none of the above matched |

`confidence` = `high` for tiers 1-3, `medium` for tiers 4-5, `low` for tier 6 or the row-0 override.

## Prioritization (all components visible, none opaque)

```
sort_key = (
    classification_actionability_rank,   # 0=most actionable .. 4=least; the PRIMARY key
    -repos_blocked,
    earliest_shared_stage_rank,
    0 if single_repair_multi_repo else 1,
    0 if deterministic else 1,
    0 if minimal_proof_possible else 1,
    0 if dependency_changed else 1,
    fingerprint_hash,                    # total-order tie-break, input-order-independent
)
```

Actionability rank: 0 = `shared_code_defect`/`ecosystem_adapter_defect`/`input_contract_mismatch`;
1 = `repository_evidence_defect`/`candidate_specific_rejection`; 2 = `transient_provider`;
3 = `infra_external`; 4 = `corrupt_or_stale_evidence`/`unknown`. Because actionability is the
primary key, a large/old `infra_external` cluster can never outrank a small actionable
`shared_code_defect` cluster.

## Minimal proof cohort selection

Per cluster: score each member additively (`evidence_ref` +3, `structured_error_code`/
`gate_or_check_id`/non-empty `dependency_fingerprint` +2 each, `structured_error_args`/
`exception_type` +1 each, a clean `known_reproducibility_verdict`
(`NO_OP_PROVEN`/`TRANSACTION_NO_OP_PROVEN`/`RENDER_REPRODUCIBLE`) +2) → highest score is the primary
representative, ties broken by earliest observation then `org_repo`. One extra representative per
additional distinct ecosystem beyond the primary's own. `unknown`-classified clusters (including the
row-0 opaque-bulk override) keep **every** member as its own representative in the cohort — never
claim one repair closes an unproven shared cause.
