"""Compile exact C++ consumers against immutable repository source in Docker."""

from __future__ import annotations

import re
import shlex
import tempfile
from collections.abc import Callable
from pathlib import Path

from readme_agent.facts.compiled_consumer import (
    compiled_proof,
    copy_snapshot,
    dependency_pins,
    diagnostic,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

GCC_14_IMAGE = "gcc@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15"
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]


def _package_root(snapshot: RepositorySnapshotV1) -> Path:
    candidates = [
        path.parent
        for path in snapshot.root_path.rglob("CMakeLists.txt")
        if (path.parent / "include").is_dir() and (path.parent / "src").is_dir()
    ]
    if not candidates:
        raise ValueError("C++ repository has no CMake package with include/ and src/")
    return min(candidates, key=lambda path: (len(path.parts), path.as_posix()))


def _selected_sources(
    snapshot: RepositorySnapshotV1,
    package_root: Path,
    code: str,
) -> tuple[list[str], list[str]]:
    includes = sorted(set(re.findall(r'(?m)^\s*#include\s+"([^"]+)"', code)))
    resolved = [
        package_root / "include" / include
        for include in includes
        if (package_root / "include" / include).is_file()
    ]
    if not resolved:
        raise ValueError("C++ example includes no repository public header")
    paths = [path.relative_to(snapshot.root_path).as_posix() for path in resolved]
    paths.append((package_root / "CMakeLists.txt").relative_to(snapshot.root_path).as_posix())
    namespace = re.findall(r"(?m)^\s*using\s+namespace\s+([^;]+);", code)
    symbols = [*includes, *namespace]
    return sorted(set(paths)), sorted(set(symbols))


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    *,
    executor: IsolatedExecutor = execute_isolated,
    immutable_image: str = GCC_14_IMAGE,
) -> LocalProductVerificationV1:
    """Compile the exact external consumer against public source headers."""

    verify_repository_snapshot(snapshot)
    package_root = _package_root(snapshot)
    source_paths, symbols = _selected_sources(snapshot, package_root, example.code)
    relative_root = package_root.relative_to(snapshot.root_path).as_posix()
    quoted_root = shlex.quote(relative_root)
    with tempfile.TemporaryDirectory(prefix="readme-agent-cpp-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        copy_snapshot(snapshot, workspace)
        consumer_dir = workspace / ".readme-agent"
        consumer_dir.mkdir()
        (consumer_dir / "example.cpp").write_text(example.code, encoding="utf-8", newline="\n")
        command = (
            "g++ --version | head -n 1; "
            f"g++ -std=c++17 -fsyntax-only -I {quoted_root}/include "
            ".readme-agent/example.cpp"
        )
        execution = executor(
            IsolatedExecutionRequestV1(
                org_repo=snapshot.org_repo,
                source_revision=snapshot.source_revision,
                source_root=workspace,
                argv=["/bin/sh", "-euc", command],
                environment={"HOME": "/tmp", "TMPDIR": "/tmp"},
                policy=IsolatedExecutionPolicyV1(
                    immutable_image=immutable_image,
                    timeout_seconds=300,
                    memory_mebibytes=1536,
                    pids_limit=128,
                ),
            )
        )
    verify_repository_snapshot(snapshot)
    proof = compiled_proof(
        snapshot=snapshot,
        ecosystem="cpp",
        source_paths=source_paths,
        selected_symbols=symbols,
        example_code=example.code,
        execution=execution,
    )
    result = diagnostic(execution)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="cpp",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "exact C++ consumer compiled against immutable repository source"
            if proof.accepted
            else "isolated C++ source or exact consumer compilation failed"
        ),
        build=result,
        example_compile=result,
        isolated_execution=execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.selected_symbols if proof.accepted else [],
        public_api_sha256=proof.source_sha256,
        acquisition_dependency_pins=dependency_pins(proof, "cpp_language_standard=17"),
        compiled_consumer=proof,
    )
