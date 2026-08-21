"""Select registry or isolated source-build truth for one package."""

from __future__ import annotations

from collections.abc import Callable

from readme_agent.ecosystems.foss_coordinate import canonical_foss_coordinate
from readme_agent.ecosystems.resolver import ResolutionResult, resolve
from readme_agent.facts.acquisition_receipts import (
    registry_receipt,
    source_build_receipt,
    source_tree_receipt,
)
from readme_agent.facts.acquisition_schema import AcquisitionDecisionV1
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


def select_acquisition(
    *,
    entry: ProductEntry,
    source_revision: str,
    local_verification: LocalProductVerificationV1 | None,
    unavailable_detail: str,
    resolution: ResolutionResult | None = None,
    resolver: AcquisitionResolver | None = None,
    manifest_coordinate: dict[str, str] | None = None,
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
    resolver_ecosystem, canonical_coordinate = canonical_foss_coordinate(
        entry.family,
        entry.ecosystem,
        entry.org,
        entry.repo_name,
    )
    coordinate = manifest_coordinate or canonical_coordinate
    source_receipt = source_build_receipt(
        local_verification,
        org_repo=entry.org_repo,
        source_revision=source_revision,
    )
    source_tree_proof = source_tree_receipt(
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

    resolve_coordinate = resolver or resolve
    if resolution is not None:
        registry_result = resolution
    else:
        registry_result = resolve_coordinate(resolver_ecosystem, coordinate)
        if (
            manifest_coordinate
            and manifest_coordinate != canonical_coordinate
            and not registry_result.found
            and not registry_result.blocked
            and canonical_coordinate
        ):
            coordinate = canonical_coordinate
            registry_result = resolve_coordinate(resolver_ecosystem, coordinate)
    receipt = registry_receipt(resolver_ecosystem, coordinate, registry_result)
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
    if source_tree_proof is not None:
        assert local_verification is not None
        return AcquisitionDecisionV1(
            org_repo=entry.org_repo,
            source_revision=source_revision,
            ecosystem=entry.ecosystem,
            method="source_tree",
            outcome="SOURCE_TREE_VERIFIED",
            detail=local_verification.detail,
            coordinate=coordinate,
            registry_receipt=receipt,
            source_tree_receipt=source_tree_proof,
            truth_eligible=True,
        )
    outcome = (
        local_verification.outcome
        if local_verification is not None
        and local_verification.outcome not in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
        else "BLOCKED_LOCAL_VERIFICATION"
    )
    detail = (
        "isolated source-build proof does not match the selected repository revision"
        if local_verification is not None
        and local_verification.outcome in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
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
            manifest_coordinate=receipt.coordinate,
        )
    if prior.coordinate is None:
        return select_acquisition(
            entry=entry,
            source_revision=prior.source_revision,
            local_verification=local_verification,
            unavailable_detail=prior.detail,
            manifest_coordinate=prior.coordinate,
        )
    # Network uncertainty or a legacy record without a receipt cannot be repaired by
    # source proof: publication precedence remains unknown, so preserve the block.
    return prior
