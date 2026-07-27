"""Workload-specific dependency inventories for isolated source acquisition."""

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1
from readme_agent.ecosystems.rust_api_schema import RustPackageLayoutV1
from readme_agent.ecosystems.typescript_api_schema import TypeScriptPackageLayoutV1
from readme_agent.facts.acquisition_pins import (
    python_acquisition_pins,
    rust_acquisition_pins,
    typescript_acquisition_pins,
)
from readme_agent.facts.rust_consumer_schema import RustConsumerProofV1
from readme_agent.facts.rust_dependency_schema import RustDependencyAcquisitionV1
from readme_agent.facts.typescript_consumer_schema import TypeScriptConsumerProofV1
from readme_agent.facts.typescript_toolchain import (
    TypeScriptToolchainArtifactV1,
    TypeScriptToolchainLockV1,
)


def test_python_pins_exact_distributed_source_tree():
    package = PythonPackageLayoutV1(
        manifest_path="pyproject.toml",
        distribution_name="widget",
        source_root="src",
        package_paths=["src/widget"],
        canonical_import="widget",
        source_sha256="a" * 64,
    )

    assert python_acquisition_pins(package) == ["python_package_source_sha256=" + "a" * 64]


def test_typescript_pins_built_artifact_compiler_and_every_archive():
    package = TypeScriptPackageLayoutV1(
        manifest_path="package.json",
        package_name="@acme/widget",
        build_config_path="tsconfig.json",
        source_root="src",
        output_root="dist",
        exports_restrict_subpaths=True,
        source_sha256="a" * 64,
    )
    toolchain = TypeScriptToolchainLockV1(
        compiler_version="5.8.3",
        immutable_image="node@sha256:" + "b" * 64,
        artifacts=[
            TypeScriptToolchainArtifactV1(
                name="typescript",
                version="5.8.3",
                filename="typescript.tgz",
                url="https://registry.example/typescript.tgz",
                sha256="c" * 64,
            )
        ],
    )
    proof = TypeScriptConsumerProofV1.model_construct(
        accepted=True,
        built_artifact_sha256="d" * 64,
        package=package,
        toolchain=toolchain,
    )

    assert typescript_acquisition_pins(proof) == [
        "typescript_package_source_sha256=" + "a" * 64,
        "typescript_built_artifact_sha256=" + "d" * 64,
        "typescript_compiler_version=5.8.3",
        "typescript_toolchain_typescript@5.8.3_sha256=" + "c" * 64,
    ]


def test_rust_pins_source_and_complete_locked_vendor_bundle():
    package = RustPackageLayoutV1(
        manifest_path="Cargo.toml",
        package_root=".",
        package_name="widget",
        crate_name="widget",
        edition="2021",
        lib_path="src/lib.rs",
        dependency_names=["serde"],
        example_paths=[],
        test_paths=[],
        acquisition="pinned_source",
        manifest_sha256="a" * 64,
        source_sha256="b" * 64,
    )
    acquisition = RustDependencyAcquisitionV1.model_construct(
        snapshot_inventory_sha256="c" * 64,
        lockfile_sha256="d" * 64,
        vendor_sha256="e" * 64,
        config_sha256="f" * 64,
        lock_package_count=7,
    )
    proof = RustConsumerProofV1.model_construct(
        accepted=True,
        package=package,
        acquisition=acquisition,
    )

    assert rust_acquisition_pins(proof) == [
        "rust_package_source_sha256=" + "b" * 64,
        "rust_manifest_sha256=" + "a" * 64,
        "rust_dependency_snapshot_inventory_sha256=" + "c" * 64,
        "rust_dependency_lockfile_sha256=" + "d" * 64,
        "rust_dependency_vendor_sha256=" + "e" * 64,
        "rust_dependency_config_sha256=" + "f" * 64,
        "rust_dependency_package_count=7",
    ]


def test_unaccepted_compiler_proofs_publish_no_dependency_inventory():
    typescript = TypeScriptConsumerProofV1.model_construct(
        accepted=False,
        built_artifact_sha256=None,
    )
    rust = RustConsumerProofV1.model_construct(accepted=False)

    assert typescript_acquisition_pins(typescript) == []
    assert rust_acquisition_pins(rust) == []
