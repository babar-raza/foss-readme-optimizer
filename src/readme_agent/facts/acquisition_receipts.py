"""Build checksum-complete registry, source-build, and source-tree receipts."""

from readme_agent.ecosystems.registry_request import registry_request_url
from readme_agent.ecosystems.resolver import ResolutionResult
from readme_agent.facts.acquisition_schema import (
    RegistryReceiptV1,
    SourceBuildReceiptV1,
    SourceTreeReceiptV1,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1


def registry_receipt(
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


def source_build_receipt(
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
        or not verification.acquisition_dependency_pins
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
    pins.update(verification.acquisition_dependency_pins)
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


def source_tree_receipt(
    verification: LocalProductVerificationV1 | None,
    *,
    org_repo: str,
    source_revision: str,
) -> SourceTreeReceiptV1 | None:
    if (
        verification is None
        or verification.outcome != "SOURCE_TREE_VERIFIED"
        or verification.ecosystem != "python"
        or not verification.truth_eligible
        or verification.isolated_execution is None
        or verification.org_repo != org_repo
        or verification.source_revision != source_revision
        or verification.isolated_execution.org_repo != org_repo
        or verification.isolated_execution.source_revision != source_revision
        or verification.python_execution_mode != "source_tree"
        or verification.python_source_install_failure != "invalid_build_backend"
        or verification.python_package is None
        or verification.public_api_sha256 is None
        or not verification.verified_public_symbols
        or not verification.acquisition_dependency_pins
    ):
        return None
    isolated = verification.isolated_execution
    pins = {
        f"container_image={isolated.policy.immutable_image}",
        f"input_sha256={isolated.input_sha256}",
        f"public_api_sha256={verification.public_api_sha256}",
        f"source_revision={verification.source_revision}",
        *verification.acquisition_dependency_pins,
    }
    return SourceTreeReceiptV1(
        org_repo=org_repo,
        source_revision=verification.source_revision,
        argv=isolated.argv,
        input_sha256=isolated.input_sha256,
        policy_sha256=isolated.policy_sha256,
        immutable_image=isolated.policy.immutable_image,
        dependency_pins=sorted(pins),
        source_root=verification.python_package.source_root,
        canonical_import=verification.python_package.canonical_import,
        public_api_sha256=verification.public_api_sha256,
        verified_public_symbols=verification.verified_public_symbols,
        source_install_failure=verification.python_source_install_failure,
        cleanup_complete=True,
        return_code=0,
        truth_eligible=True,
    )
