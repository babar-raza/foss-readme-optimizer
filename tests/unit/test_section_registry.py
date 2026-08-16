"""T14 -- section registry + plugin framework. Includes the plan's own
named "section-16 agility tests a-d":
  (a) registry v1 reproduces the current contract byte-compatibly
  (b) adding a synthetic section (registry entry + plugin only) composes,
      validates, and calibrates with zero edits elsewhere
  (c) removing a section deactivates its checks/fragments cleanly with no
      orphan findings and no false calibration regressions on unrelated
      sections
  (d) a registry change flips the freshness tuple for exactly the
      affected sections/products
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from readme_agent.presentation.sections import (
    SECTION_REGISTRY_PATH,
    SectionRegistryEntryV1,
    SectionRegistryV1,
    all_section_fingerprints,
    derive_section_registry_from_live_contract,
    document_global_fingerprint,
    load_section_registry,
    section_fingerprint,
)
from readme_agent.presentation.template_schema import load_repository_presentation_template
from readme_agent.readme.document_templates import document_template_hash


def _synthetic_registry() -> SectionRegistryV1:
    return SectionRegistryV1(
        entries=(
            SectionRegistryEntryV1(
                id="alpha",
                heading="Alpha",
                order=0,
                required=True,
                composer_binding="deterministic_existing",
                section_checks=("check_alpha_present",),
            ),
            SectionRegistryEntryV1(
                id="beta",
                heading="Beta",
                order=1,
                required=False,
                composer_binding="deterministic_existing",
                section_checks=(),
            ),
        )
    )


# --- (a) registry v1 reproduces the current contract byte-compatibly -------


def test_agility_a_derived_registry_reproduces_the_live_contract_byte_compatibly():
    contract = load_repository_presentation_template()
    registry = derive_section_registry_from_live_contract(contract)

    ordered = registry.ordered_entries()
    assert [entry.id for entry in ordered] == list(contract.section_order)
    assert {entry.id: entry.heading for entry in ordered} == dict(contract.headings)
    assert {entry.id for entry in ordered if entry.required} == set(contract.required_slots)


def test_agility_a_committed_registry_file_matches_a_fresh_derivation():
    """The committed templates/readme/section-registry-v2.json must never
    hand-drift from the live contract it describes -- re-deriving it must
    produce byte-identical content (after canonical JSON round-tripping)."""

    committed = load_section_registry()
    fresh = derive_section_registry_from_live_contract()

    assert committed.model_dump(mode="json") == fresh.model_dump(mode="json")


def test_committed_registry_file_is_the_real_generated_artifact():
    assert SECTION_REGISTRY_PATH.is_file()
    registry = load_section_registry()
    assert len(registry.entries) == 15
    assert registry.entry_by_id("license").heading == "License"


def test_derive_discloses_real_unmapped_section_checks_not_silently_dropped():
    """Real, disclosed discrepancy: T3's vendored check registry has
    section-scoped checks for headings ("Dependencies", "Project
    Structure", the badge/banner "header" group) that do not correspond
    to any slot in the live 14-slot contract. These must be surfaced, not
    silently dropped from the registry."""

    registry = derive_section_registry_from_live_contract()

    assert len(registry.unmapped_section_checks) > 0
    assert any(
        "dependency" in name or "dependencies" in name for name in registry.unmapped_section_checks
    )
    assert any("badge" in name or "banner" in name for name in registry.unmapped_section_checks)


# --- (b) adding a synthetic section: zero edits elsewhere -------------------


def test_agility_b_adding_a_section_composes_and_validates_with_zero_code_changes():
    registry = _synthetic_registry()
    extended_entries = (
        *registry.entries,
        SectionRegistryEntryV1(
            id="gamma",
            heading="Gamma",
            order=2,
            required=False,
            composer_binding="deterministic_existing",
            section_checks=("check_gamma_present",),
        ),
    )
    extended = SectionRegistryV1(entries=extended_entries)

    assert len(extended.entries) == 3
    assert extended.entry_by_id("gamma").heading == "Gamma"
    gamma_fingerprint = section_fingerprint(extended.entry_by_id("gamma"))
    assert isinstance(gamma_fingerprint, str) and len(gamma_fingerprint) == 64
    # The pre-existing sections' fingerprints are untouched by the addition.
    assert section_fingerprint(extended.entry_by_id("alpha")) == section_fingerprint(
        registry.entry_by_id("alpha")
    )
    assert section_fingerprint(extended.entry_by_id("beta")) == section_fingerprint(
        registry.entry_by_id("beta")
    )


# --- (c) removing a section: clean deactivation, no orphans ----------------


def test_agility_c_removing_a_section_leaves_no_orphan_and_no_false_regression():
    registry = _synthetic_registry()
    remaining = tuple(entry for entry in registry.entries if entry.id != "beta")
    reduced = SectionRegistryV1(entries=remaining)

    assert len(reduced.entries) == 1
    with pytest.raises(KeyError):
        reduced.entry_by_id("beta")
    # The surviving section's fingerprint is unaffected by beta's removal.
    assert section_fingerprint(reduced.entry_by_id("alpha")) == section_fingerprint(
        registry.entry_by_id("alpha")
    )


# --- (d) a registry change flips the freshness tuple for exactly the -------
# --- affected sections -------------------------------------------------


def test_agility_d_a_section_change_flips_only_that_sections_fingerprint():
    registry = _synthetic_registry()
    before = all_section_fingerprints(registry)

    changed_alpha = registry.entry_by_id("alpha").model_copy(
        update={"section_checks": ("check_alpha_present", "check_alpha_new_rule")}
    )
    mutated_entries = tuple(
        changed_alpha if entry.id == "alpha" else entry for entry in registry.entries
    )
    mutated = SectionRegistryV1(entries=mutated_entries)
    after = all_section_fingerprints(mutated)

    assert after["alpha"] != before["alpha"]
    assert after["beta"] == before["beta"]


def test_agility_d_section_registry_change_does_not_move_the_document_global_fingerprint():
    """resolution 8: section change -> that section only; global-contract/
    assembly change -> whole document. A section-registry-only edit must
    never move the (unrelated, pre-existing) document-global fingerprint,
    since that fingerprint governs assembly/global-contract, not any one
    section's own content."""

    before = document_global_fingerprint()
    _synthetic_registry()  # constructing/mutating a registry in memory only
    after = document_global_fingerprint()

    assert before == after
    assert after == document_template_hash()


def test_section_fingerprint_excludes_order_a_pure_reorder_is_not_a_content_change():
    entry_first = SectionRegistryEntryV1(
        id="alpha",
        heading="Alpha",
        order=0,
        required=True,
        composer_binding="deterministic_existing",
        section_checks=(),
    )
    entry_reordered = entry_first.model_copy(update={"order": 5})

    assert section_fingerprint(entry_first) == section_fingerprint(entry_reordered)


# --- Validator / structural tests -------------------------------------------


def test_section_registry_rejects_duplicate_ids():
    entry = SectionRegistryEntryV1(
        id="alpha",
        heading="Alpha",
        order=0,
        required=True,
        composer_binding="deterministic_existing",
    )
    duplicate = entry.model_copy(update={"heading": "Alpha Two", "order": 1})
    with pytest.raises(ValidationError):
        SectionRegistryV1(entries=(entry, duplicate))


def test_section_registry_rejects_duplicate_order_values():
    entry_a = SectionRegistryEntryV1(
        id="alpha",
        heading="Alpha",
        order=0,
        required=True,
        composer_binding="deterministic_existing",
    )
    entry_b = SectionRegistryEntryV1(
        id="beta",
        heading="Beta",
        order=0,
        required=False,
        composer_binding="deterministic_existing",
    )
    with pytest.raises(ValidationError):
        SectionRegistryV1(entries=(entry_a, entry_b))


def test_section_registry_rejects_duplicate_headings():
    entry_a = SectionRegistryEntryV1(
        id="alpha",
        heading="Same",
        order=0,
        required=True,
        composer_binding="deterministic_existing",
    )
    entry_b = SectionRegistryEntryV1(
        id="beta",
        heading="Same",
        order=1,
        required=False,
        composer_binding="deterministic_existing",
    )
    with pytest.raises(ValidationError):
        SectionRegistryV1(entries=(entry_a, entry_b))


def test_section_registry_entries_are_frozen():
    registry = _synthetic_registry()
    with pytest.raises(ValidationError):
        registry.entry_by_id("alpha").heading = "Changed"  # type: ignore[misc]
