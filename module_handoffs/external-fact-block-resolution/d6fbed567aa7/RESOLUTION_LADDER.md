# Resolution ladder

Two independent taxonomies drive resolution:

- `FactClaimKindV1` -- what kind of claim the blocked fact surface represents
  (`identity_coordinates`, `static_existence`, `example_execution`, `runtime_behavior`).
  Selects which evidence tier is *competent* to justify it.
- `ExternalFactBlockClassV1` -- why extraction failed. Selects which
  `ExternalDependencyFingerprintV1` fields make a future retry worthwhile (see
  `DEPENDENCY_INVALIDATION.md`). The two taxonomies never cross-influence each other's
  decision -- a block never uses `block_class` to pick a wording mode, and the ladder
  never uses `claim_kind` to pick retry fields. Keeping them orthogonal is what prevents
  "evidence present but merely irrelevant" from masquerading as "evidence competent".

## Tiers, strongest first

| Tier | `evidence_kind` | Competent `claim_kind`(s) | Wording granted | Why |
|---|---|---|---|---|
| 1 | `current_source_or_manifest` | `identity_coordinates`, `static_existence` | `assert` | Current immutable source/manifest settles these two by inspection alone; never competent for execution/runtime claims. |
| 2 | `committed_distribution_metadata` | `identity_coordinates` only | `assert` | A built/committed distribution artifact proves package identity, nothing about runtime. |
| 3 | `static_public_api_or_source` | `static_existence` -> `assert`; `example_execution`/`runtime_behavior` -> `qualify` | mixed | Proves existence outright; never proves execution. Not competent for `identity_coordinates`. |
| 4 | `verified_imported_knowledge` | all four | `qualify` (never `assert`) | Bound to current source, so it may corroborate any claim kind, but current source always outranks imported knowledge -- capped at qualify even for identity claims. |
| 5 | `syntax_verified_example` | `example_execution` only | `qualify` (never `assert`) | Syntax verification proves nothing about execution result. |
| 6 | `non_applicability_evidence` | all four | `not_applicable` or `omit`, per the evidence's own `omission_basis` field | Only reached with real evidence the surface doesn't apply -- never a default. |
| 7 | -- (nothing competent found) | -- | `block` | Default terminal state. |

Selection walks tiers 1->5 in order; the first tier with claim-kind-competent,
identity-bound evidence wins (the ladder never keeps looking for something "better"
once a tier resolves). If nothing in tiers 1-5 resolves, tier 6 (non-applicability) is
checked; if that's also empty, the resolution remains blocked at tier 7.

## Identity binding vs. conflict

Two distinct concepts, both evaluated per evidence item against the block:

- **Conflict** (both sides present, different values on `org_repo` / `source_revision` /
  `package_identity` for evidence competent for this claim kind): the *entire*
  resolution fails closed to `block`, regardless of any other evidence present --
  "never pick convenient evidence." Restricted to claim-kind-competent evidence only, so
  an unrelated catalog entry can never spuriously block an unrelated claim.
- **Unbound / incompetent** (the block has a concrete identity value but the evidence
  item's corresponding field is simply absent): not a conflict, just skipped by the
  ladder as if the item weren't in the catalog. Which field matters depends on evidence
  kind: `committed_distribution_metadata` binds on `package_identity` (it has no notion
  of a git revision); every other evidence kind here is source-derived and binds on
  `source_revision`.

## Structural guarantees

`ExternalFactBlockResolutionV1`'s `model_validator` makes the following impossible to
construct, not just discouraged by convention: `assert` without competent tier-1/2/3
evidence and non-empty citations; `not_applicable`/`omit` without tier 6;
`block` with any citation; a conflict without `wording_mode == "block"`.
