"""T14 -- section registry + plugin framework.

Follows this repo's established convention (`template_schema.py`,
`validation/aspose_checks/__init__.py`): one governed data file + a strict
pydantic model + a `load_*()` function. No dynamic plugin-discovery
machinery exists anywhere else in this codebase (searched for one before
writing this), so this does not invent one either -- "plugin" here means
"one registry entry"; adding/removing/reordering a section is
adding/removing/reordering one entry in the JSON file, with zero code
edits anywhere else (proven in `tests/unit/test_section_registry.py`'s
agility tests).

Section registry v1 (`templates/readme/section-registry-v2.json`)
byte-reproduces the CURRENT, already-live contract
(`presentation/template_schema.py`'s `RepositoryPresentationTemplateV1`,
loaded from `templates/readme/repository-presentation-v1.json`) as data:
`id`/`heading`/`order`/`required`. It adds the fields the existing
contract does not carry: `section_checks` (bound from T3's vendored check
registry by matching heading text), `composer_binding`,
`ledger_obligations`, `invalidation_scope`.

Honest v1 scope note: `composer_binding` is `"deterministic_existing"` for
every section today, because no LLM slot-step machinery (T6/T7A-F) exists
yet in this repo -- every section is currently produced by the existing
deterministic `document_renderer.py` pipeline. `ledger_obligations` is
empty for v1 for the same reason (TP-11A/B's reconciliation-ledger
machinery is not wired to per-section granularity yet). Both fields exist
now so future cards update entries in place rather than adding a schema
migration. `document_global_fingerprint()` deliberately reuses the
existing `document_template_hash()` unchanged -- this repo already has
exactly one whole-document/global-contract hash; T14 composes it with the
new per-section fingerprints below rather than reinventing it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.presentation.template_schema import (
    RepositoryPresentationTemplateV1,
    load_repository_presentation_template,
)
from readme_agent.readme.document_templates import document_template_hash
from readme_agent.validation.aspose_checks import AsposeCheckDescriptorV1, load_check_registry

# sections/__init__.py lives at src/readme_agent/presentation/sections/ --
# parents[4] is the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
SECTION_REGISTRY_PATH = _PROJECT_ROOT / "templates" / "readme" / "section-registry-v2.json"

ComposerBinding = Literal["deterministic_existing"]
InvalidationScope = Literal["section", "document"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SectionRegistryEntryV1(_StrictModel):
    id: str
    heading: str
    order: int = Field(ge=0)
    required: bool
    composer_binding: ComposerBinding
    section_checks: tuple[str, ...] = Field(default_factory=tuple)
    ledger_obligations: tuple[str, ...] = Field(default_factory=tuple)
    invalidation_scope: InvalidationScope = "section"


class SectionRegistryV1(_StrictModel):
    schema_version: Literal[1] = 1
    entries: tuple[SectionRegistryEntryV1, ...]
    # Section-scoped checks from T3's registry whose heading has no match
    # in the live contract (e.g. "Dependencies", "Project Structure" --
    # real, disclosed discrepancies between the vendored check names and
    # this repo's current 14-slot contract, never silently dropped).
    unmapped_section_checks: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _well_formed(self) -> SectionRegistryV1:
        ids = [entry.id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("section registry has duplicate section ids")
        orders = [entry.order for entry in self.entries]
        if len(orders) != len(set(orders)):
            raise ValueError("section registry has duplicate order values")
        headings = [entry.heading for entry in self.entries]
        if len(headings) != len(set(headings)):
            raise ValueError("section registry has duplicate headings")
        return self

    def entry_by_id(self, section_id: str) -> SectionRegistryEntryV1:
        for entry in self.entries:
            if entry.id == section_id:
                return entry
        raise KeyError(section_id)

    def ordered_entries(self) -> tuple[SectionRegistryEntryV1, ...]:
        return tuple(sorted(self.entries, key=lambda entry: entry.order))


def load_section_registry(path: Path = SECTION_REGISTRY_PATH) -> SectionRegistryV1:
    """Load and validate the section registry from disk."""

    return SectionRegistryV1.model_validate_json(path.read_text(encoding="utf-8"))


def derive_section_registry_from_live_contract(
    contract: RepositoryPresentationTemplateV1 | None = None,
    check_registry: dict[str, AsposeCheckDescriptorV1] | None = None,
) -> SectionRegistryV1:
    """Derive a `SectionRegistryV1` from the CURRENT live contract
    (`template_schema.py`) plus T3's vendored check registry -- the same
    builder that generated `section-registry-v2.json`'s committed content
    and that proves, in tests, it byte-reproduces the live contract
    (never hand-typed in parallel and left to drift)."""

    contract = contract or load_repository_presentation_template()
    check_registry = check_registry if check_registry is not None else load_check_registry()

    heading_to_slot = {heading: slot for slot, heading in contract.headings.items()}
    checks_by_heading: dict[str, list[str]] = {}
    unmapped: list[str] = []
    for name, descriptor in check_registry.items():
        if descriptor.scope != "section" or descriptor.section is None:
            continue
        if descriptor.section in heading_to_slot:
            checks_by_heading.setdefault(descriptor.section, []).append(name)
        else:
            unmapped.append(name)

    entries = tuple(
        SectionRegistryEntryV1(
            id=slot,
            heading=contract.headings[slot],
            order=order,
            required=slot in contract.required_slots,
            composer_binding="deterministic_existing",
            section_checks=tuple(sorted(checks_by_heading.get(contract.headings[slot], []))),
        )
        for order, slot in enumerate(contract.section_order)
    )
    return SectionRegistryV1(entries=entries, unmapped_section_checks=tuple(sorted(unmapped)))


# Fields that determine a section's rendered content/validation surface.
# `order` is deliberately excluded -- reordering is a structural,
# zero-cross-cutting-edit change (resolution 9's "reordering = the order
# field"), not a content change. `ledger_obligations` is process
# bookkeeping, not renderable content, so it is excluded too.
_FINGERPRINT_FIELDS = ("id", "heading", "required", "composer_binding", "section_checks")


def section_fingerprint(entry: SectionRegistryEntryV1) -> str:
    """Content-relevant fingerprint for one section."""

    payload = {field: getattr(entry, field) for field in _FINGERPRINT_FIELDS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=list)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def all_section_fingerprints(registry: SectionRegistryV1) -> dict[str, str]:
    return {entry.id: section_fingerprint(entry) for entry in registry.entries}


def document_global_fingerprint() -> str:
    """The document-global fingerprint (resolution 8): reuses the
    existing `document_template_hash()` unchanged."""

    return document_template_hash()


__all__ = [
    "SECTION_REGISTRY_PATH",
    "ComposerBinding",
    "InvalidationScope",
    "SectionRegistryEntryV1",
    "SectionRegistryV1",
    "all_section_fingerprints",
    "derive_section_registry_from_live_contract",
    "document_global_fingerprint",
    "load_section_registry",
    "section_fingerprint",
]
