"""Build a Cargo repository and check its exact Rust README example."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from readme_agent.facts.example_execution import execute_example
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.example_verifiers.common import (
    disposable_profile_environment,
    missing_tool_result,
)
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    """Use Cargo's native project and example targets in a credential-free profile."""
    cargo = shutil.which("cargo")
    if cargo is None:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="rust",
            outcome="BLOCKED_TOOLCHAIN",
            detail="required executable is unavailable: cargo",
            build=missing_tool_result("cargo"),
        )

    environment = disposable_profile_environment(workspace)
    cargo_home = workspace.parent / "cargo-home"
    environment["CARGO_HOME"] = str(cargo_home)
    environment["CARGO_TERM_COLOR"] = "never"
    rustup_home = os.environ.get("RUSTUP_HOME")
    if rustup_home:
        environment["RUSTUP_HOME"] = rustup_home
    locked = ["--locked"] if (workspace / "Cargo.lock").is_file() else []
    build = execute_example(
        [cargo, "check", *locked],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=environment,
    )
    if build.return_code != 0:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="rust",
            outcome="BUILD_FAILED",
            detail="Cargo source check failed",
            build=build,
        )

    examples = workspace / "examples"
    examples.mkdir(exist_ok=True)
    example_name = "readme_agent_example"
    (examples / f"{example_name}.rs").write_text(example.code, encoding="utf-8")
    compiled = execute_example(
        [cargo, "check", *locked, "--example", example_name],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=environment,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="rust",
        outcome="SOURCE_BUILD_VERIFIED" if compiled.return_code == 0 else "BUILD_FAILED",
        detail=(
            "Cargo source check and exact README example check passed"
            if compiled.return_code == 0
            else "exact README Rust example check failed"
        ),
        build=build,
        example_compile=compiled,
    )
