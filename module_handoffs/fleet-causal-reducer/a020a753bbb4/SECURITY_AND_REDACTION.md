# Security and redaction

## Redaction

Every free-text diagnostic that could reach `CausalFailureFingerprintV1.normalized_diagnostic` (the
only free-text field in any output model) is passed through `redact_secret_like_values` (reused from
`readme_agent.evidence.redaction`, not reimplemented) as the *first* step of normalization, before
any other transformation. This masks OpenAI/GitHub/Google-style API keys, `Bearer` tokens, and
`key=`/`token=`/`api_key=`/`access_token=` query parameters to `[REDACTED]`. Verified live in
`test_secrets_are_redacted_in_normalized_diagnostic`.

No other output field carries caller-supplied free text at more than a capped, structured length
(`classification_reason`, `required_closure_evidence`, `inclusion_reason`, `exclusion_reason`,
`selection_reason` are all reducer-generated fixed/templated strings, never echoes of raw input
text, and are all length-capped at 500 chars matching the repo's existing
`RubricAcceptanceOutcome.bounded_summary()` convention).

## Path traversal

`FailureObservationV1.evidence_ref` is validated at construction (Pydantic `field_validator`,
`ValueError` on violation — never silently sanitized, never reaches the reducer):
- rejects any path with a `..` segment (after normalizing `\` to `/`)
- rejects absolute POSIX paths (leading `/`)
- rejects paths with a drive-letter prefix (`C:/...`) or any colon in the first path segment

`evidence_ref` is never opened, read, or resolved by this module — it is an opaque pointer for the
caller's own traceability, kept only for path-traversal validation and for scoring representative
selection (`+3` when present). Verified live in
`test_evidence_ref_path_traversal_rejected_at_construction` and
`test_evidence_ref_absolute_path_rejected_at_construction`.

## No raw provider/header/credential persistence

This module never receives, stores, or forwards HTTP headers, tokens, or full provider responses —
its only inputs are already-sanitized `FailureObservationV1`/`DependencyFingerprintSnapshotV1`
records the caller constructs. `dependency_fingerprint` values are treated as opaque hash-shaped
strings (the codebase's own convention — `local_poc_cache.py`'s dependency dict is always hashes,
never raw content) and are hashed via `canonical_sha256`, never logged verbatim outside the
already-redacted `normalized_diagnostic` path.

## Malformed/incompatible evidence — fail-closed, never silently discarded

Structurally invalid input (bad `org_repo` shape, bad hash-pattern fields, a non-FAILED receipt
wrapped in an observation, unsorted/duplicate `structured_error_args` keys) is rejected at Pydantic
construction time — before it can ever reach `reduce_fleet_failures`. Semantically-implausible-but-
shape-valid evidence (an unparseable timestamp, an empty `dependency_fingerprint` dict) is caught
inside the reducer and routed to one shared `corrupt_or_stale_evidence` cluster — **never dropped**.
`FleetCausalReductionV1.unresolved_org_repos` is kept as a visible output field (always `()` by
construction) specifically so a future regression in this "never lose a repo" guarantee would show
up as data, not require a crash to notice.

## No state writes, no network, no provider calls

Verified live via `test_no_state_write_or_io_occurs` (`monkeypatch.chdir(tmp_path)` +
post-call directory-empty check) and by code inspection: the module imports no filesystem, network,
subprocess, or provider-client symbol anywhere. `dependency_snapshot` — the one input that could in
principle be computed from live state — is always caller-supplied; this module never derives it.
