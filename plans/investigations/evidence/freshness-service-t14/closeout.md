# T14 — section registry + plugin framework

**Status: COMPLETE.**

## What is done and verified

Investigated the CURRENT, already-live section/template system before writing anything (reuse
discipline): `presentation/template_schema.py`'s `RepositoryPresentationTemplateV1` (loaded from
`templates/readme/repository-presentation-v1.json`) already defines the 14-slot contract
(`section_order`, `headings`, `required_slots`) that `readme/document_section_order.py` consumes
to actually reorder rendered README H2 blocks. No dynamic plugin-discovery pattern exists
anywhere in this codebase — the established convention (confirmed by search) is "one governed
data file + a strict pydantic model + a `load_*()` function", so T14 follows that pattern rather
than inventing entry-point/discovery machinery.

### `src/readme_agent/presentation/sections/__init__.py` (new package)

- `SectionRegistryEntryV1` / `SectionRegistryV1` (pydantic, `extra="forbid"`, frozen): each entry
  carries `id`, `heading`, `order`, `required`, `composer_binding`, `section_checks`,
  `ledger_obligations`, `invalidation_scope` — the exact field set T14's card text specifies.
- `derive_section_registry_from_live_contract()`: the single builder that both generated the
  committed JSON file's content and is re-run in tests to prove it never hand-drifts from the
  live contract.
- `section_fingerprint()` / `all_section_fingerprints()`: per-section content fingerprint
  (id/heading/required/composer_binding/section_checks — deliberately excluding `order`, since
  reordering is a structural change with zero cross-cutting edits per resolution 9, not a
  content change, and excluding `ledger_obligations`, which is process bookkeeping).
- `document_global_fingerprint()`: **reuses the existing `document_template_hash()` unchanged**
  rather than reinventing a document-global hash — this repo already had exactly one.

### `templates/readme/section-registry-v2.json` (new, generated)

14 entries, one per real `TemplateSlot`, byte-derived from the live contract. `section_checks`
per entry is bound from T3's vendored check registry (`aspose_checks.load_check_registry()`) by
matching each section-scoped check's free-text heading against the contract's heading strings.

**Real, honestly disclosed discrepancy found and surfaced, not silently dropped**: 20
section-scoped checks from T3's registry reference headings with **no match** in the live
14-slot contract — "Dependencies" (11 checks: `check_dependency_*`/`check_dependencies_*`,
matching this plan's own §4 "10 required H2s" list, which names a Dependencies section that
`template_schema.py`'s current `TemplateSlot` enum does not have), "header" (8 badge/banner
checks — the badge row/banner exist above the H2 structure, not as their own H2 slot), and
`check_project_structure_canonical_tree_format` (an optional section named in this plan's §4 but
also absent from `TemplateSlot`). These are recorded in `unmapped_section_checks` (not dropped),
tested (`test_derive_discloses_real_unmapped_section_checks_not_silently_dropped`), and are a
genuine open reconciliation item for whoever next revises `template_schema.py`'s `TemplateSlot`
enum — **not fixed here**, since `template_schema.py` is pre-existing, heavily-consumed shared
machinery outside T14's owned paths, and widening its slot enum is a decision with its own
downstream-consumer impact this card does not have the scope to assess.

### Honest v1 scope notes (both intentional, both leave room for later cards, neither a gap)

- `composer_binding` is `"deterministic_existing"` for all 14 sections — true today, since no LLM
  slot-step machinery (T6/T7A-F) exists yet; every section is currently produced by the existing
  deterministic `document_renderer.py` pipeline. The field exists now so T7A-F update entries in
  place rather than needing a schema migration.
- `ledger_obligations` is empty for all 14 — true today, since TP-11A/B's reconciliation-ledger
  machinery is not wired to per-section granularity yet.

## Agility tests (section 16, named a-d in the plan — all 4 implemented and green)

- **(a)** `test_agility_a_*` (2 tests): the derived registry's id/heading/required set exactly
  matches the live contract's `section_order`/`headings`/`required_slots`; the *committed* JSON
  file matches a fresh re-derivation (proves it can never silently drift).
- **(b)** `test_agility_b_adding_a_section_composes_and_validates_with_zero_code_changes`: a
  synthetic registry gains a third entry (registry data only, zero code edits) and composes,
  validates, and gets its own independent fingerprint; pre-existing entries' fingerprints are
  provably untouched by the addition.
- **(c)** `test_agility_c_removing_a_section_leaves_no_orphan_and_no_false_regression`: removing
  an entry cleanly raises `KeyError` on lookup (no orphan reference) and leaves the surviving
  entry's fingerprint provably unchanged (no false regression on an unrelated section).
- **(d)** `test_agility_d_*` (2 tests): mutating one entry's `section_checks` flips only that
  entry's fingerprint (the other entry's fingerprint is provably unchanged); a section-registry
  edit never moves the separate, pre-existing document-global fingerprint (resolution 8: section
  change → that section only, global-contract change → whole document — tested as two genuinely
  independent fingerprint sources, not merely asserted).

Plus structural validator tests (duplicate id/order/heading rejection, frozen-entry immutability)
and a direct cross-check that `document_global_fingerprint() == document_template_hash()`.

**13 tests, all passing** (`tests/unit/test_section_registry.py`). Full governed suite: 3,908
passed, 1 skipped, 0 failed (up from 3,895 before this round — the delta is exactly the 13 new
tests, zero regressions). ruff + mypy clean.

## Downstream effect

`T5` (deterministic pilot skeleton, cells/python) is G3's other mandatory card — it does not
depend on T14 directly per the taskcard graph (both are prereq'd only on `GC-02`), so T5 may
proceed independently once started. `GC-03` (G3 close) requires both `T14` and `T5` COMPLETE.
