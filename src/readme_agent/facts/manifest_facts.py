"""Derive visitor-facing manifest facts from the selected product root."""

import re
from pathlib import Path

from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.facts.manifest_compatibility import manifest_compatibility_rows
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.product_identity import canonical_aspose_family_name
from readme_agent.facts.root_role_schema import (
    PackageRootRoleInventoryV1,
    filesystem_repository_path,
)
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    FactVerificationState,
    descriptive_fact_id,
)
from readme_agent.profile.schema import PackageRoot, RepositoryProfile
from readme_agent.registry.models import ProductEntry

_FOSS_REPOSITORY_NAME = re.compile(r"^(.+?)-FOSS-for-.+$", flags=re.IGNORECASE)


def _registry_product_name(entry: ProductEntry) -> str | None:
    """Return the repository-bound product family display name when encoded."""

    repo_name = str(getattr(entry, "repo_name", "")).strip()
    if not repo_name:
        return None
    match = _FOSS_REPOSITORY_NAME.fullmatch(repo_name)
    if match is None:
        return None
    product_name = match.group(1).strip()
    return canonical_aspose_family_name(product_name) or product_name or None


def _fact(
    field_name: str,
    qualifier: str,
    value,
    *,
    source: FactSourceV2,
    state: FactVerificationState,
    confidence: float,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, qualifier),
        field=field_name,
        value=value,
        source=source,
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=confidence,
        affected_surfaces=SURFACE_DEPENDENCIES[field_name],
    )


def _selected_manifest_values(
    entry: ProductEntry,
    profile: RepositoryProfile,
    repository_root: Path,
    root_roles: PackageRootRoleInventoryV1,
) -> tuple[
    list[str],
    list[dict],
    list[dict],
    list[str],
    list[str],
    list[dict],
    list[PackageRoot],
]:
    selected_root = root_roles.selected_package_root(profile)
    package_roots = [selected_root] if selected_root is not None else []
    selected_role = next(
        (
            record
            for record in root_roles.roots
            if record.manifest_path == root_roles.selected_product_manifest_path
        ),
        None,
    )
    names: list[str] = []
    coordinates: list[dict] = []
    compatibility: list[dict] = []
    licenses: list[str] = []
    distribution_license_expressions: list[str] = []
    release_state: list[dict] = []
    for package_root in package_roots:
        package_dir = (
            repository_root
            if package_root.path == "."
            else repository_root / filesystem_repository_path(package_root.path)
        )
        parsed = parse_manifest(package_root.ecosystem, package_dir)
        manifest_path = (
            selected_role.manifest_path
            if selected_role is not None
            else package_root.manifest_path.replace("\\", "/")
        )
        package_path = selected_role.path if selected_role is not None else package_root.path
        if parsed.get("name"):
            names.append(parsed["name"])
        coordinates.append(
            {
                key: value
                for key, value in {
                    "path": package_path,
                    "ecosystem": package_root.ecosystem,
                    "manifest_path": manifest_path,
                    "group_id": parsed.get("group_id"),
                    "artifact_id": parsed.get("artifact_id"),
                    "name": parsed.get("name"),
                    "version": parsed.get("version"),
                    "root_role": "product",
                }.items()
                if value is not None
            }
        )
        compatibility.extend(
            manifest_compatibility_rows(package_root.ecosystem, parsed, manifest_path)
        )
        license_expression = parsed.get("license")
        if license_expression:
            if license_expression.startswith("LicenseRef-"):
                distribution_license_expressions.append(license_expression)
            else:
                licenses.append(license_expression)
        release_state.append(
            {
                "path": package_path,
                "manifest_path": manifest_path,
                "version": parsed.get("version", "unknown"),
                "active": getattr(entry, "active", True),
                "root_role": "product",
            }
        )
    return (
        names,
        coordinates,
        compatibility,
        licenses,
        distribution_license_expressions,
        release_state,
        package_roots,
    )


def manifest_fact_candidates(
    entry: ProductEntry,
    profile: RepositoryProfile,
    repository_root: Path,
    source_revision: str | None,
    observed_at: str | None,
    root_roles: PackageRootRoleInventoryV1,
) -> list[FactRecordV2]:
    """Bind identity/acquisition/compatibility/release facts to one product root."""

    (
        names,
        coordinates,
        compatibility,
        licenses,
        distribution_license_expressions,
        releases,
        package_roots,
    ) = _selected_manifest_values(
        entry,
        profile,
        repository_root,
        root_roles,
    )
    selected_paths = [
        record.manifest_path for record in root_roles.roots if record.role == "product"
    ]
    inventory_paths = [record.manifest_path for record in root_roles.roots]
    manifest_source = FactSourceV2(
        source_type="mechanical_manifest",
        location="repository://" + ",".join(sorted(set(selected_paths or inventory_paths))),
        source_revision=source_revision,
        retrieved_at=observed_at,
    )
    candidates = [
        _fact(
            "product.identity",
            "manifest-and-registry",
            {
                "family": entry.family,
                "platform": entry.platform,
                "ecosystem": entry.ecosystem,
                "repository": profile.org_repo,
                "manifest_names": names,
                "product_name": _registry_product_name(entry),
            },
            source=manifest_source,
            state="verified",
            confidence=1.0,
        ),
        _fact(
            "product.platforms",
            "manifest",
            sorted(
                {
                    value
                    for value in [
                        entry.platform,
                        *(root.ecosystem for root in package_roots),
                    ]
                    if value
                }
            ),
            source=manifest_source,
            state="verified",
            confidence=1.0,
        ),
    ]
    for field_name, qualifier, value in (
        ("installation.coordinates", "manifest", coordinates),
        ("product.compatibility", "manifest", compatibility),
        (
            "product.license",
            "manifest",
            licenses[0] if len(set(licenses)) == 1 else sorted(set(licenses)),
        ),
        ("release.state", "manifest-and-registry", releases),
        (
            "distribution.license_expression",
            "manifest",
            (
                distribution_license_expressions[0]
                if len(set(distribution_license_expressions)) == 1
                else sorted(set(distribution_license_expressions))
            ),
        ),
    ):
        if value:
            candidates.append(
                _fact(
                    field_name,
                    qualifier,
                    value,
                    source=manifest_source,
                    state="verified",
                    confidence=1.0,
                )
            )
    if root_roles.selected_product_manifest_path is None:
        blocked_value = {
            "selection_state": root_roles.selection_state,
            "selection_rationale": root_roles.selection_rationale,
            "root_inventory_hash": root_roles.canonical_hash(),
        }
        for field_name in (
            "installation.coordinates",
            "product.compatibility",
            "product.license",
            "release.state",
        ):
            candidates.append(
                _fact(
                    field_name,
                    "blocked-root-selection",
                    blocked_value,
                    source=manifest_source,
                    state="blocked",
                    confidence=0.0,
                )
            )
    return candidates
