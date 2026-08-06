"""Allocate verified template documentation links within the README link budget."""

from __future__ import annotations

from typing import cast

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.allocation import resolve_link_budget
from readme_agent.links.catalog import normalize_target_url
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1
from readme_agent.links.fact_owned_targets import accepted_fact_owned_targets
from readme_agent.links.occurrences import find_aspose_link_occurrences
from readme_agent.presentation.verified_template_documentation import (
    DOCUMENTATION_SURFACE_ORDER,
    DocumentationSurface,
)
from readme_agent.registry.models import LinkAllocationPolicyV1


def documentation_link_limit(
    candidate: str,
    facts: ProductFactsV2,
    catalogs: AsposeLinkCatalogSetV1,
    policy: LinkAllocationPolicyV1,
    *,
    verified_code_sha256s: set[str],
) -> int:
    """Return the maximum ordered documentation roots that fit all ceilings."""

    budget = resolve_link_budget(
        policy,
        candidate,
        verified_code_sha256s=verified_code_sha256s,
    )
    owned = accepted_fact_owned_targets(facts, catalogs)
    owned_urls = set(owned)
    occurrences = find_aspose_link_occurrences(candidate)
    non_documentation = [
        occurrence for occurrence in occurrences if occurrence.normalized_url not in owned_urls
    ]
    remaining_total = max(0, budget.max_total - len(non_documentation))
    non_documentation_org = sum(
        occurrence.parent_domain == "aspose.org" for occurrence in non_documentation
    )
    remaining_org = max(
        0,
        budget.domain_maxima["aspose.org"] - non_documentation_org,
    )
    non_documentation_surfaces = {
        surface: sum(occurrence.surface == surface for occurrence in non_documentation)
        for surface in DOCUMENTATION_SURFACE_ORDER
    }
    remaining_surfaces = {
        surface: max(0, budget.surface_maxima[surface] - non_documentation_surfaces[surface])
        for surface in DOCUMENTATION_SURFACE_ORDER
    }
    available: list[tuple[DocumentationSurface, str]] = []
    for target in owned.values():
        record = catalogs.aspose_org.records.get(target.record_id)
        if record is None or record.surface not in DOCUMENTATION_SURFACE_ORDER:
            continue
        available.append((cast(DocumentationSurface, record.surface), record.url))
    ordered_records = sorted(
        available,
        key=lambda item: (
            DOCUMENTATION_SURFACE_ORDER.index(item[0]),
            normalize_target_url(item[1]),
        ),
    )
    selected = 0
    for surface, _url in ordered_records:
        if selected >= remaining_total or selected >= remaining_org:
            break
        if remaining_surfaces[surface] <= 0:
            continue
        selected += 1
        remaining_surfaces[surface] -= 1
    return selected


__all__ = ["documentation_link_limit"]
