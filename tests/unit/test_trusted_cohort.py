"""Prove qualified trusted-cohort derivation, exclusion, and reconstruction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from readme_agent.registry.models import ProductEntry, ProviderRepositoryIdentityV1
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.state.trusted_cohort_schema import QualifiedTrustedCohortMemberV1
from readme_agent.supervisor import trusted_cohort
from readme_agent.supervisor.trusted_cohort_qualification import (
    validate_trusted_cohort_member,
)

SHA = "a" * 40
DIGEST = "b" * 64


def _entry(name: str, repository_id: int) -> ProductEntry:
    return ProductEntry(
        registry_schema_version=2,
        provider_identity=ProviderRepositoryIdentityV1(
            repository_id=repository_id,
            node_id=f"R_{repository_id}",
        ),
        family="Example",
        platform="Python",
        repo_name=name,
        repo_url=f"https://github.com/example/{name}",
        clone_url=f"https://github.com/example/{name}.git",
        active=True,
        discovered_via="test",
        mode="disabled",
        ecosystem="python",
        policy_profile="aspose-foss",
    )


def _state(
    org_repo: str,
    *,
    status: str = "TRUSTED_NO_OP_PROVEN",
    assurance: str = "trusted_inherited",
    version: int = 4,
) -> RunStateV2:
    lifecycle = ReadmePocLifecycleStateV2(
        status=status,
        content_assurance=assurance,
        source_revision=SHA,
        facts_hash=DIGEST,
        candidate_hash=DIGEST,
        prompt_hash=DIGEST,
    )
    return RunStateV2(
        org_repo=org_repo,
        state_version=version,
        readme_poc_lifecycle=lifecycle,
    )


def _member(entry: ProductEntry, state: RunStateV2) -> QualifiedTrustedCohortMemberV1:
    return QualifiedTrustedCohortMemberV1(
        org_repo=entry.org_repo,
        provider_identity=entry.provider_identity,
        source_revision=SHA,
        observed_target_head=SHA,
        state_version=state.state_version,
        readme_sha256=DIGEST,
        facts_sha256=DIGEST,
        plan_sha256=DIGEST,
        candidate_sha256=DIGEST,
        deterministic_validation_sha256=DIGEST,
        independent_review_sha256=DIGEST,
        no_op_proof_sha256=DIGEST,
        review_cache_identity_sha256=DIGEST,
        reviewer_standard_sha256=trusted_cohort.trusted_reviewer_standard_hash(),
        prompt_registry_sha256=trusted_cohort.prompt_registry.content_hash(),
        prompt_dependency_hashes=trusted_cohort.prompt_registry.dependency_hashes(),
        candidate_normalization_version=trusted_cohort.TRUSTED_CANDIDATE_NORMALIZATION_VERSION,
        bundle_manifest_sha256=DIGEST,
        bundle_inventory_sha256=DIGEST,
        bundle_path="runs/readme-poc/example",
    )


def _registry_file(tmp_path: Path, entries: list[ProductEntry]) -> Path:
    path = tmp_path / "products.json"
    path.write_text(
        json.dumps([entry.model_dump(mode="json") for entry in entries]),
        encoding="utf-8",
    )
    return path


def _patch_valid_members(
    monkeypatch: pytest.MonkeyPatch,
    states: dict[str, RunStateV2 | None],
) -> None:
    def validate(entry, state, bundle_dir, **kwargs):
        del bundle_dir, kwargs
        return _member(entry, state), []

    monkeypatch.setattr(trusted_cohort, "_validate_member_bundle", validate)


def test_build_accounts_for_every_entry_and_uses_stable_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _entry("B", 2)
    second = _entry("A", 1)
    states = {
        first.org_repo: _state(first.org_repo),
        second.org_repo: _state(
            second.org_repo,
            status="SYSTEM_FAILURE",
            assurance="trusted_inherited",
        ),
    }
    _patch_valid_members(monkeypatch, states)
    cohort = trusted_cohort.build_qualified_trusted_cohort(
        [first, second],
        states,
        registry_path=_registry_file(tmp_path, [first, second]),
        control_revision="c" * 40,
        observe_head=lambda _: SHA,
    )

    assert [member.org_repo for member in cohort.members] == [first.org_repo]
    assert [item.org_repo for item in cohort.exclusions] == [second.org_repo]
    assert cohort.registry_denominator == 2
    assert cohort.exclusions[0].reasons == ("lifecycle_not_trusted_no_op_proven",)


def test_stale_and_checksum_invalid_terminals_are_excluded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fresh = _entry("A", 1)
    stale = _entry("B", 2)
    corrupt = _entry("C", 3)
    entries = [fresh, stale, corrupt]
    states = {entry.org_repo: _state(entry.org_repo) for entry in entries}

    def validate(entry, state, bundle_dir, **kwargs):
        del bundle_dir, kwargs
        if entry.org_repo == corrupt.org_repo:
            return None, ["trusted_bundle_checksum_inventory_invalid"]
        return _member(entry, state), []

    monkeypatch.setattr(trusted_cohort, "_validate_member_bundle", validate)
    cohort = trusted_cohort.build_qualified_trusted_cohort(
        entries,
        states,
        registry_path=_registry_file(tmp_path, entries),
        control_revision="c" * 40,
        observe_head=lambda clone_url: "d" * 40 if clone_url == stale.clone_url else SHA,
    )

    assert [member.org_repo for member in cohort.members] == [fresh.org_repo]
    by_repo = {item.org_repo: item for item in cohort.exclusions}
    assert by_repo[stale.org_repo].reasons == ("target_head_drifted",)
    assert by_repo[corrupt.org_repo].reasons == ("trusted_bundle_checksum_inventory_invalid",)


def test_schema_rejects_noncurrent_member() -> None:
    entry = _entry("A", 1)
    state = _state(entry.org_repo)
    payload = _member(entry, state).model_dump(mode="json")
    payload["observed_target_head"] = "d" * 40
    with pytest.raises(ValueError, match="must match the target head"):
        QualifiedTrustedCohortMemberV1.model_validate(payload)


def test_missing_checksum_inventory_fails_member_qualification(tmp_path: Path) -> None:
    entry = _entry("A", 1)
    state = _state(entry.org_repo)
    member, reasons = validate_trusted_cohort_member(
        entry,
        state,
        tmp_path / "missing",
        reviewer_standard=DIGEST,
        prompt_content=DIGEST,
        prompt_dependencies={"trusted": DIGEST},
        prompt_hashes={"trusted": DIGEST},
    )

    assert member is None
    assert reasons == ["trusted_bundle_checksum_inventory_invalid"]


def test_write_is_idempotent_and_reconstruction_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = _entry("A", 1)
    state = _state(entry.org_repo)
    states = {entry.org_repo: state}
    _patch_valid_members(monkeypatch, states)
    registry_path = _registry_file(tmp_path, [entry])
    cohort = trusted_cohort.build_qualified_trusted_cohort(
        [entry],
        states,
        registry_path=registry_path,
        control_revision="c" * 40,
        observe_head=lambda _: SHA,
    )
    frozen, cohort_dir = trusted_cohort.write_qualified_trusted_cohort(
        cohort,
        output_root=tmp_path / "cohorts",
    )
    repeated, repeated_dir = trusted_cohort.write_qualified_trusted_cohort(
        cohort.model_copy(update={"frozen_at": "later"}),
        output_root=tmp_path / "cohorts",
    )
    reconstruction = trusted_cohort.verify_qualified_trusted_cohort(
        frozen,
        [entry],
        states,
        registry_path=registry_path,
        control_revision="c" * 40,
        observe_head=lambda _: SHA,
        cohort_dir=cohort_dir,
    )

    assert repeated == frozen
    assert repeated_dir == cohort_dir
    assert reconstruction.passed is True
    assert reconstruction.reconstructed_cohort_id == frozen.cohort_id
