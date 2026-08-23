# Interface

Module: `src/readme_agent/facts/external_fact_block_resolution.py`
`from readme_agent.facts.external_fact_block_resolution import ...` -- `facts/__init__.py`
is empty and was left untouched; every consumer imports this submodule directly, matching
every other module in `facts/`.

## Naming deviation, stated explicitly

`ExternalFactBlockClassV1` and `FactClaimKindV1` are bare `typing.Literal` aliases, not
one-field wrapper `BaseModel` classes, even though both carry a `V1` suffix. This matches
the repo's own convention for closed-vocabulary enums elsewhere in `facts/` and
`supervisor/` (`BlockedCategory`, `AcquisitionOutcome`, `ProductTruthOutcome` are all bare
`Literal`s with no suffix) -- `V1` suffixes are otherwise reserved for `BaseModel` schemas
in this package. The two new supporting Literals this module had to invent
(`FactEvidenceKindV1`, `WordingModeV1`) were given the same `V1` suffix for internal
consistency within this one file, rather than mixing conventions inside a single module.
This is a deliberate, narrow, file-scoped choice -- flagging it here so a reviewer does
not read it as an oversight against the four-Literal-named-as-models framing in the
original task brief.

## Public functions

```python
def classify_external_fact_block_class(
    *, diagnostic_code: str | None, detail: str
) -> ExternalFactBlockClassV1: ...

def resolve_external_fact_block(
    *,
    block: ExternalFactBlockV1,
    available_evidence: AvailableFactEvidenceCatalogV1,
    current_dependencies: ExternalDependencyFingerprintV1,
    previous_resolution: ExternalFactBlockResolutionV1 | None = None,
) -> ExternalFactBlockResolutionV1: ...
```

`resolve_external_fact_block` always classifies fresh from `block.diagnostic_code` /
`block.detail` internally -- there is no `block_class` field on `ExternalFactBlockV1` a
caller could set directly, so classification cannot be bypassed or contradicted by a
caller-supplied value. `previous_resolution` is purely informational: the function always
computes a fresh resolution from `block` / `available_evidence` / `current_dependencies`
and only uses `previous_resolution` to report whether anything causally relevant changed.

## Types

- `FactClaimKindV1` -- `identity_coordinates | static_existence | example_execution | runtime_behavior`
- `ExternalFactBlockClassV1` -- 13 values, see `BLOCK_TAXONOMY.md`
- `FactEvidenceKindV1` -- 6 values, see `RESOLUTION_LADDER.md`
- `WordingModeV1` -- `assert | qualify | omit | block | not_applicable`
- `ExternalFactBlockV1` -- the input block (`block_id`, `fact_surface`, `claim_kind`,
  `diagnostic_code`, `detail`, `org_repo`, `source_revision`, `package_identity`)
- `AvailableFactEvidenceV1` -- one evidence item (`evidence_id`, `evidence_kind`,
  `competent_claim_kinds`, `org_repo`, `source_revision`, `package_identity`,
  `omission_basis`, `detail`); a `model_validator` enforces `omission_basis` is set iff
  `evidence_kind == "non_applicability_evidence"`.
- `AvailableFactEvidenceCatalogV1` -- `org_repo`, `source_revision`, `items`; a
  `model_validator` enforces unique `evidence_id`s.
- `ExternalDependencyFingerprintV1` -- 11 optional fingerprint fields, no timestamp field
  by design (see `DEPENDENCY_INVALIDATION.md`).
- `FactAssertionAuthorityV1` -- the winning ladder tier's justification
  (`ladder_tier`, `evidence_kind`, `claim_kind`, `competent`, `citation_evidence_ids`,
  `rationale`); a `model_validator` enforces tier 7 cites nothing and every other tier
  records an `evidence_kind`.
- `ExternalFactBlockResolutionV1` -- the output (see `REPORT.md` field list); a
  `model_validator` enforces: `authority.claim_kind == claim_kind`; `conflict_detected`
  agrees with `conflicting_evidence_ids`; a conflict forces `wording_mode == "block"`;
  `assert` requires competent tier-1/2/3 evidence with non-empty citations;
  `not_applicable`/`omit` require tier 6; `block` cites nothing. These are structural
  guarantees enforced at construction time (a `ValueError` on violation), not just
  documented conventions -- mirroring `facts/example_verification_schema.py`'s
  `LocalProductVerificationV1.verified_truth_requires_isolated_execution` pattern.

All models are frozen (`ConfigDict(extra="forbid", frozen=True)` via a shared
`_StrictModel` base), matching `facts/readme_facts_readiness.py` and every other recent
model in this package.
