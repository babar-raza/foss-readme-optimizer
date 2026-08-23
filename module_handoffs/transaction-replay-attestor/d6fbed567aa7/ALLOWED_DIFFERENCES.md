# Allowed differences

`ALLOWED_DIFFERENCE_KEYS` (module constant, **non-extensible by the contract** -- a caller-supplied
exemption would be a drift-laundering hole, so this list cannot be widened per-contract):

```
run_id, campaign_run_id, receipt_id,
started_at, finished_at, completed_at, promoted_at, sealed_at, captured_at, emitted_at,
observed_at, timestamp, last_run_timestamp,
snapshot_root, bundle_root, ledger_path,
process_id, pid
```

Precedent: `local_poc_snapshot_evidence.py::_stable_snapshot_identity` pops exactly `captured_at`
and `snapshot_root` for the same reason -- "this particular local capture, not the immutable
object."

## The three conditions for an ignore to hold

A difference under one of these keys is only actually ignored when **all three** hold:

1. The key is in `ALLOWED_DIFFERENCE_KEYS`.
2. Both sides' values are scalars (`str | int | float | bool | None`). A differing `dict`/`list`
   under an allowed key is still drift -- this blocks smuggling a structured payload under, say,
   `"run_id"`.
3. The mismatch isn't found via a full-document semantic projection that already excluded it --
   i.e. every ignored pointer is still recorded, never silently dropped.

Every ignored pointer is recorded in `ReplayArtifactDeltaV1.allowed_differences_observed` as
`"<artifact_id>#<pointer>"` (RFC 6901 JSON pointer), so an allowed difference is visible in the
proof, not invisible.

## Never allowed, regardless of key name

`source_revision`, `facts_hash`, `candidate_hash`, any `*_sha256`/`*_hash`, `prompt_*`, `verdict`,
`checks`, `nonce`, `token`, `llm_call_count`, `llm_call_ids`, `calls_by_job`, `latency_ms`,
`total_tokens`, `cost`, `attempt`, `model`, `provider`, `patch_created`, `duplicate_bundle_created`,
`completed_stages`, `lifecycle_status`, and every dependency fingerprint or semantic evidence
field. None of these keys appear in `ALLOWED_DIFFERENCE_KEYS`; any difference in them is drift by
construction.

## How the allowlist actually gets applied

`_project_semantic(document)` recursively strips any dict key that is both in
`ALLOWED_DIFFERENCE_KEYS` and holds a scalar value, then the projected forms of the first and
replay copies of a `json_object`/`json_array` artifact are canonically hashed and compared. If
they match, the artifact is `semantically_identical` (not `byte_identical` -- the raw bytes did
differ, just not in a way that matters) and every actually-observed allowed difference is recorded
via `_diff_allowed_pointers`. If they don't match after projection, the artifact is `changed` and a
`semantic_artifact_changed` finding is emitted at the artifact's declared stage.

Artifacts declared in `output_equivalence_artifact_ids` skip this pathway entirely and require
**raw byte identity** -- the allowlist never applies to a promised-byte-identical artifact (test
10's mutation targets `source/revision.json`, which is not declared output-equivalent, precisely to
exercise the allowlist pathway rather than the stricter one).
