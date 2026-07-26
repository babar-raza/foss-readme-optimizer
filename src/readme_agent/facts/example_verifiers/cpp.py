"""Build a CMake repository and syntax-check its exact C++ README example."""

from __future__ import annotations

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
    """Use CMake plus an installed compiler; never execute repository output."""
    cmake = shutil.which("cmake")
    compiler = next(
        (path for name in ("clang++", "g++", "c++", "cl") if (path := shutil.which(name))),
        None,
    )
    if cmake is None or compiler is None:
        missing = "cmake" if cmake is None else "C++ compiler"
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="cpp",
            outcome="BLOCKED_TOOLCHAIN",
            detail=f"required executable is unavailable: {missing}",
            build=missing_tool_result(missing),
        )

    environment = disposable_profile_environment(workspace)
    build_dir = workspace.parent / "cmake-build"
    configure = execute_example(
        [cmake, "-S", str(workspace), "-B", str(build_dir)],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=environment,
    )
    if configure.return_code != 0:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="cpp",
            outcome="BUILD_FAILED",
            detail="CMake configure failed",
            build=configure,
        )
    build = execute_example(
        [cmake, "--build", str(build_dir), "--config", "Release"],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=environment,
    )
    if build.return_code != 0:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="cpp",
            outcome="BUILD_FAILED",
            detail="CMake source build failed",
            build=build,
        )

    example_path = workspace.parent / "readme-agent-example.cpp"
    example_path.write_text(example.code, encoding="utf-8")
    include_roots = {
        candidate.resolve()
        for package_root in snapshot.package_roots
        if package_root.ecosystem == "cpp"
        for candidate in (
            workspace / Path(package_root.manifest_path).parent / "include",
            workspace / Path(package_root.manifest_path).parent / "src",
        )
        if candidate.is_dir()
    }
    include_roots.update(
        candidate.resolve()
        for candidate in (workspace / "include", workspace / "src")
        if candidate.is_dir()
    )
    include_args = [
        argument
        for candidate in sorted(include_roots)
        for argument in (
            [f"/I{candidate}"]
            if Path(compiler).name.lower() == "cl.exe"
            else ["-I", str(candidate)]
        )
    ]
    compile_args = (
        [compiler, "/nologo", "/std:c++17", "/Zs", *include_args, str(example_path)]
        if Path(compiler).name.lower() == "cl.exe"
        else [compiler, "-std=c++17", "-fsyntax-only", *include_args, str(example_path)]
    )
    compiled = execute_example(
        compile_args,
        workspace=workspace,
        timeout_seconds=300,
        base_environment=environment,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="cpp",
        outcome="SOURCE_BUILD_VERIFIED" if compiled.return_code == 0 else "BUILD_FAILED",
        detail=(
            "CMake source build and exact README example syntax check passed"
            if compiled.return_code == 0
            else "exact README C++ example syntax check failed"
        ),
        build=build,
        example_compile=compiled,
    )
