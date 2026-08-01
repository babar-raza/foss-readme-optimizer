"""Build a complete no-network discovery inventory for local ACT workflow proof."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from readme_agent.errors import UsageError
from readme_agent.registry import discovery
from readme_agent.registry.discovery_models import (
    DiscoveryInventoryV1,
    DiscoveryObservationV1,
    DiscoverySourceResultV1,
    DiscoverySourceV1,
)


def build_act_registry_inventory(
    products_path: Path,
    families_path: Path = discovery.FAMILIES_PATH,
) -> DiscoveryInventoryV1:
    """Mirror the admitted denominator as a complete ACT-only provider fixture."""

    if os.environ.get("ACT", "").lower() != "true":
        raise UsageError("the registry fixture is permitted only under ACT=true")
    if os.environ.get("README_AGENT_PRODUCTION_AUTH") != "act_local":
        raise UsageError("the registry fixture requires the act_local authentication provider")

    captured_at = datetime.now(UTC).isoformat()
    products = json.loads(products_path.read_text(encoding="utf-8"))
    families = discovery.load_families(families_path)
    sources = {
        str(family["github_org"]): DiscoverySourceV1.from_family(family) for family in families
    }
    counts = {owner: 0 for owner in sources}
    observations: list[DiscoveryObservationV1] = []
    for entry in products:
        owner = str(entry["repo_url"]).rstrip("/").split("/")[-2]
        source = sources.get(owner)
        if source is None:
            raise UsageError(f"registry entry {owner}/{entry['repo_name']} has no source catalog")
        identity = entry.get("provider_identity")
        if not isinstance(identity, dict):
            raise UsageError(
                f"registry entry {owner}/{entry['repo_name']} has no provider identity"
            )
        counts[owner] += 1
        observations.append(
            DiscoveryObservationV1(
                source_id=source.source_id,
                provider_repository_id=identity["repository_id"],
                provider_node_id=identity["node_id"],
                full_name=f"{owner}/{entry['repo_name']}",
                name=entry["repo_name"],
                html_url=entry["repo_url"],
                clone_url=entry["clone_url"],
                visibility="unknown",
                archived=not entry.get("active", True),
                observed_at=captured_at,
                classification="matched",
                classification_reason="ACT fixture mirrors the admitted provider identity",
                disposition="admit_candidate",
                family=entry["family"],
                platform=entry["platform"],
            )
        )
    source_results = [
        DiscoverySourceResultV1(
            source=source,
            status="complete",
            observed_at=captured_at,
            observation_count=counts[owner],
        )
        for owner, source in sorted(sources.items())
    ]
    observations.sort(key=lambda item: (item.source_id, item.full_name.casefold()))
    return DiscoveryInventoryV1(
        captured_at=captured_at,
        sources=source_results,
        observations=observations,
        complete=True,
    )
