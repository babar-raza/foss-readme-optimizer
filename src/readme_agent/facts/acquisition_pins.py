"""Derive exact workload dependency pins for isolated source acquisition."""

from __future__ import annotations

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1
from readme_agent.facts.rust_consumer_schema import RustConsumerProofV1
from readme_agent.facts.typescript_consumer_schema import TypeScriptConsumerProofV1


def python_acquisition_pins(package: PythonPackageLayoutV1) -> list[str]:
    """Bind Python source acquisition to the distributed package tree."""

    return [f"python_package_source_sha256={package.source_sha256}"]


def typescript_acquisition_pins(proof: TypeScriptConsumerProofV1) -> list[str]:
    """Bind TypeScript acquisition to source, built artifact, compiler, and archives."""

    if not proof.accepted or proof.built_artifact_sha256 is None:
        return []
    return [
        f"typescript_package_source_sha256={proof.package.source_sha256}",
        f"typescript_built_artifact_sha256={proof.built_artifact_sha256}",
        f"typescript_compiler_version={proof.toolchain.compiler_version}",
        *[
            (f"typescript_toolchain_{artifact.name}@{artifact.version}_sha256={artifact.sha256}")
            for artifact in proof.toolchain.artifacts
        ],
    ]


def rust_acquisition_pins(proof: RustConsumerProofV1) -> list[str]:
    """Bind Rust acquisition to source plus the exact locked vendor bundle."""

    if not proof.accepted:
        return []
    acquisition = proof.acquisition
    return [
        f"rust_package_source_sha256={proof.package.source_sha256}",
        f"rust_manifest_sha256={proof.package.manifest_sha256}",
        (f"rust_dependency_snapshot_inventory_sha256={acquisition.snapshot_inventory_sha256}"),
        f"rust_dependency_lockfile_sha256={acquisition.lockfile_sha256}",
        f"rust_dependency_vendor_sha256={acquisition.vendor_sha256}",
        f"rust_dependency_config_sha256={acquisition.config_sha256}",
        f"rust_dependency_package_count={acquisition.lock_package_count}",
    ]
