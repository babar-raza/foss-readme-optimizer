# Superseded (2026-07-24) — captured before the resolver fix

This bundle's package-acquisition results are **wrong**: `verify_package_acquisition` queried
`search.maven.org` (a Solr index that does not index the `org.aspose` group at all), so it
falsely reported every Java pilot's Maven package as `NOT_PUBLISHED`. All three packages
(`org.aspose:aspose-cells-foss`, `aspose-3d-foss`, `aspose-pdf-foss`) are actually published on
Maven Central.

Preserved for history (`GOV-003`/`GOV-017`), not deleted or edited. Do not treat any
`NOT_PUBLISHED`/`source_build`/`readme_claim_conflicts` finding in this bundle as current truth.

Superseding evidence:

- `plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/` — the authoritative
  portfolio matrix (all 31 `data/products.json` entries, live-verified against each ecosystem's
  real registry).
- `plans/investigations/evidence/level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24/`
  — the re-derived pilot facts/snapshot bundle.
