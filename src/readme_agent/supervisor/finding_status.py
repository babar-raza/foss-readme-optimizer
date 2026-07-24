"""Classify specialist outputs as unresolved findings or completed proposals."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from readme_agent.state.schema import DomainStateV1


@dataclass(frozen=True)
class SpecialistFindingStatus:
    unresolved: tuple[str, ...]
    proposals: tuple[str, ...]


def _items(details: Mapping[str, Any], key: str) -> list[Any]:
    value = details.get(key)
    return value if isinstance(value, list) else []


def classify_specialist_findings(
    specialist_results: Mapping[str, DomainStateV1] | None,
) -> SpecialistFindingStatus:
    """Return deterministic terminal signals from the typed specialist tier.

    `accepted_status=FIRST_OBSERVATION` means only that a domain snapshot was
    persisted; it does not mean the observed presentation is acceptable.
    Domain-specific detail fields are therefore the authoritative terminal
    signals until every specialist exposes one common finding schema.
    """
    unresolved: list[str] = []
    proposals: list[str] = []
    results = specialist_results or {}

    readme = results.get("readme_presentation")
    if readme is not None:
        render_status = readme.details.get("render_status")
        if render_status in {"STALE_NONCOMPLIANT", "BLOCKED_VALIDATION_FAILED"}:
            unresolved.append(f"readme_presentation:{render_status}")
        elif render_status == "GENERATED" and not (
            readme.details.get("written") or readme.details.get("committed")
        ):
            proposals.append("readme_presentation:candidate_ready")

    metadata = results.get("metadata_presentation")
    if metadata is not None:
        blocked = _items(metadata.details, "blocked_findings")
        if blocked:
            unresolved.append(f"metadata_presentation:{len(blocked)}_blocked")
        if metadata.details.get("has_proposal"):
            proposals.append("metadata_presentation:proposal_ready")

    community = results.get("community_files_presentation")
    if community is not None and _items(community.details, "prepared_candidates"):
        proposals.append("community_files_presentation:candidates_ready")

    package_release = results.get("package_release_audit")
    if package_release is not None and _items(package_release.details, "handoff_findings"):
        proposals.append("package_release_audit:handoff_ready")

    cross_surface = results.get("cross_surface_validation")
    if cross_surface is not None:
        inconsistencies = _items(cross_surface.details, "inconsistencies")
        if inconsistencies:
            unresolved.append(f"cross_surface_validation:{len(inconsistencies)}_inconsistent")

    benchmarking = results.get("presentation_benchmarking")
    if benchmarking is not None:
        failed_dimensions = [
            str(item.get("dimension", "unknown"))
            for item in _items(benchmarking.details, "criteria_results")
            if isinstance(item, dict) and item.get("satisfied") is False
        ]
        if failed_dimensions:
            unresolved.append("presentation_benchmarking:" + ",".join(sorted(failed_dimensions)))

    verifier = results.get("independent_verification")
    if verifier is not None:
        adversarial = _items(verifier.details, "adversarial_findings")
        escalations = verifier.details.get("failure_escalations")
        if adversarial:
            unresolved.append(f"independent_verification:{len(adversarial)}_adversarial")
        if isinstance(escalations, dict) and escalations:
            unresolved.append(f"independent_verification:{len(escalations)}_failure_escalations")

    visual = results.get("visual_preparation")
    if visual is not None and visual.details.get("prepared_candidate"):
        proposals.append("visual_preparation:candidate_ready")

    return SpecialistFindingStatus(
        unresolved=tuple(sorted(set(unresolved))),
        proposals=tuple(sorted(set(proposals))),
    )
