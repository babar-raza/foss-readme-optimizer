# RED_TEST_PLAN -- OPT-CANONICAL-103-CHECK-GAP

Planning only (time-boxed audit, no implementation). Every test below is a red test today at optimizer pin
`aa998102191c530af4dca3a6895d62a4027a613e` -- named, located, and justified against actual current source,
not invented against an assumed one. None of these files were created or edited by this audit.

## 1. Canonical-parity gate (closes D12)

**File:** `tests/unit/test_aspose_checks_registry.py` (extends the existing registry-loader test module)

- `test_canonical_inventory_matches_committed_manifest_exactly`
  Loads a new committed `data/canonical_aspose_check_inventory.json` (103 names + canonical source sha256,
  per `DEFECT_GATE_MATRIX.json`'s own recommended fixture:
  `"A committed canonical_check_inventory.json with the 103 exact names and source SHA"`), AST-extracts the
  live vendored `check_*` names via `load_check_registry()`, and asserts
  `set(canonical_names) - set(vendored_names)` is **either empty or fully accounted for** by an explicit
  `not_applicable_for_readme_only_scope` bucket in `data/aspose_check_classification.json` (see test 3
  below) -- never silently absent. **Currently fails**: no such manifest is committed, and
  `test_registry_loads_the_complete_derived_inventory` only asserts `len(registry) >= 80`.

- `test_canonical_inventory_marks_issue_draft_checks_explicitly_not_applicable`
  Asserts `check_issue_draft_rejection_list` and `check_no_internal_details_leaked_into_issue_draft` exist in
  the canonical manifest but carry an explicit, governed `not_applicable_for_readme_only_scope` disposition
  (with a real reason string), not silent absence from the vendored registry. **Currently fails**: no such
  disposition bucket exists.

## 2. Per-missing-check ported red tests (closes 12 of the 14, once implemented)

**File:** `tests/unit/test_aspose_checks_missing_adaptation.py` (new file)

One `test_check_<name>_...` per ported check, each invoking the real function on a minimal real-text fixture
(same discipline as the existing `test_check_required_sections_real_invocation_finds_missing_sections`-style
tests already in `test_aspose_checks_registry.py`) and asserting it fires on a deliberately noncompliant
fixture and stays clean on a compliant one:

| Test name | Target |
|---|---|
| `test_check_additional_example_headings_real_invocation_flags_missing_heading` | `check_additional_example_headings` |
| `test_check_code_example_excluded_reason_citation_too_narrow_flags_underspecified_citation` | `check_code_example_excluded_reason_citation_too_narrow` |
| `test_check_content_unit_redundant_claim_verifiable_flags_unverifiable_redundant_claim` | `check_content_unit_redundant_claim_verifiable` |
| `test_check_dependency_development_claim_not_in_manifest_flags_unlisted_dev_dependency` | `check_dependency_development_claim_not_in_manifest` |
| `test_check_dependency_section_subheadings_present_real_invocation_flags_missing_subheading` | `check_dependency_section_subheadings_present` |
| `test_check_diagram_from_scratch_capability_labeled_real_invocation_on_missing_label` | `check_diagram_from_scratch_capability_labeled` |
| `test_check_diagram_label_geometry_real_invocation_on_malformed_layout` | `check_diagram_label_geometry` |
| `test_check_frozen_blocks_unchanged_flags_modified_protected_span` | `check_frozen_blocks_unchanged` |
| `test_check_image_content_unit_excluded_reason_verified_flags_unverified_exclusion` | `check_image_content_unit_excluded_reason_verified` |
| `test_check_no_upstream_issue_leaked_into_install_or_quickstart_flags_leaked_issue_text` | `check_no_upstream_issue_leaked_into_install_or_quickstart` |
| `test_check_scope_compliance_real_invocation_flags_noncompliant_scope_section` | `check_scope_compliance` |
| `test_check_seo_keyword_plan_usage_flags_unused_planned_keyword` | `check_seo_keyword_plan_usage` |

All 12 currently fail with `AttributeError`/`ImportError` (the functions do not exist anywhere in this repo
today -- confirmed: `grep -rn "def check_additional_example_headings\|def check_scope_compliance\|..." src`
returns nothing).

Registry-merge test (both files above depend on this):

- `test_load_check_registry_includes_adapted_checks_alongside_vendored`
  Once `src/readme_agent/validation/aspose_checks_adapted.py` exists,
  `load_check_registry()` must return **101** entries (89 vendored + 12 ported; the 2 issue-draft-only names
  are governed-N/A, not registered functions) with the vendored module itself byte-unchanged (`git diff`
  against `vendored_asposeorg/` empty) -- proves the "vendored, never hand-edited" invariant survives the
  port. **Currently fails**: the registry has no merge step; only the vendored module is scanned.

## 3. `check_banner_present` family/platform gap (closes GOV-014 / requirement 7)

**File:** `tests/unit/test_aspose_check_coverage.py` (extends the module the prior 907ac0847 fix already
extended) or a new `tests/unit/test_aspose_checks_bridge.py` if the bridge-specific surface grows enough to
warrant its own file.

- `test_real_kwargs_derives_family_platform_from_registry_when_no_imported_fact_present`
  Constructs a `ProductFactsV2` with **zero** `aspose.*` facts selected (the common case per GOV-014) plus an
  `org_repo` value that matches a real `data/products.json` entry (e.g. `"aspose-3d-foss/Aspose.3D-FOSS-for-Java"`
  -> `family="3d"`, `platform="java"`), and asserts `_real_kwargs` (or its post-fix successor) still produces
  non-`None` `family`/`platform`, so `check_banner_present` is **not** skipped. **Currently fails**:
  `_real_kwargs` has no `org_repo`/registry lookup path at all; it only ever reads `aspose.*` fact locations.

- `test_run_aspose_checks_does_not_skip_banner_present_for_a_synthetic_facts_free_candidate`
  End-to-end: `run_aspose_checks(candidate_text, facts=None or synthetic-only-facts)` with a registry-derived
  family/platform passed alongside; asserts `"check_banner_present" not in result.checks_skipped`.
  **Currently fails**: this is exactly the GOV-014-documented near-universal skip case (907ac0847's own
  commit message: "check_banner_present ... skips in nearly every non-full-portfolio run").

- `test_blocking_aspose_check_gaps_synthesizes_skip_not_only_error_once_family_platform_is_reliable`
  Once the family/platform derivation above lands, extend `blocking_aspose_check_gaps()` (already exists,
  already tested for the `error` outcome per 907ac0847) to also gate `outcome == "skip"` for
  `check_banner_present` specifically (or for any check whose declared parameters are now provably always
  derivable), without re-breaking the 36+ tests and the end-to-end supervisor-loop test the prior attempt
  broke (`test_local_poc_records_snapshot_and_profile_before_later_stages`). This test should assert both:
  the new skip-gating fires for a real missing-banner case, and the previously-broken synthetic-fixture tests
  still pass. **Currently not applicable** (the gate does not exist yet for skip) -- this is the regression
  guard for the eventual fix, written as a red test against the *current* narrowed `outcome == "error"`-only
  gate in `local_poc_acceptance_binding.py`.

## 4. Broad-gate parity for existing blocking checks (closes the other half of D11, §4A of REPORT.md)

**File:** `tests/unit/test_document_validation.py` (existing suite for `validate_readme_document_candidate`
-- exact filename to confirm at implementation time; if absent, add to the module housing
`document_validation.py`'s primary test coverage)

- `test_validate_readme_document_candidate_fails_closed_on_errored_blocking_check`
  Monkeypatches one of the 10 always-available-params blocking checks (e.g.
  `check_no_duplicate_badges_in_candidate`) to raise, calls `validate_readme_document_candidate` directly
  (not through `local_poc_acceptance_binding.py`), and asserts `valid is False` with a typed reason
  identifying the errored blocking check. **Currently fails**: `validate_readme_document_candidate` only
  ever inspects `result.findings` via `blocking_aspose_check_findings`, which is empty for an errored check,
  so `checks["aspose_checks"]` stays `True` and nothing else in that function's `errors` list catches it.

## Scope note

This plan intentionally does not propose tests for the 2 issue-draft-only missing checks as ported
functions (see REPORT.md §5/§6) -- their red test is the *classification* test in §1
(`test_canonical_inventory_marks_issue_draft_checks_explicitly_not_applicable`), not a function-invocation
test, since porting them would mean fabricating a producer this pipeline does not have.
