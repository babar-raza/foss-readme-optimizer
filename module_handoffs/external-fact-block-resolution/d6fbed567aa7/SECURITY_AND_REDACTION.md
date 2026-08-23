# Security and redaction

## Redaction

`ExternalFactBlockV1.detail` and `AvailableFactEvidenceV1.detail` are caller-supplied
free text (real diagnostic tool output, in the integrated future) and may legitimately
contain a live secret. Every place this module composes a `rationale` string that echoes
that free text passes it through
`readme_agent.evidence.redaction.redact_secret_like_values` first -- the one shared
secret-redaction utility in the repo (`src/readme_agent/evidence/redaction.py`), reused
directly rather than reimplemented. Covered by two tests:
`test_a_secret_like_token_in_the_blocks_own_detail_is_redacted_from_the_rationale` and
`test_a_secret_like_token_in_evidence_detail_is_redacted_from_the_rationale`.

## No network, no filesystem, no clock

The module performs no network calls, no filesystem I/O, and reads no wall-clock time --
every input is a fully-constructed pydantic model passed in by the caller, and every
output is a pure function of those inputs. Verified by an automated test
(`test_the_module_source_contains_no_network_filesystem_or_clock_side_effects`) that
scans the module's own source text for forbidden tokens (`import requests`,
`import httpx`, `import subprocess`, `import socket`, `import urllib`, `from pathlib`,
`datetime.now`, `random.`, `open(`). `ExternalDependencyFingerprintV1` deliberately has
no timestamp field for the same reason (see `DEPENDENCY_INVALIDATION.md`).

## No product/family branching

`fact_surface`, `org_repo`, and `package_identity` are opaque strings, never compared
against a fixed set of known product/family/license names anywhere in the module. All
dispatch happens on the four closed Literal taxonomies
(`FactClaimKindV1`, `ExternalFactBlockClassV1`, `FactEvidenceKindV1`, `WordingModeV1`),
which are product-agnostic by construction. Verified by
`test_identical_ladder_behavior_regardless_of_org_repo_or_package_identity_strings`,
which runs the identical scenario through both a familiar and a deliberately
unfamiliar/nonsense org/package pair and asserts identical output.

## No reimplementation of adjacent policy/pipeline logic

No import of `acquisition.py`, `acquisition_schema.py`, `local_verification.py`,
`example_verification_schema.py`, any `isolated_execution*.py`, `schema_v2.py`,
`gating.py`, `acceptance_contract.py`, `readme_facts_readiness.py`,
`portfolio_facts_readiness.py`, or anything under `supervisor/`. No license-specific
field or branch exists anywhere in the module -- `fact_surface` stays fully opaque, so a
hypothetical `product.license` surface flows through the exact same generic ladder as
any other surface (`test_a_license_fact_surface_flows_through_the_same_generic_ladder_as_any_other_surface`).
Whether "missing LICENSE" even constitutes an external block at all is a policy decision
made entirely upstream, before an `ExternalFactBlockV1` is ever constructed -- this
module has no field or branch that could express that policy even by accident.

## No traversal / injection surface

There is no path construction, no file access, and no dynamic code execution anywhere in
the module, so there is no path-traversal or injection surface to guard against beyond
the redaction covered above. Pydantic's `extra="forbid"` on every model rejects any
unexpected field a caller might try to smuggle in.

## Determinism

`resolution_hash` is a deterministic sha256 of a sorted-key canonical JSON payload;
citation lists (`citation_evidence_ids`, `conflicting_evidence_ids`,
`causally_relevant_fingerprint_fields`) are always sorted before being returned, so
catalog input order never changes the output (see
`test_evidence_catalog_item_order_does_not_change_the_outcome_or_hash` and
`test_two_independently_constructed_but_field_identical_inputs_produce_the_same_hash`).
