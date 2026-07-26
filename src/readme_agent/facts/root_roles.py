"""Select one distributed product root from deterministic role evidence."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.root_role_evidence import (
    PRODUCT_PATH_TOKENS,
    PackageRootEvidence,
    evidence_tokens,
    identity_score,
    inspect_package_root,
)
from readme_agent.facts.root_role_schema import (
    PackageRootRoleInventoryV1,
    PackageRootRoleV1,
    RootSelectionState,
    portable_repository_path,
)
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.registry.models import ProductEntry


def _score_candidates(
    entry: ProductEntry,
    observations: list[PackageRootEvidence],
    referenced_by: dict[str, list[str]],
) -> list[tuple[int, str, list[str], PackageRootEvidence]]:
    scored: list[tuple[int, str, list[str], PackageRootEvidence]] = []
    for observation in observations:
        package_root = observation.package_root
        if observation.secondary_role is not None:
            continue
        if entry.ecosystem is not None and package_root.ecosystem != entry.ecosystem:
            continue
        score, reasons = identity_score(entry, observation.parsed)
        manifest_path = portable_repository_path(package_root.manifest_path)
        inbound = sorted(referenced_by.get(manifest_path, []))
        if inbound:
            score += 50 + min(25, 5 * len(inbound))
            reasons.append("referenced by another repository root: " + ", ".join(inbound))
        if evidence_tokens(package_root.path) & PRODUCT_PATH_TOKENS:
            score += 15
            reasons.append("path identifies a product/library root")
        if package_root.path == ".":
            score += 10
            reasons.append("repository-root manifest")
        scored.append((score, manifest_path, reasons, observation))
    return scored


def _select_product_root(
    root_count: int,
    scored: list[tuple[int, str, list[str], PackageRootEvidence]],
) -> tuple[str | None, RootSelectionState, list[str]]:
    if root_count == 0:
        return None, "missing", ["repository profile contains no package roots"]
    if not scored:
        return (
            None,
            "ambiguous",
            ["no unambiguously product-shaped root matches the registry ecosystem"],
        )
    if len(scored) == 1:
        return (
            scored[0][1],
            "selected",
            [
                "the sole non-secondary root matching the registry ecosystem was selected",
                *scored[0][2],
            ],
        )
    ranked = sorted(scored, key=lambda item: (-item[0], item[1].casefold()))
    if ranked[0][0] <= 0 or ranked[0][0] == ranked[1][0]:
        return (
            None,
            "ambiguous",
            ["multiple roots have equal or insufficient product evidence; selection is blocked"],
        )
    return (
        ranked[0][1],
        "selected",
        [
            f"highest deterministic product-root score selected ({ranked[0][0]})",
            *ranked[0][2],
        ],
    )


def _role_records(
    entry: ProductEntry,
    observations: list[PackageRootEvidence],
    selected_manifest: str | None,
    selection_rationale: list[str],
) -> list[PackageRootRoleV1]:
    records: list[PackageRootRoleV1] = []
    for observation in observations:
        package_root = observation.package_root
        manifest_path = portable_repository_path(package_root.manifest_path)
        if observation.secondary_role is not None:
            role = observation.secondary_role
            confidence = 1.0
            rationale = list(observation.rationale)
        elif manifest_path == selected_manifest:
            role = "product"
            confidence = 1.0
            rationale = ["selected as the distributed product root", *selection_rationale]
        else:
            role = "unknown"
            confidence = 0.0
            rationale = [
                "root is preserved as evidence but is not selected for visitor-facing facts"
            ]
            if entry.ecosystem is not None and package_root.ecosystem != entry.ecosystem:
                rationale.append(
                    f"root ecosystem {package_root.ecosystem!r} differs from registry "
                    f"ecosystem {entry.ecosystem!r}"
                )
        records.append(
            PackageRootRoleV1(
                path=portable_repository_path(package_root.path) or ".",
                ecosystem=package_root.ecosystem,
                manifest_path=manifest_path,
                role=role,
                confidence=confidence,
                parsed_identity={
                    key: value
                    for key, value in sorted(observation.parsed.items())
                    if key in {"artifact_id", "group_id", "name", "version"}
                },
                referenced_manifest_paths=[
                    portable_repository_path(path) for path in observation.references
                ],
                rationale=list(dict.fromkeys(rationale)),
            )
        )
    return records


def classify_package_root_roles(
    entry: ProductEntry,
    profile: RepositoryProfile,
    repository_root: Path,
    source_revision: str | None,
) -> PackageRootRoleInventoryV1:
    """Classify every root without guessing between equally supported products."""

    ordered_roots = sorted(
        profile.package_roots,
        key=lambda package_root: portable_repository_path(package_root.manifest_path).casefold(),
    )
    observations = [
        inspect_package_root(repository_root, package_root) for package_root in ordered_roots
    ]
    referenced_by: dict[str, list[str]] = {}
    for observation in observations:
        source = portable_repository_path(observation.package_root.manifest_path)
        for referenced in observation.references:
            referenced_by.setdefault(portable_repository_path(referenced), []).append(source)

    scored = _score_candidates(entry, observations, referenced_by)
    selected, selection_state, rationale = _select_product_root(len(ordered_roots), scored)
    return PackageRootRoleInventoryV1(
        org_repo=profile.org_repo,
        source_revision=source_revision,
        selection_state=selection_state,
        selected_product_manifest_path=selected,
        selection_rationale=list(dict.fromkeys(rationale)),
        roots=_role_records(entry, observations, selected, rationale),
    )
