"""Render documentation catalog facts into the verified presentation template."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from readme_agent.facts.schema_v2 import ProductFactsV2

DocumentationSurface = Literal["docs", "reference", "kb"]
DOCUMENTATION_SURFACE_ORDER: tuple[DocumentationSurface, ...] = (
    "docs",
    "kb",
    "reference",
)
_SURFACE_PRESENTATION = {
    "docs": (
        "Getting started guide",
        "installation, walkthroughs, and feature guides for this library",
    ),
    "kb": (
        "How-to guides and FAQ",
        "task-focused answers for common product questions",
    ),
    "reference": (
        "Full API reference",
        "the complete browsable reference for the public API",
    ),
}
_CATALOG_LOCATION = "data/aspose_org_links.json"


def _accepted_catalog_rows(facts: ProductFactsV2) -> list[dict[str, object]]:
    try:
        fact = facts.selected_fact("documentation.links")
    except KeyError:
        return []
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or fact.source.source_type != "external_registry"
        or fact.source.location != _CATALOG_LOCATION
        or not isinstance(fact.value, list)
    ):
        return []
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for value in fact.value:
        if not isinstance(value, dict):
            continue
        surface = value.get("surface")
        url = value.get("url")
        if surface not in DOCUMENTATION_SURFACE_ORDER or not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != f"{surface}.aspose.org":
            continue
        if not all(
            isinstance(value.get(field), str) and str(value[field]).strip()
            for field in (
                "record_id",
                "source_location",
                "source_revision_or_hash",
                "title",
                "family",
                "platform",
                "product",
            )
        ):
            continue
        key = (surface, url)
        if key in seen:
            continue
        seen.add(key)
        rows.append(value)
    return rows


def documentation_resources_markdown(
    facts: ProductFactsV2,
    *,
    link_limit: int | None = None,
) -> str | None:
    """Render accepted docs, knowledge-base, and API-reference catalog rows only."""

    rows = _accepted_catalog_rows(facts)
    if not rows:
        return None
    ordered = sorted(
        rows,
        key=lambda row: (
            DOCUMENTATION_SURFACE_ORDER.index(str(row["surface"])),
            str(row["url"]),
        ),
    )
    if link_limit is not None:
        ordered = ordered[: max(0, link_limit)]
    if not ordered:
        return None
    resources = []
    for row in ordered:
        label, purpose = _SURFACE_PRESENTATION[str(row["surface"])]
        resources.append(f"- **[{label}]({row['url']})** - {purpose}.")
    identity = facts.selected_fact("product.identity")
    identity_value = identity.value if isinstance(identity.value, dict) else {}
    repository = str(identity_value.get("repository") or facts.org_repo).strip()
    if (
        identity.verification_state in {"verified", "policy_approved"}
        and not identity.has_unresolved_conflict
        and len(repository.split("/")) == 2
    ):
        resources.append(
            f"- Found a bug or have a feature request? "
            f"[Open an issue](https://github.com/{repository}/issues) on GitHub."
        )
    return "\n".join(resources)


__all__ = [
    "DOCUMENTATION_SURFACE_ORDER",
    "DocumentationSurface",
    "documentation_resources_markdown",
]
