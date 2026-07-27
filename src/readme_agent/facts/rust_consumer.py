"""Compile an exact external Rust consumer against a locked vendored source snapshot."""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from readme_agent.ecosystems.rust_api_schema import (
    RustConsumerExampleV1,
    RustPackageLayoutV1,
    RustPublicApiSurfaceV1,
)
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.rust_consumer_schema import RustConsumerProofV1
from readme_agent.facts.rust_dependency_acquisition import (
    RUST_188_IMAGE,
    RustDependencyBundle,
    acquire_rust_dependencies,
    materialize_rust_dependencies,
    rust_consumer_manifest,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

_COPY_IGNORE = shutil.ignore_patterns(".git", "target")
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]
DependencyAcquirer = Callable[
    [RepositorySnapshotV1, RustPackageLayoutV1],
    RustDependencyBundle,
]


def _selected_symbols(
    surface: RustPublicApiSurfaceV1,
    example: RustConsumerExampleV1,
) -> list[str]:
    available = {symbol.qualified_name for symbol in surface.symbols}
    missing = sorted(set(example.required_symbols) - available)
    if missing:
        raise ValueError(f"Rust example selects non-public symbols: {missing}")
    unused: list[str] = []
    for qualified_name in example.required_symbols:
        parts = qualified_name.rsplit("::", 1)[-1].split(".")
        root, members = parts[0], parts[1:]
        root_used = len(re.findall(rf"\b{re.escape(root)}\b", example.code)) >= 2
        members_used = all(
            re.search(rf"(?:\.|::){re.escape(member)}\b", example.code) is not None
            for member in members
        )
        if not root_used or not members_used:
            unused.append(qualified_name)
    if unused:
        raise ValueError(
            f"Rust example must import and use selected public symbols: {sorted(unused)}"
        )
    return sorted(set(example.required_symbols))


def _diagnostics(result: IsolatedExecutionResultV1) -> list[str]:
    if result.return_code == 0:
        return []
    return [
        line.strip() for line in f"{result.stdout}\n{result.stderr}".splitlines() if line.strip()
    ][-100:]


def prove_rust_consumer(
    snapshot: RepositorySnapshotV1,
    package: RustPackageLayoutV1,
    surface: RustPublicApiSurfaceV1,
    example: RustConsumerExampleV1,
    *,
    acquirer: DependencyAcquirer = acquire_rust_dependencies,
    executor: IsolatedExecutor = execute_isolated,
    immutable_image: str = RUST_188_IMAGE,
) -> RustConsumerProofV1:
    """Run locked, offline Cargo check over a separate exact consumer crate."""

    verify_repository_snapshot(snapshot)
    if surface.org_repo != snapshot.org_repo or surface.source_revision != snapshot.source_revision:
        raise ValueError("Rust surface does not belong to the immutable repository snapshot")
    if surface.package != package:
        raise ValueError("Rust package layout does not match the public API surface")
    selected = _selected_symbols(surface, example)
    bundle = acquirer(snapshot, package)
    if (
        bundle.acquisition.org_repo != snapshot.org_repo
        or bundle.acquisition.source_revision != snapshot.source_revision
        or bundle.acquisition.snapshot_inventory_sha256 != snapshot.inventory_sha256
        or bundle.acquisition.package_source_sha256 != package.source_sha256
        or bundle.acquisition.image.requested_reference != immutable_image
    ):
        raise ValueError("Rust dependency acquisition does not match the immutable source")
    with tempfile.TemporaryDirectory(prefix="readme-agent-rust-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        package_copy = workspace / "package"
        consumer = workspace / "consumer"
        shutil.copytree(snapshot.root_path, package_copy, ignore=_COPY_IGNORE)
        (consumer / "src").mkdir(parents=True)
        (consumer / "Cargo.toml").write_text(
            rust_consumer_manifest(package),
            encoding="utf-8",
            newline="\n",
        )
        (consumer / "src/main.rs").write_text(
            example.code,
            encoding="utf-8",
            newline="\n",
        )
        materialize_rust_dependencies(bundle, workspace)
        shutil.copy2(workspace / "Cargo.lock", consumer / "Cargo.lock")
        request = IsolatedExecutionRequestV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            source_root=workspace,
            argv=[
                "cargo",
                "check",
                "--locked",
                "--offline",
                "--manifest-path",
                "consumer/Cargo.toml",
            ],
            environment={
                "CARGO_HOME": "/tmp/cargo",
                "CARGO_TERM_COLOR": "never",
                "HOME": "/tmp",
            },
            policy=IsolatedExecutionPolicyV1(
                immutable_image=immutable_image,
                timeout_seconds=600,
                memory_mebibytes=1024,
                pids_limit=96,
            ),
        )
        result = executor(request)
    verify_repository_snapshot(snapshot)
    diagnostics = _diagnostics(result)
    accepted = result.truth_eligible and result.return_code == 0 and not diagnostics
    return RustConsumerProofV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        package=package,
        surface=surface,
        example=example,
        acquisition=bundle.acquisition,
        verified_symbols=selected if accepted else [],
        missing_symbols=[] if accepted else selected,
        diagnostics=diagnostics,
        isolated_execution=result,
        accepted=accepted,
    )
