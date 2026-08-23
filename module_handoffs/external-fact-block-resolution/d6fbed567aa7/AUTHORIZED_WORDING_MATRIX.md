# Authorized wording matrix

`resolve_external_fact_block()` returns exactly one `wording_mode`:
`assert | qualify | omit | block | not_applicable`.

| Mode | Meaning | Permitted when |
|---|---|---|
| `assert` | State the fact directly, no hedge. | Tier 1, 2, or 3 (static-existence branch only) evidence is competent and cited, and no identity conflict exists. |
| `qualify` | State the fact with an explicit hedge (e.g. "likely", "as of the last verified build"). | Tier 3 (execution/runtime branch), 4, or 5 evidence is competent and cited. |
| `omit` | Say nothing about this surface at all. | Tier 6 non-applicability evidence with `omission_basis == "omit"`. |
| `not_applicable` | State explicitly that this surface does not apply to this product. | Tier 6 non-applicability evidence with `omission_basis == "not_applicable"`. |
| `block` | Remain blocked; no wording is authorized. | An identity conflict, or no tier 1-6 evidence resolves the claim. |

## Never elevate (enforced by the ladder table, not by convention)

- Static presence (`static_public_api_or_source`) into runtime success -- it asserts
  only `static_existence`; every execution-adjacent claim kind caps at `qualify`.
- Package/distribution metadata into compatibility or runtime proof -- it is only
  competent for `identity_coordinates`.
- Syntax validity into an executed-example proof -- `syntax_verified_example` caps at
  `qualify` and is only competent for `example_execution`.
- Imported knowledge into verified fact -- `verified_imported_knowledge` caps at
  `qualify` unconditionally, even for `identity_coordinates`, because current source
  always outranks it.
- Toolchain absence into "tests passed" -- a `toolchain_unavailable` block with only
  static evidence resolves to `qualify` at best, never `assert`.

## `prohibited_claims` field

`ExternalFactBlockResolutionV1.prohibited_claims` lists every mode in
`("assert", "qualify", "omit", "not_applicable")` other than the one granted -- i.e.
which weaker-or-alternative wordings a caller must not silently substitute instead of
the one actually authorized. `"block"` is not itself listed as a "prohibited claim"
since it is the terminal fallback, not an assertive claim being made.

## `residual_unknowns` field

Populated only for `block` (states the claim/surface remains unresolved) and `qualify`
(states the claim is evidenced but not proven to assertion strength). Empty for
`assert`, `omit`, and `not_applicable`, since those are affirmatively-resolved outcomes
with no residual gap being reported.
