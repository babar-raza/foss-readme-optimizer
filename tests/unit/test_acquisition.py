"""Registry-receipt and isolated source-acquisition selection contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from readme_agent.ecosystems.resolver import ResolutionResult
from readme_agent.facts.acquisition import reconcile_acquisition, select_acquisition
from readme_agent.facts.acquisition_schema import AcquisitionDecisionV1
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionPolicyV1,
    IsolatedExecutionResultV1,
)
from readme_agent.registry.models import ProductEntry

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REVISION = "a" * 40
IMAGE = "python@sha256:" + "b" * 64


def _entry(ecosystem: str = "python") -> ProductEntry:
    return ProductEntry(
        family="3d",
        platform=ecosystem,
        repo_name="Aspose.3D-FOSS-for-Python",
        repo_url=f"https://github.com/{ORG_REPO}",
        clone_url=f"https://github.com/{ORG_REPO}.git",
        active=True,
        discovered_via="fixture",
        mode="dry_run",
        ecosystem=ecosystem,
        policy_profile="fixture",
    )


def _resolution(*, found: bool, blocked: bool = False) -> ResolutionResult:
    status = None if blocked else (200 if found else 404)
    return ResolutionResult(
        found=found,
        detail="network blocked" if blocked else ("found" if found else "NOT FOUND (404)"),
        blocked=blocked,
        registry_label="PyPI",
        request_url="https://pypi.org/pypi/aspose-3d-foss/json",
        status_code=status,
        response_sha256=None if blocked else "c" * 64,
        retrieved_at=datetime.now(UTC),
    )


def _isolated_verification(*, truth_eligible: bool = True) -> LocalProductVerificationV1:
    policy = IsolatedExecutionPolicyV1(immutable_image=IMAGE)
    isolated = IsolatedExecutionResultV1(
        truth_eligible=truth_eligible,
        org_repo=ORG_REPO,
        source_revision=REVISION,
        argv=["python", "-I", ".readme-agent-consumer-driver.py"],
        environment_names=["HOME"],
        input_sha256="d" * 64,
        input_file_count=8,
        policy_sha256="e" * 64,
        policy=policy,
        image=ContainerImageIdentityV1(
            requested_reference=IMAGE,
            repo_digest=IMAGE,
            image_id="sha256:" + "f" * 64,
            operating_system="linux",
            architecture="amd64",
            engine_version="fixture",
        ),
        container_id="fixture",
        process_inventory=[],
        return_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        oom_killed=False,
        started_at="2026-07-27T00:00:00+00:00",
        finished_at="2026-07-27T00:00:01+00:00",
        cleanup=ContainerCleanupV1(
            execution_container_removed=True,
            seed_container_removed=True,
            workspace_volume_removed=True,
        ),
    )
    diagnostic = ExampleExecutionResultV1(
        argv=isolated.argv,
        return_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        environment_names=[],
        isolation_kind="isolated_result_projection",
    )
    return LocalProductVerificationV1(
        org_repo=ORG_REPO,
        source_revision=REVISION,
        ecosystem="python",
        outcome="SOURCE_BUILD_VERIFIED" if truth_eligible else "BUILD_FAILED",
        detail="isolated source install and consumer passed",
        build=diagnostic,
        isolated_execution=isolated if truth_eligible else None,
        truth_eligible=truth_eligible,
    )


def test_registry_publication_wins_over_available_source_build():
    decision = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=_isolated_verification(),
        unavailable_detail="not needed",
        resolution=_resolution(found=True),
    )

    assert decision.outcome == "REGISTRY_VERIFIED"
    assert decision.method == "pypi"
    assert decision.truth_eligible is True
    assert decision.registry_receipt is not None
    assert decision.source_build_receipt is None


def test_registry_404_and_isolated_build_select_reproducible_source():
    decision = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=_isolated_verification(),
        unavailable_detail="not needed",
        resolution=_resolution(found=False),
    )

    assert decision.outcome == "SOURCE_BUILD_VERIFIED"
    assert decision.registry_receipt is not None
    assert decision.registry_receipt.status_code == 404
    assert decision.source_build_receipt is not None
    assert decision.source_build_receipt.network_mode == "none"
    assert decision.source_build_receipt.immutable_image == IMAGE
    assert len(decision.source_build_receipt.dependency_pins) >= 3


def test_later_isolated_proof_reconciles_the_same_negative_registry_receipt():
    prior = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=None,
        unavailable_detail="no example yet",
        resolution=_resolution(found=False),
    )

    reconciled = reconcile_acquisition(
        entry=_entry(),
        prior=prior,
        local_verification=_isolated_verification(),
    )

    assert reconciled.outcome == "SOURCE_BUILD_VERIFIED"
    assert reconciled.registry_receipt == prior.registry_receipt
    assert reconciled.source_build_receipt is not None


def test_network_uncertainty_blocks_even_when_a_source_build_is_available():
    decision = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=_isolated_verification(),
        unavailable_detail="not needed",
        resolution=_resolution(found=False, blocked=True),
    )

    assert decision.outcome == "BLOCKED_NETWORK"
    assert decision.truth_eligible is False
    assert decision.source_build_receipt is None


def test_later_isolated_proof_cannot_override_prior_network_uncertainty():
    prior = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=None,
        unavailable_detail="not needed",
        resolution=_resolution(found=False, blocked=True),
    )

    reconciled = reconcile_acquisition(
        entry=_entry(),
        prior=prior,
        local_verification=_isolated_verification(),
    )

    assert reconciled == prior


def test_unpublished_package_without_isolated_build_remains_blocked():
    decision = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=None,
        unavailable_detail="no verified example",
        resolution=_resolution(found=False),
    )

    assert decision.outcome == "BLOCKED_LOCAL_VERIFICATION"
    assert decision.registry_receipt is not None
    assert decision.source_build_receipt is None
    assert decision.truth_eligible is False


def test_source_build_from_a_different_revision_cannot_prove_acquisition():
    verification = _isolated_verification().model_copy(update={"source_revision": "f" * 40})

    decision = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=verification,
        unavailable_detail="mismatched verification",
        resolution=_resolution(found=False),
    )

    assert decision.outcome == "BLOCKED_LOCAL_VERIFICATION"
    assert decision.source_build_receipt is None
    assert decision.truth_eligible is False


def test_legacy_found_result_without_http_receipt_fails_closed():
    decision = select_acquisition(
        entry=_entry(),
        source_revision=REVISION,
        local_verification=None,
        unavailable_detail="no verified example",
        resolution=ResolutionResult(True, "found without receipt"),
    )

    assert decision.outcome == "BLOCKED_NETWORK"
    assert decision.truth_eligible is False


def test_source_build_decision_cannot_claim_a_coordinate_without_registry_absence():
    with pytest.raises(ValidationError, match="no published coordinate"):
        AcquisitionDecisionV1(
            org_repo=ORG_REPO,
            source_revision=REVISION,
            ecosystem="python",
            method="source_build",
            outcome="SOURCE_BUILD_VERIFIED",
            detail="invalid fixture",
            coordinate={"name": "aspose-3d-foss"},
            source_build_receipt=select_acquisition(
                entry=_entry(),
                source_revision=REVISION,
                local_verification=_isolated_verification(),
                unavailable_detail="not needed",
                resolution=_resolution(found=False),
            ).source_build_receipt,
            truth_eligible=True,
        )
