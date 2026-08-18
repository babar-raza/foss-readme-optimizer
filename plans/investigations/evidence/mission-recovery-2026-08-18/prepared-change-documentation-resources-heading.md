# Prepared change: `Documentation and Resources` → `Documentation & Resources` (queued)

The universal 7/7 parity divergence: aspose.org's contract (its `_REQUIRED_SECTIONS` and every
shipped candidate) uses `## Documentation & Resources`; every candidate of ours renders
`## Documentation and Resources`. The imported detectors (`facts/aspose_detectors.py`) already
target the ampersand form — our template layer is the odd one out.

## Exact touch set (verified by grep, 2026-08-18)

1. `templates/readme/repository-presentation-v1.json` — slot heading
   `"documentation_resources": "Documentation and Resources"`; bump `template_version`
   1.20.0 → 1.21.0.
2. `templates/readme/section-registry-v2.json` — the same heading in the registry entry
   (keeps `section_fingerprint()` honest).
3. `src/readme_agent/presentation/verified_source_detail_routing.py` — two routing strings.
4. `src/readme_agent/presentation/verified_template_api_reference.py:303` — prose reference.
5. `src/readme_agent/validation/aspose_checks/__init__.py:144` — fixture text.
6. Tests: grep `"Documentation and Resources"` under tests/ and update expectations; the
   characterization-hash tests will need their recorded constants advanced (template change is
   a real semantic delta — advance deliberately, do not chase).

## Invalidation expectation (say it before running it)

Template hash + section fingerprint change ⇒ `PLAN_READY`-scope invalidation for every
repository (VALID_UPDATE_AVAILABLE/recompose of presentation-dependent stages; facts stay
valid). Run it as its own gated change AFTER the current pass + worktree merges, with one
canary (pdf — the at-parity repo) before any portfolio pass.

## Explicitly not bundled

Anchor slugs derived from the heading (check `anchor_destination_consistency` and
`contextual_links` behavior for `#documentation--resources` vs `#documentation-and-resources`)
must be verified in the same change — a heading rename that breaks Navigation anchors would
trade one universal divergence for another.
