"""Build complete typed inventories from authorized repository sources."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, cast

from readme_agent.registry.discovery_models import (
    DiscoveryClassification,
    DiscoveryDisposition,
    DiscoveryInventoryV1,
    DiscoveryObservationV1,
    DiscoverySourceResultV1,
    DiscoverySourceV1,
)

ScanOrganization = Callable[..., list[dict]]
ClassifyRepository = Callable[[str], tuple[str, str] | None]


def inventory_sources(
    families: list[dict],
    *,
    scan_organization: ScanOrganization,
    classify_repository: ClassifyRepository,
    token: str | None = None,
    max_rate_limit_wait_seconds: float | None = None,
) -> DiscoveryInventoryV1:
    """Inventory every visible repository; classification never filters observations."""

    captured_at = datetime.now(UTC).isoformat()
    source_results: list[DiscoverySourceResultV1] = []
    observations: list[DiscoveryObservationV1] = []

    for family in families:
        source = DiscoverySourceV1.from_family(family)
        if not source.enabled:
            continue
        try:
            repositories = scan_organization(
                source.organization,
                token=token,
                max_rate_limit_wait_seconds=max_rate_limit_wait_seconds,
            )
        except Exception as exc:  # noqa: BLE001 -- failure is retained as typed source data
            source_results.append(
                DiscoverySourceResultV1(
                    source=source,
                    status="failed",
                    observed_at=captured_at,
                    observation_count=0,
                    error=str(exc),
                )
            )
            continue

        source_observations = [
            _observation(
                source,
                raw,
                observed_at=captured_at,
                classify_repository=classify_repository,
            )
            for raw in repositories
        ]
        observations.extend(source_observations)
        source_results.append(
            DiscoverySourceResultV1(
                source=source,
                status="complete",
                observed_at=captured_at,
                observation_count=len(source_observations),
            )
        )

    observations.sort(key=lambda item: (item.source_id, item.full_name.lower()))
    return DiscoveryInventoryV1(
        captured_at=captured_at,
        sources=source_results,
        observations=observations,
        complete=all(source.status == "complete" for source in source_results),
    )


def _observation(
    source: DiscoverySourceV1,
    raw: dict,
    *,
    observed_at: str,
    classify_repository: ClassifyRepository,
) -> DiscoveryObservationV1:
    pair = classify_repository(str(raw["name"]))
    classification: DiscoveryClassification = "unmatched"
    classification_reason = "repository name does not match a known product/platform convention"
    disposition: DiscoveryDisposition = "review_required"
    family = None
    platform = None

    if pair is not None:
        candidate_family, candidate_platform = pair
        if source.family_hint is not None and candidate_family != source.family_hint:
            classification = "ambiguous"
            classification_reason = (
                f"name-derived family {candidate_family!r} conflicts with "
                f"source family {source.family_hint!r}"
            )
        else:
            classification = "matched"
            classification_reason = "repository name and authorized source agree"
            disposition = "admit_candidate"
            family = candidate_family
            platform = candidate_platform

    name = str(raw["name"])
    full_name = str(raw.get("full_name") or f"{source.organization}/{name}")
    raw_visibility = str(raw.get("visibility") or "unknown")
    visibility = (
        cast(Literal["public", "private", "internal", "unknown"], raw_visibility)
        if raw_visibility in {"public", "private", "internal", "unknown"}
        else "unknown"
    )
    return DiscoveryObservationV1(
        source_id=source.source_id,
        provider_repository_id=raw["id"],
        provider_node_id=str(raw["node_id"]),
        full_name=full_name,
        name=name,
        html_url=str(raw["html_url"]),
        clone_url=str(raw["clone_url"]),
        visibility=visibility,
        default_branch=raw.get("default_branch"),
        archived=bool(raw.get("archived")),
        pushed_at=raw.get("pushed_at"),
        updated_at=raw.get("updated_at"),
        topics=list(raw.get("topics") or []),
        primary_language=raw.get("language"),
        observed_at=observed_at,
        classification=classification,
        classification_reason=classification_reason,
        disposition=disposition,
        family=family,
        platform=platform,
    )
