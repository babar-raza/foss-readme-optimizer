"""Ingest policy-selected assertions only after repository evidence proves them."""

from __future__ import annotations

from pathlib import Path

from readme_agent.ecosystems.registry import parse_manifest
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.policy_evidence import evidence_fact_candidate
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.inspection.file_inventory import scan
from readme_agent.license.auditor import detect_license
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.registry.models import PolicyProfile, ProductEntry

_RUNTIME_REQUIREMENT_FIELDS: dict[str, tuple[str, str]] = {
    "cpp": ("cmake_min_version", "CMake"),
    "go": ("runtime_min_version", "Go"),
    "java": ("runtime_min_version", "Java"),
    "net": ("min_framework", ".NET"),
    "python": ("requires_python", "Python"),
    "rust": ("rust_version", "Rust"),
    "typescript": ("engines_node", "Node.js"),
}


def _source(
    source_type: str,
    location: str,
    source_revision: str | None,
    observed_at: str | None,
) -> FactSourceV2:
    return FactSourceV2(
        source_type=source_type,  # type: ignore[arg-type]
        location=location,
        source_revision=source_revision,
        retrieved_at=observed_at,
    )


def _fact(
    field_name: str,
    qualifier: str,
    value,
    *,
    source: FactSourceV2,
    state: str,
    owner: str,
    confidence: float,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, qualifier),
        field=field_name,
        value=value,
        source=source,
        verification_state=state,  # type: ignore[arg-type]
        authoritative_owner=owner,
        confidence=confidence,
        affected_surfaces=SURFACE_DEPENDENCIES[field_name],
    )


def _manifest_candidates(
    entry: ProductEntry,
    profile: RepositoryProfile,
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
) -> list[FactRecordV2]:
    coordinates: list[dict[str, str]] = []
    compatibility: list[dict[str, str]] = []
    release_state: list[dict[str, str | bool]] = []
    names: list[str] = []
    manifest_locations: list[str] = []
    for package_root in profile.package_roots:
        package_dir = root if package_root.path == "." else root / package_root.path
        parsed = parse_manifest(package_root.ecosystem, package_dir)
        manifest_locations.append(package_root.manifest_path)
        name = parsed.get("name")
        if name:
            names.append(name)
        coordinate = {
            key: value
            for key, value in {
                "path": package_root.path,
                "ecosystem": package_root.ecosystem,
                "manifest_path": package_root.manifest_path,
                "group_id": parsed.get("group_id"),
                "artifact_id": parsed.get("artifact_id"),
                "name": parsed.get("name"),
                "version": parsed.get("version"),
            }.items()
            if value is not None
        }
        coordinates.append(coordinate)
        requirement_key, runtime_label = _RUNTIME_REQUIREMENT_FIELDS.get(
            package_root.ecosystem,
            ("runtime_min_version", package_root.ecosystem),
        )
        runtime = parsed.get(requirement_key)
        if runtime:
            compatibility.append(
                {
                    "ecosystem": package_root.ecosystem,
                    "runtime_label": runtime_label,
                    "minimum_runtime": runtime,
                    "manifest_path": package_root.manifest_path,
                }
            )
        release_state.append(
            {
                "path": package_root.path,
                "version": parsed.get("version", "unknown"),
                "active": getattr(entry, "active", True),
            }
        )
    location = "repository://" + ",".join(sorted(set(manifest_locations)))
    manifest_source = _source(
        "mechanical_manifest",
        location,
        source_revision,
        observed_at,
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
            },
            source=manifest_source,
            state="verified",
            owner="repository-owner",
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
                        *(root.ecosystem for root in profile.package_roots),
                    ]
                    if value
                }
            ),
            source=manifest_source,
            state="verified",
            owner="repository-owner",
            confidence=1.0,
        ),
    ]
    if coordinates:
        candidates.append(
            _fact(
                "installation.coordinates",
                "manifest",
                coordinates,
                source=manifest_source,
                state="verified",
                owner="repository-owner",
                confidence=1.0,
            )
        )
    if compatibility:
        candidates.append(
            _fact(
                "product.compatibility",
                "manifest",
                compatibility,
                source=manifest_source,
                state="verified",
                owner="repository-owner",
                confidence=1.0,
            )
        )
    if release_state:
        candidates.append(
            _fact(
                "release.state",
                "manifest-and-registry",
                release_state,
                source=manifest_source,
                state="verified",
                owner="repository-owner",
                confidence=1.0,
            )
        )
    return candidates


def ingest_repository_product_facts(
    entry: ProductEntry,
    policy: PolicyProfile,
    profile: RepositoryProfile,
    root: Path,
    source_revision: str | None,
    observed_at: str | None = None,
) -> list[FactRecordV2]:
    """Return mechanically or policy verified candidates from one snapshot."""

    candidates = _manifest_candidates(entry, profile, root, source_revision, observed_at)
    truth = policy.product_truth
    if truth is not None:
        policy_source = _source(
            "approved_policy",
            f"config/policies/{policy.policy_profile}.yml",
            source_revision,
            observed_at,
        )
        candidates.extend(
            [
                _fact(
                    "product.audience",
                    "approved-policy",
                    truth.audience,
                    source=policy_source,
                    state="policy_approved",
                    owner="product-policy-owner",
                    confidence=1.0,
                ),
                _fact(
                    "product.problems_solved",
                    "approved-policy",
                    truth.problems_solved,
                    source=policy_source,
                    state="policy_approved",
                    owner="product-policy-owner",
                    confidence=1.0,
                ),
                evidence_fact_candidate(
                    root,
                    source_revision,
                    observed_at,
                    "product.capabilities",
                    truth.capabilities,
                ),
                evidence_fact_candidate(
                    root,
                    source_revision,
                    observed_at,
                    "product.formats",
                    truth.formats,
                ),
                evidence_fact_candidate(
                    root,
                    source_revision,
                    observed_at,
                    "product.limitations",
                    truth.limitations,
                ),
            ]
        )

    inventory = scan(root)
    license_state = detect_license(None, inventory.license_path)
    if license_state.detected and inventory.license_path is not None:
        candidates.append(
            _fact(
                "product.license",
                "license-file",
                license_state.detected,
                source=_source(
                    "mechanical_repository",
                    f"repository://{inventory.license_path.relative_to(root).as_posix()}",
                    source_revision,
                    observed_at,
                ),
                state="verified",
                owner="repository-owner",
                confidence=1.0,
            )
        )
    return candidates
