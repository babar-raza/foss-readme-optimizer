"""Derive and persist the qualified trusted cohort from live authoritative state."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    sha256_file,
    verify_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
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
    TrustedCohortExclusionV1,
    TrustedCohortReconstructionV1,
)
from readme_agent.supervisor.trusted_cohort_qualification import (
    display_path as _display_path,
)
from readme_agent.supervisor.trusted_cohort_qualification import (
    trusted_bundle_dir as _bundle_dir,
)
from readme_agent.supervisor.trusted_cohort_qualification import (
    validate_trusted_cohort_member as _validate_member_bundle,
)

HeadObserver = Callable[[str], str | None]


def build_qualified_trusted_cohort(
    entries: Sequence[ProductEntry],
    states: Mapping[str, RunStateV2 | None],
    *,
    registry_path: Path,
    control_revision: str,
    observe_head: HeadObserver,
) -> QualifiedTrustedCohortV1:
    """Build a fail-closed cohort view; every registry entry is accounted for."""

    registry_sha256 = sha256_file(registry_path)[0]
    reviewer_standard = trusted_reviewer_standard_hash()
    prompt_content = prompt_registry.content_hash()
    prompt_dependencies = prompt_registry.dependency_hashes()
    prompt_hashes = prompt_registry.prompt_hashes()
    members: list[QualifiedTrustedCohortMemberV1] = []
    exclusions: list[TrustedCohortExclusionV1] = []

    for entry in sorted(entries, key=lambda item: item.org_repo):
        state = states.get(entry.org_repo)
        lifecycle = state.readme_poc_lifecycle if state is not None else None
        lifecycle_status = str(lifecycle.status) if lifecycle is not None else None
        content_assurance = (
            str(lifecycle.content_assurance)
            if isinstance(lifecycle, ReadmePocLifecycleStateV2)
            else None
        )
        source_revision = (
            lifecycle.source_revision if isinstance(lifecycle, ReadmePocLifecycleStateV2) else None
        )
        reasons: list[str] = []
        if state is None:
            reasons.append("durable_state_missing")
        if lifecycle is None:
            reasons.append("lifecycle_missing")
        elif not isinstance(lifecycle, ReadmePocLifecycleStateV2):
            reasons.append("lifecycle_schema_not_v2")
        elif lifecycle.content_assurance != "trusted_inherited":
            reasons.append("wrong_content_assurance")
        elif lifecycle.status != "TRUSTED_NO_OP_PROVEN":
            reasons.append("lifecycle_not_trusted_no_op_proven")
        if entry.provider_identity is None:
            reasons.append("stable_provider_identity_missing")
        if reasons:
            exclusions.append(
                TrustedCohortExclusionV1(
                    org_repo=entry.org_repo,
                    lifecycle_status=lifecycle_status,
                    content_assurance=content_assurance,
                    source_revision=source_revision,
                    reasons=tuple(reasons),
                )
            )
            continue

        assert state is not None
        assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
        assert lifecycle.source_revision is not None
        bundle_dir = _bundle_dir(entry.org_repo, lifecycle.source_revision)
        member, validation_reasons = _validate_member_bundle(
            entry,
            state,
            bundle_dir,
            reviewer_standard=reviewer_standard,
            prompt_content=prompt_content,
            prompt_dependencies=prompt_dependencies,
            prompt_hashes=prompt_hashes,
        )
        if validation_reasons:
            exclusions.append(
                TrustedCohortExclusionV1(
                    org_repo=entry.org_repo,
                    lifecycle_status=lifecycle_status,
                    content_assurance=content_assurance,
                    source_revision=source_revision,
                    reasons=tuple(sorted(set(validation_reasons))),
                    bundle_path=_display_path(bundle_dir),
                )
            )
            continue

        observed_head = observe_head(entry.clone_url)
        if observed_head is None:
            exclusions.append(
                TrustedCohortExclusionV1(
                    org_repo=entry.org_repo,
                    lifecycle_status=lifecycle_status,
                    content_assurance=content_assurance,
                    source_revision=source_revision,
                    reasons=("target_head_unavailable",),
                    bundle_path=_display_path(bundle_dir),
                )
            )
            continue
        if observed_head != lifecycle.source_revision:
            exclusions.append(
                TrustedCohortExclusionV1(
                    org_repo=entry.org_repo,
                    lifecycle_status=lifecycle_status,
                    content_assurance=content_assurance,
                    source_revision=source_revision,
                    observed_target_head=observed_head,
                    reasons=("target_head_drifted",),
                    bundle_path=_display_path(bundle_dir),
                )
            )
            continue

        assert member is not None
        members.append(member.model_copy(update={"observed_target_head": observed_head}))

    identity = QualifiedTrustedCohortIdentityV1(
        registry_sha256=registry_sha256,
        reviewer_standard_sha256=reviewer_standard,
        prompt_registry_sha256=prompt_content,
        candidate_normalization_version=TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
        member_bindings=tuple(_member_identity(member) for member in members),
    )
    return QualifiedTrustedCohortV1(
        cohort_id=identity.canonical_hash(),
        control_revision=control_revision,
        registry_path=registry_path.as_posix(),
        registry_sha256=registry_sha256,
        frozen_at=datetime.now(UTC).isoformat(),
        reviewer_standard_sha256=reviewer_standard,
        prompt_registry_sha256=prompt_content,
        candidate_normalization_version=TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
        registry_denominator=len(entries),
        qualified_count=len(members),
        members=tuple(members),
        exclusions=tuple(exclusions),
    )


def write_qualified_trusted_cohort(
    cohort: QualifiedTrustedCohortV1,
    *,
    output_root: Path | None = None,
) -> tuple[QualifiedTrustedCohortV1, Path]:
    """Write one immutable cohort directory and an idempotent current pointer."""

    root = output_root or paths.readme_poc_root() / "cohorts" / "qualified-trusted"
    cohort_dir = root / cohort.cohort_id
    manifest_path = cohort_dir / "manifest.json"
    if manifest_path.is_file():
        existing = QualifiedTrustedCohortV1.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        if existing.cohort_id != cohort.cohort_id or not verify_sha256sums(cohort_dir):
            raise ValueError("existing qualified cohort directory is corrupt or mismatched")
        frozen = existing
    else:
        frozen = cohort
        write_redacted_json(manifest_path, frozen)
        write_redacted_json(
            cohort_dir / "source-head-receipts.json",
            [
                {
                    "org_repo": member.org_repo,
                    "source_revision": member.source_revision,
                    "observed_target_head": member.observed_target_head,
                    "fresh": True,
                }
                for member in frozen.members
            ],
        )
        write_redacted_json(cohort_dir / "exclusions.json", list(frozen.exclusions))
        write_redacted_text(
            cohort_dir / "REPRODUCE.txt",
            (".venv/Scripts/python -m readme_agent.supervisor.trusted_cohort_command\n"),
        )
        refresh_sha256sums(cohort_dir)

    write_redacted_json(
        root / "current.json",
        {
            "schema_version": 1,
            "cohort_id": frozen.cohort_id,
            "manifest_path": _display_path(cohort_dir / "manifest.json"),
            "qualified_count": frozen.qualified_count,
        },
    )
    return frozen, cohort_dir


def verify_qualified_trusted_cohort(
    frozen: QualifiedTrustedCohortV1,
    entries: Sequence[ProductEntry],
    states: Mapping[str, RunStateV2 | None],
    *,
    registry_path: Path,
    control_revision: str,
    observe_head: HeadObserver,
    cohort_dir: Path,
) -> TrustedCohortReconstructionV1:
    """Independently rederive cohort identity and ordering from current inputs."""

    reconstructed = build_qualified_trusted_cohort(
        entries,
        states,
        registry_path=registry_path,
        control_revision=control_revision,
        observe_head=observe_head,
    )
    manifest_path = cohort_dir / "manifest.json"
    reasons: list[str] = []
    if not verify_sha256sums(cohort_dir):
        reasons.append("cohort_checksum_inventory_invalid")
    if reconstructed.cohort_id != frozen.cohort_id:
        reasons.append("cohort_identity_mismatch")
    frozen_order = tuple(member.org_repo for member in frozen.members)
    reconstructed_order = tuple(member.org_repo for member in reconstructed.members)
    if reconstructed_order != frozen_order:
        reasons.append("cohort_order_mismatch")
    return TrustedCohortReconstructionV1(
        cohort_id=frozen.cohort_id,
        reconstructed_cohort_id=reconstructed.cohort_id,
        ordered_members=frozen_order,
        reconstructed_ordered_members=reconstructed_order,
        manifest_sha256=sha256_file(manifest_path)[0],
        passed=not reasons,
        reasons=tuple(reasons or ["cohort identity, order, and inventory reproduced"]),
    )


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
