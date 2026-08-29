"""Single source of truth for reviewer-section-name to authoring-slot mapping.

Split out from `section_authoring_repair.py` so `readme_repair_validation.py` can resolve a
finding's slot too (to report whether that slot's author was actually attempted) without an
import cycle -- `section_authoring_repair.py` already imports from `readme_repair_validation.py`.
"""

from __future__ import annotations

_REVIEW_SECTION_TO_AUTHORING_SLOT = {
    "summary": "summary",
    "front-matter": "summary",
    "key-capabilities": "key_capabilities",
    "capabilities": "key_capabilities",
    "installation": "installation",
    "quick-start": "quick_start",
    "scope-and-limitations": "scope_and_limitations",
    "limitations": "scope_and_limitations",
}


def authoring_slot_for_section(section: str) -> str | None:
    """Only 6 of the reviewer's 13 section roots have a section-authoring slot
    (`ACL-REVIEW-REPAIR-SCOPE-MISMATCH`) -- `None` means the finding has no
    section-authoring repair route at all, not that the caller made a mistake."""

    return _REVIEW_SECTION_TO_AUTHORING_SLOT.get(section.strip().casefold().replace("_", "-"))
