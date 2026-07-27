"""Select registry or isolated source-build truth for one package."""

from __future__ import annotations

from collections.abc import Callable

from readme_agent.ecosystems.foss_coordinate import canonical_foss_coordinate
from readme_agent.ecosystems.registry_request import registry_request_url
from readme_agent.ecosystems.resolver import ResolutionResult, resolve
from readme_agent.facts.acquisition_schema import (
    AcquisitionDecisionV1,
    RegistryReceiptV1,
    SourceBuildReceiptV1,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.registry.models import ProductEntry

_REGISTRY_METHOD_NAMES = {
    "java": "maven_central",
    "python": "pypi",
    "net": "nuget",
    "typescript": "npm",
    "go": "go_proxy",
    "rust": "crates_io",
}
AcquisitionResolver = Callable[[str, dict[str, str]], ResolutionResult]


def _registry_receipt(
    resolver_ecosystem: str,
    coordinate: dict[str, str],
    result: ResolutionResult,
) -> RegistryReceiptV1 | None:
    expected_url = registry_request_url(resolver_ecosystem, coordinate)
    if (
        expected_url is None
        or result.registry_label is None
        or result.request_url is None
        or result.request_url != expected_url
        or result.status_code is None
        or result.response_sha256 is None
        or result.retrieved_at is None
    ):
        return None
    return RegistryReceiptV1(
        resolver_ecosystem=resolver_ecosystem,
        registry_label=result.registry_label,
        coordinate=coordinate,
        request_url=result.request_url,
        status_code=result.status_code,
        response_sha256=result.response_sha256,
        retrieved_at=result.retrieved_at,
        found=result.found,
        detail=result.detail,
    )


def _source_build_receipt(
    verification: LocalProductVerificationV1 | None,
    *,
    org_repo: str,
    source_revision: str,
) -> SourceBuildReceiptV1 | None:
    if (
        verification is None
        or verification.outcome != "SOURCE_BUILD_VERIFIED"
        or not verification.truth_eligible
        or verification.isolated_execution is None
        or verification.org_repo != org_repo
        or verification.source_revision != source_revision
        or verification.isolated_execution.org_repo != org_repo
        or verification.isolated_execution.source_revision != source_revision
    ):
        return None
    isolated = verification.isolated_execution
    pins = {
        f"container_image={isolated.policy.immutable_image}",
        f"input_sha256={isolated.input_sha256}",
        f"source_revision={verification.source_revision}",
    }
    if verification.public_api_sha256 is not None:
        pins.add(f"public_api_sha256={verification.public_api_sha256}")
    if verification.rust_source_dependency is not None:
        pins.add(f"rust_source_dependency={verification.rust_source_dependency}")
    return SourceBuildReceiptV1(
        org_repo=org_repo,
        source_revision=verification.source_revision,
        argv=isolated.argv,
        input_sha256=isolated.input_sha256,
        policy_sha256=isolated.policy_sha256,
        immutable_image=isolated.policy.immutable_image,
        dependency_pins=sorted(pins),
        cleanup_complete=True,
        return_code=0,
        truth_eligible=True,
    )


def select_acquisition(
    *,
    entry: ProductEntry,
    source_revision: str,
    local_verification: LocalProductVerificationV1 | None,
    unavailable_detail: str,
    resolution: ResolutionResult | None = None,
    resolver: AcquisitionResolver | None = None,
) -> AcquisitionDecisionV1:
    """Prefer authoritative publication and otherwise require isolated source proof."""

    if entry.ecosystem is None:
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem="unknown",
            method="unresolved",
            outcome="CAPABILITY_GAP",
            detail="registry entry has no ecosystem",
            truth_eligible=False,
        )
    resolver_ecosystem, coordinate = canonical_foss_coordinate(
        entry.family,
        entry.ecosystem,
        entry.org,
        entry.repo_name,
    )
    source_receipt = _source_build_receipt(
        local_verification,
        org_repo=entry.org_repo,
        source_revision=source_revision,
    )
    if resolver_ecosystem is None:
        if source_receipt is not None:
            assert local_verification is not None
            return AcquisitionDecisionV1(
                org_repo=entry.org_repo,
                source_revision=source_revision,
                ecosystem=entry.ecosystem,
                method="source_build",
                outcome="SOURCE_BUILD_VERIFIED",
                detail=local_verification.detail,
                source_build_receipt=source_receipt,
                truth_eligible=True,
            )
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem=entry.ecosystem,
            method="unresolved",
            outcome="CAPABILITY_GAP",
            detail="no canonical FOSS registry coordinate and no isolated source-build proof",
            truth_eligible=False,
        )

    registry_result = resolution or (resolver or resolve)(resolver_ecosystem, coordinate)
    receipt = _registry_receipt(resolver_ecosystem, coordinate, registry_result)
    method = _REGISTRY_METHOD_NAMES.get(resolver_ecosystem, resolver_ecosystem)
    if registry_result.found:
        if receipt is None:
            return AcquisitionDecisionV1(
                org_repo=entry.org_repo,
                source_revision=source_revision,
                ecosystem=entry.ecosystem,
                method=method,
                outcome="BLOCKED_NETWORK",
                detail="registry reported publication without a checksum-complete HTTP receipt",
                coordinate=coordinate,
                truth_eligible=False,
            )
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem=entry.ecosystem,
            method=method,
            outcome="REGISTRY_VERIFIED",
            detail=registry_result.detail,
            coordinate=coordinate,
            registry_receipt=receipt,
            truth_eligible=True,
        )
    if registry_result.blocked:
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem=entry.ecosystem,
            method=method,
            outcome="BLOCKED_NETWORK",
            detail=registry_result.detail,
            coordinate=coordinate,
            truth_eligible=False,
        )
    if receipt is None:
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem=entry.ecosystem,
            method=method,
            outcome="NOT_PUBLISHED",
            detail="registry absence lacks a checksum-complete HTTP receipt",
            coordinate=coordinate,
            truth_eligible=False,
        )
    if source_receipt is not None:
        assert local_verification is not None
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem=entry.ecosystem,
            method="source_build",
            outcome="SOURCE_BUILD_VERIFIED",
            detail=local_verification.detail,
            coordinate=coordinate,
            registry_receipt=receipt,
            source_build_receipt=source_receipt,
            truth_eligible=True,
        )
    outcome = (
        local_verification.outcome
        if local_verification is not None and local_verification.outcome != "SOURCE_BUILD_VERIFIED"
        else "BLOCKED_LOCAL_VERIFICATION"
    )
    detail = (
        "isolated source-build proof does not match the selected repository revision"
        if local_verification is not None and local_verification.outcome == "SOURCE_BUILD_VERIFIED"
        else local_verification.detail
        if local_verification is not None
        else unavailable_detail
    )
    return AcquisitionDecisionV1(
        org_repo=entry.org_repo,
        source_revision=source_revision,
        ecosystem=entry.ecosystem,
        method="source_build",
        outcome=outcome,
        detail=detail,
        coordinate=coordinate,
        registry_receipt=receipt,
        truth_eligible=False,
    )


def reconcile_acquisition(
    *,
    entry: ProductEntry,
    prior: AcquisitionDecisionV1,
    local_verification: LocalProductVerificationV1 | None,
) -> AcquisitionDecisionV1:
    """Re-evaluate a prior registry decision after isolated source proof becomes available."""

    if prior.org_repo != entry.org_repo:
        raise ValueError(f"prior acquisition belongs to {prior.org_repo!r}, not {entry.org_repo!r}")
    if prior.outcome == "REGISTRY_VERIFIED":
        return prior
    receipt = prior.registry_receipt
    if receipt is not None:
        resolution = ResolutionResult(
            found=receipt.found,
            detail=receipt.detail,
            registry_label=receipt.registry_label,
            request_url=receipt.request_url,
            status_code=receipt.status_code,
            response_sha256=receipt.response_sha256,
            retrieved_at=receipt.retrieved_at,
        )
        return select_acquisition(
            entry=entry,
            source_revision=prior.source_revision,
            local_verification=local_verification,
            unavailable_detail=prior.detail,
            resolution=resolution,
        )
    if prior.coordinate is None:
        return select_acquisition(
            entry=entry,
            source_revision=prior.source_revision,
            local_verification=local_verification,
            unavailable_detail=prior.detail,
        )
    # Network uncertainty or a legacy record without a receipt cannot be repaired by
    # source proof: publication precedence remains unknown, so preserve the block.
    return prior
