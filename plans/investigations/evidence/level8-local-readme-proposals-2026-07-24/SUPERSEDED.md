# Superseded (2026-07-24) — candidates built from pre-resolver-fix facts

These three README candidates were rendered from facts captured before the Maven resolver fix
(see `level8-local-immutable-snapshot-and-facts-2026-07-24/SUPERSEDED.md`). All three
`installation.verified_acquisition` facts wrongly say `method: "source_build"`, so all three
candidates strip a real, published Maven `<dependency>` block/badge and substitute a source-build
install path the package doesn't need. Each bundle's own `independent-review.json` was also
producer-self-written (the `VERIFIER-BUILT-NOT-WIRED` gap, closed 2026-07-24 in commit `de7ff3d`),
so its `"accepted"` verdict was never independently confirmed.

Preserved for history (`GOV-003`/`GOV-017`), not deleted or edited.

Superseding evidence:

- `plans/investigations/evidence/package-acquisition-ground-truth-2026-07-24/` — the authoritative
  portfolio matrix.
- `plans/investigations/evidence/level8-local-readme-proposals-corrected-acquisition-2026-07-24/`
  — candidates re-rendered from corrected facts, independently verified (producer defers to the
  real `verify_readme_proposal_bundle()`, plus a separate standalone re-verification run), and the
  Cells/PDF Java bundles are `accepted` and keep their correct Maven install. The 3D Java bundle is
  honestly `rejected` on an unrelated, pre-existing gap (`FACT-014`: this execution environment
  lacks the Java 21 toolchain 3D's example needs) -- its acquisition fix is independently confirmed
  correct regardless (`acquisition_matches_live_registry: true`).
