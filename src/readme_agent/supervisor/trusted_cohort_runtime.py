"""Validate and expose one frozen trusted cohort to the reusable runtime."""

from __future__ import annotations

from pathlib import Path

from readme_agent.evidence.writer import sha256_file, verify_sha256sums
from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import trusted_reviewer_standard_hash
from readme_agent.readme.trusted_composition_candidate_validation import (
    TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
)
from readme_agent.registry.loader import PRODUCTS_PATH, require_listed
from readme_agent.state.trusted_cohort_schema import (
    QualifiedTrustedCohortMemberV1,
    QualifiedTrustedCohortV1,
)


def load_runtime_trusted_cohort(
    manifest_path: Path,
    *,
    registry_path: Path = PRODUCTS_PATH,
) -> QualifiedTrustedCohortV1:
    """Load a frozen cohort only while all candidate-affecting contracts still match."""

    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise ValueError(f"qualified cohort manifest does not exist: {manifest_path}")
    if not verify_sha256sums(manifest_path.parent):
        raise ValueError(f"qualified cohort checksum inventory is invalid: {manifest_path.parent}")

    cohort = QualifiedTrustedCohortV1.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    current_registry_hash = sha256_file(registry_path)[0]
    if cohort.registry_sha256 != current_registry_hash:
        raise ValueError("qualified cohort registry hash no longer matches data/products.json")
    if cohort.reviewer_standard_sha256 != trusted_reviewer_standard_hash():
        raise ValueError("qualified cohort reviewer standard is stale")
    if cohort.prompt_registry_sha256 != prompt_registry.content_hash():
        raise ValueError("qualified cohort prompt registry is stale")
    if cohort.candidate_normalization_version != TRUSTED_CANDIDATE_NORMALIZATION_VERSION:
        raise ValueError("qualified cohort candidate normalization contract is stale")
    for member in cohort.members:
        require_listed(member.org_repo)
    return cohort


def require_runtime_trusted_cohort_member(
    manifest_path: Path,
    org_repo: str,
) -> QualifiedTrustedCohortMemberV1:
    """Fail closed unless the requested repository is in the exact frozen cohort."""

    cohort = load_runtime_trusted_cohort(manifest_path)
    for member in cohort.members:
        if member.org_repo == org_repo:
            return member
    raise ValueError(f"{org_repo!r} is not a member of qualified cohort {cohort.cohort_id}")


def require_runtime_trusted_cohort_repair_member(
    manifest_path: Path,
    org_repo: str,
    *,
    registry_path: Path = PRODUCTS_PATH,
) -> QualifiedTrustedCohortMemberV1:
    """Select a stale-contract member only for canonical local regeneration."""

    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise ValueError(f"qualified cohort manifest does not exist: {manifest_path}")
    if not verify_sha256sums(manifest_path.parent):
        raise ValueError(f"qualified cohort checksum inventory is invalid: {manifest_path.parent}")
    cohort = QualifiedTrustedCohortV1.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if cohort.registry_sha256 != sha256_file(registry_path)[0]:
        raise ValueError("qualified cohort registry hash no longer matches data/products.json")
    for member in cohort.members:
        require_listed(member.org_repo)
        if member.org_repo == org_repo:
            return member
    raise ValueError(f"{org_repo!r} is not a member of repair cohort {cohort.cohort_id}")


def runtime_trusted_cohort_matrix(cohort: QualifiedTrustedCohortV1) -> dict[str, object]:
    """Render the deterministic Actions matrix bound to the frozen member identities."""

    return {
        "include": [
            {
                "repo": member.org_repo,
                "owner": member.org_repo.split("/", maxsplit=1)[0],
                "name": member.org_repo.split("/", maxsplit=1)[1],
                "source_revision": member.source_revision,
                "candidate_sha256": member.candidate_sha256,
                "cohort_id": cohort.cohort_id,
            }
            for member in cohort.members
        ]
    }
