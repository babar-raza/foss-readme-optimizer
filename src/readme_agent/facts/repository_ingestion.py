"""Ingest policy-selected assertions only after repository evidence proves them."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.manifest_facts import manifest_fact_candidates
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.policy_evidence import evidence_fact_candidate
from readme_agent.facts.root_role_schema import PackageRootRoleInventoryV1
from readme_agent.facts.root_roles import classify_package_root_roles
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.inspection.file_inventory import scan
from readme_agent.license.auditor import detect_license
from readme_agent.profile.schema import RepositoryProfile
from readme_agent.registry.models import PolicyProfile, ProductEntry


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


def ingest_repository_product_facts(
    entry: ProductEntry,
    policy: PolicyProfile,
    profile: RepositoryProfile,
    root: Path,
    source_revision: str | None,
    observed_at: str | None = None,
    *,
    root_roles: PackageRootRoleInventoryV1 | None = None,
) -> list[FactRecordV2]:
    """Return mechanically or policy verified candidates from one snapshot."""

    root_role_inventory = root_roles or classify_package_root_roles(
        entry,
        profile,
        root,
        source_revision,
    )
    candidates = manifest_fact_candidates(
        entry,
        profile,
        root,
        source_revision,
        observed_at,
        root_role_inventory,
    )
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
