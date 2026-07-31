"""Independently recheck package acquisition against an authoritative registry."""

from __future__ import annotations

from typing import Any

from readme_agent.ecosystems.foss_coordinate import canonical_foss_coordinate
from readme_agent.ecosystems.resolver import resolve
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.registry.loader import require_listed


def _project_manifest_coordinate(
    facts: ProductFactsV2,
    ecosystem: str,
) -> dict[str, str] | None:
    coordinate_fact = facts.selected_fact("installation.coordinates")
    if coordinate_fact.verification_state != "verified" or not isinstance(
        coordinate_fact.value, list
    ):
        return None
    selected = next(
        (
            coordinate
            for coordinate in coordinate_fact.value
            if isinstance(coordinate, dict) and coordinate.get("ecosystem") == ecosystem
        ),
        None,
    )
    if selected is None:
        return None
    keys = ("group_id", "artifact_id") if ecosystem == "java" else ("name",)
    projected = {key: str(selected[key]) for key in keys if selected.get(key) is not None}
    return projected if len(projected) == len(keys) else None


def _recorded_coordinate(acquisition_value: Any) -> dict[str, str] | None:
    if not isinstance(acquisition_value, dict):
        return None
    coordinate = acquisition_value.get("coordinate")
    if not isinstance(coordinate, dict) or not coordinate:
        return None
    if not all(
        isinstance(key, str) and isinstance(value, str) for key, value in coordinate.items()
    ):
        return None
    return coordinate


def verify_acquisition_ground_truth(
    org_repo: str,
    facts: ProductFactsV2,
) -> tuple[bool, str]:
    """Re-resolve the fact-bound coordinate instead of trusting stored registry claims."""

    try:
        entry = require_listed(org_repo)
    except Exception as exc:  # noqa: BLE001 -- any lookup failure is a verification failure
        return False, f"could not resolve registry entry for {org_repo}: {exc}"
    if entry.ecosystem is None:
        return True, "no ecosystem configured -- acquisition ground truth not applicable"

    resolver_ecosystem, canonical_coordinate = canonical_foss_coordinate(
        entry.family,
        entry.ecosystem,
        entry.org,
        entry.repo_name,
    )
    if resolver_ecosystem is None:
        return True, f"no canonical FOSS coordinate for ecosystem {entry.ecosystem!r}"

    acquisition = facts.selected_fact("installation.verified_acquisition")
    recorded_coordinate = _recorded_coordinate(acquisition.value)
    if recorded_coordinate is None:
        return False, "verified acquisition fact has no complete recorded coordinate"

    allowed_coordinates = [canonical_coordinate]
    manifest_coordinate = _project_manifest_coordinate(facts, entry.ecosystem)
    if manifest_coordinate is not None:
        allowed_coordinates.append(manifest_coordinate)
    if recorded_coordinate not in allowed_coordinates:
        return False, (
            f"recorded acquisition coordinate {recorded_coordinate} is not bound to a verified "
            "manifest coordinate or the governed portfolio fallback"
        )

    result = resolve(resolver_ecosystem, recorded_coordinate)
    if result.blocked:
        return True, f"acquisition ground-truth check network-blocked: {result.detail}"

    recorded_method = (
        acquisition.value.get("method") if isinstance(acquisition.value, dict) else None
    )
    if result.found and recorded_method == "source_build":
        return False, (
            f"{recorded_coordinate} IS published ({result.detail}) but the bundle's facts record "
            "method=source_build -- a published install was wrongly stripped"
        )
    if not result.found and recorded_method != "source_build":
        return False, (
            f"{recorded_coordinate} is NOT published ({result.detail}) but the bundle's facts "
            f"record method={recorded_method!r} -- an unpublished package cannot be verified"
        )
    return True, ""
