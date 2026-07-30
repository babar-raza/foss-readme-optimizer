"""Independently reconstruct and verify a frozen trusted cohort."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from readme_agent.evidence.writer import sha256_file, verify_sha256sums
from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import trusted_reviewer_standard_hash
from readme_agent.readme.trusted_composition_candidate_validation import (
    TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
)
from readme_agent.registry.models import ProductEntry
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.state.trusted_cohort_schema import (
    QualifiedTrustedCohortIdentityV1,
    QualifiedTrustedCohortMemberV1,
    QualifiedTrustedCohortV1,
    TrustedCohortReconstructionV1,
)
from readme_agent.supervisor.trusted_cohort_qualification import (
    trusted_bundle_dir,
    validate_trusted_cohort_member,
)

HeadObserver = Callable[[str], str | None]


def reconstruct_qualified_trusted_cohort(
    frozen: QualifiedTrustedCohortV1,
    entries: Sequence[ProductEntry],
    states: Mapping[str, RunStateV2 | None],
    *,
    registry_path: Path,
    control_revision: str,
    observe_head: HeadObserver,
    cohort_dir: Path,
) -> TrustedCohortReconstructionV1:
    """Recompute membership without trusting the frozen exclusions or reducer."""

    reasons: list[str] = []
    expected_members = _independently_qualify_members(entries, states, observe_head)
    identity = QualifiedTrustedCohortIdentityV1(
        control_revision=control_revision,
        registry_sha256=sha256_file(registry_path)[0],
        reviewer_standard_sha256=trusted_reviewer_standard_hash(),
        prompt_registry_sha256=prompt_registry.content_hash(),
        candidate_normalization_version=TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
        member_bindings=tuple(_member_identity(member) for member in expected_members),
    )
    reconstructed_id = identity.canonical_hash()
    frozen_order = tuple(member.org_repo for member in frozen.members)
    reconstructed_order = tuple(member.org_repo for member in expected_members)
    if reconstructed_id != frozen.cohort_id:
        reasons.append("cohort_identity_mismatch")
    if reconstructed_order != frozen_order:
        reasons.append("cohort_order_mismatch")
    if frozen.registry_denominator != len(entries):
        reasons.append("registry_denominator_mismatch")
    if not verify_sha256sums(cohort_dir):
        reasons.append("cohort_checksum_inventory_invalid")
    manifest_path = cohort_dir / "manifest.json"
    return TrustedCohortReconstructionV1(
        cohort_id=frozen.cohort_id,
        reconstructed_cohort_id=reconstructed_id,
        ordered_members=frozen_order,
        reconstructed_ordered_members=reconstructed_order,
        manifest_sha256=sha256_file(manifest_path)[0],
        passed=not reasons,
        reasons=tuple(reasons or ["cohort identity, order, and inventory reproduced"]),
    )


def _independently_qualify_members(
    entries: Sequence[ProductEntry],
    states: Mapping[str, RunStateV2 | None],
    observe_head: HeadObserver,
) -> list[QualifiedTrustedCohortMemberV1]:
    reviewer_standard = trusted_reviewer_standard_hash()
    prompt_content = prompt_registry.content_hash()
    prompt_dependencies = prompt_registry.dependency_hashes()
    prompt_hashes = prompt_registry.prompt_hashes()
    members: list[QualifiedTrustedCohortMemberV1] = []
    for entry in sorted(entries, key=lambda item: item.org_repo):
        state = states.get(entry.org_repo)
        lifecycle = state.readme_poc_lifecycle if state is not None else None
        if (
            state is None
            or not isinstance(lifecycle, ReadmePocLifecycleStateV2)
            or lifecycle.content_assurance != "trusted_inherited"
            or lifecycle.status != "TRUSTED_NO_OP_PROVEN"
            or lifecycle.source_revision is None
            or entry.provider_identity is None
        ):
            continue
        member, validation_reasons = validate_trusted_cohort_member(
            entry,
            state,
            trusted_bundle_dir(entry.org_repo, lifecycle.source_revision),
            reviewer_standard=reviewer_standard,
            prompt_content=prompt_content,
            prompt_dependencies=prompt_dependencies,
            prompt_hashes=prompt_hashes,
        )
        if member is None or validation_reasons:
            continue
        observed_head = observe_head(entry.clone_url)
        if observed_head != lifecycle.source_revision:
            continue
        members.append(member.model_copy(update={"observed_target_head": observed_head}))
    return members


def _member_identity(member: QualifiedTrustedCohortMemberV1) -> dict[str, str | int]:
    return {
        "org_repo": member.org_repo,
        "repository_id": member.provider_identity.repository_id,
        "source_revision": member.source_revision,
        "candidate_sha256": member.candidate_sha256,
        "bundle_manifest_sha256": member.bundle_manifest_sha256,
        "bundle_inventory_sha256": member.bundle_inventory_sha256,
        "state_version": member.state_version,
    }
