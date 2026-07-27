"""Verify Rust README examples against syntax-resolved public API and locked Cargo."""

from __future__ import annotations

from readme_agent.ecosystems.rust_api_schema import RustConsumerExampleV1
from readme_agent.ecosystems.rust_format_truth import extract_rust_format_evidence
from readme_agent.ecosystems.rust_package_layout import (
    inspect_rust_package_layout,
    pinned_rust_git_dependency,
)
from readme_agent.ecosystems.rust_public_api import inspect_rust_public_api
from readme_agent.facts.acquisition_pins import rust_acquisition_pins
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.rust_consumer import prove_rust_consumer
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1


def _diagnostic(result) -> ExampleExecutionResultV1:
    return ExampleExecutionResultV1(
        argv=result.argv,
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=result.timed_out,
        environment_names=result.environment_names,
        isolation_kind="isolated_result_projection",
    )


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
) -> LocalProductVerificationV1:
    """Compile the exact consumer using only public, source-pinned Rust facts."""

    package = inspect_rust_package_layout(snapshot.root_path)
    surface = inspect_rust_public_api(
        snapshot.root_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    consumer = RustConsumerExampleV1(
        code=example.code,
        required_symbols=example.required_symbols,
    )
    proof = prove_rust_consumer(snapshot, package, surface, consumer)
    diagnostic = _diagnostic(proof.isolated_execution)
    formats = extract_rust_format_evidence(surface)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="rust",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "source-pinned crate and exact external Rust consumer passed locked offline Cargo check"
            if proof.accepted
            else "locked offline Cargo check rejected the source-pinned Rust consumer"
        ),
        build=diagnostic,
        example_compile=diagnostic,
        isolated_execution=proof.isolated_execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.verified_symbols,
        public_api_sha256=surface.canonical_hash(),
        rust_package=package,
        rust_formats=formats,
        rust_source_dependency=pinned_rust_git_dependency(
            package,
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
        ),
        acquisition_dependency_pins=rust_acquisition_pins(proof),
    )
