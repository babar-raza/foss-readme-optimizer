"""Resolve exact Aspose targets owned by accepted product facts."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.links.catalog import normalize_target_url
from readme_agent.links.catalog_models import AsposeLinkCatalogSetV1

_DOCUMENTATION_FIELD = "documentation.links"
_DOCUMENTATION_LOCATION = "data/aspose_org_links.json"
_DOCUMENTATION_SURFACES = frozenset({"docs", "kb", "reference"})


@dataclass(frozen=True)
class FactOwnedAsposeTarget:
    """One exact catalog target whose candidate use is owned by an accepted fact."""

    fact_id: str
    record_id: str
    url: str


def accepted_fact_owned_targets(
    facts: ProductFactsV2,
    catalogs: AsposeLinkCatalogSetV1,
) -> dict[str, FactOwnedAsposeTarget]:
    """Return source-catalog documentation roots only after exact fact/catalog agreement."""

    try:
        fact = facts.selected_fact(_DOCUMENTATION_FIELD)
        identity = facts.selected_fact("product.identity")
    except KeyError:
        return {}
    source_revision = fact.source.source_revision
    if (
        fact.verification_state != "verified"
        or fact.has_unresolved_conflict
        or fact.source.source_type != "external_registry"
        or fact.source.location != _DOCUMENTATION_LOCATION
        or source_revision is None
        or not source_revision.startswith("sha256:")
        or not isinstance(fact.value, list)
        or identity.verification_state != "verified"
        or identity.has_unresolved_conflict
        or not isinstance(identity.value, dict)
    ):
        return {}
    family = str(identity.value.get("family") or "").casefold()
    platform = str(identity.value.get("platform") or "").casefold()
    repository = str(identity.value.get("repository") or "")
    repo_name = repository.split("/", 1)[-1] if "/" in repository else ""
    if not family or not platform or not repo_name or repository != facts.org_repo:
        return {}

    accepted: dict[str, FactOwnedAsposeTarget] = {}
    for value in fact.value:
        if not isinstance(value, dict):
            continue
        record_id = value.get("record_id")
        url = value.get("url")
        surface = value.get("surface")
        if (
            not isinstance(record_id, str)
            or not isinstance(url, str)
            or surface not in _DOCUMENTATION_SURFACES
            or value.get("family") != family
            or str(value.get("platform") or "").casefold() != platform
            or value.get("product") != repo_name
        ):
            return {}
        record = catalogs.aspose_org.records.get(record_id)
        if (
            record is None
            or record.surface != surface
            or record.parent_domain != "aspose.org"
            or record.source_type != "source_tree"
            or record.content_evidence != "source_body"
            or record.family != family
            or platform not in record.platforms
            or record.url != url
            or record.title != value.get("title")
            or record.source_location != value.get("source_location")
            or record.source_revision_or_hash != value.get("source_revision_or_hash")
        ):
            return {}
        normalized = normalize_target_url(url)
        if normalized in accepted:
            return {}
        accepted[normalized] = FactOwnedAsposeTarget(
            fact_id=fact.fact_id,
            record_id=record.record_id,
            url=record.url,
        )
    return accepted


__all__ = ["FactOwnedAsposeTarget", "accepted_fact_owned_targets"]
