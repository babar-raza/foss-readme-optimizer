"""Project accepted section-cluster prose into deterministic template slots."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.specialists.section_authoring_contracts import (
    SectionAuthoringDocumentV1,
    SectionClusterUnitV1,
)


@dataclass(frozen=True)
class AuthoredSlotV1:
    markdown: str
    fact_fields: tuple[str, ...]


def _belongs_to(target_section_id: str, section_id: str) -> bool:
    return target_section_id == section_id or target_section_id.startswith(f"{section_id}-")


def authored_unit_markdown(section_id: str, unit: SectionClusterUnitV1) -> str:
    """Render one accepted unit exactly as the template overlay renders it."""

    if section_id == "key_capabilities":
        return f"- **{unit.heading.strip().rstrip('.')}** - {unit.text.strip()}"
    return unit.text.strip()


def authored_slot(
    document: SectionAuthoringDocumentV1 | None,
    facts: ProductFactsV2,
    section_id: str,
) -> AuthoredSlotV1 | None:
    """Return only complete, exact-dependency authored prose for one template slot."""

    if document is None:
        return None
    if not document.complete:
        raise ValueError("incomplete section authoring cannot enter a README candidate")
    if document.org_repo != facts.org_repo or document.facts_hash != facts.canonical_hash():
        raise ValueError("section authoring document does not match candidate facts")
    units = [
        unit
        for outcome in document.outcomes
        if _belongs_to(outcome.target_section_id, section_id)
        for unit in outcome.result.units
    ]
    if not units:
        return None
    fact_ids = list(dict.fromkeys(fact_id for unit in units for fact_id in unit.fact_ids))
    fields = tuple(dict.fromkeys(facts.fact_by_id(fact_id).field for fact_id in fact_ids))
    if section_id == "key_capabilities":
        markdown = "\n".join(authored_unit_markdown(section_id, unit) for unit in units)
    else:
        markdown = "\n\n".join(unit.text.strip() for unit in units)
    return AuthoredSlotV1(markdown=markdown, fact_fields=fields)


__all__ = ["AuthoredSlotV1", "authored_slot", "authored_unit_markdown"]
