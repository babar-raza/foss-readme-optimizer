"""Verify source acquisition and exact examples in disposable secret-free workspaces."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent import env
from readme_agent.facts.example_execution import ExampleExecutionResultV1, execute_example
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot


class LocalProductVerificationV1(BaseModel):
    """Bounded build and exact-example result for one immutable snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    org_repo: str
    source_revision: str
    ecosystem: str
    outcome: Literal["SOURCE_BUILD_VERIFIED", "BLOCKED_TOOLCHAIN", "BUILD_FAILED"]
    detail: str
    build: ExampleExecutionResultV1
    example_compile: ExampleExecutionResultV1 | None = None


_CACHE: dict[str, LocalProductVerificationV1] = {}
_CACHE_LOCK = Lock()
_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
)


def _cache_key(snapshot: RepositorySnapshotV1, example: MinimalExamplePolicy) -> str:
    payload = "\0".join(
        [
            snapshot.org_repo,
            snapshot.source_revision,
            snapshot.inventory_sha256,
            example.language,
            example.class_name,
            example.code,
            env.java_home() or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _java_toolchain_blocked(result: ExampleExecutionResultV1) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    signals = (
        "invalid target release",
        "release version 21 not supported",
        "source option 21 is not supported",
        "target option 21 is not supported",
        "java_home",
        "mvn is not recognized",
        "javac is not recognized",
    )
    return result.return_code in {2, 9009} or any(signal in text for signal in signals)


def _missing_tool_result(tool: str) -> ExampleExecutionResultV1:
    return ExampleExecutionResultV1(
        argv=[tool],
        return_code=9009,
        stdout="",
        stderr=f"required executable is not available on PATH: {tool}",
        timed_out=False,
        environment_names=[],
    )


def _verify_java(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    maven = shutil.which("mvn")
    java_home = Path(configured_home) if (configured_home := env.java_home()) else None
    javac_name = "javac.exe" if os.name == "nt" else "javac"
    configured_javac = java_home / "bin" / javac_name if java_home is not None else None
    javac = (
        str(configured_javac)
        if configured_javac is not None and configured_javac.is_file()
        else shutil.which("javac")
    )
    if maven is None or javac is None:
        missing = "mvn" if maven is None else "javac"
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="java",
            outcome="BLOCKED_TOOLCHAIN",
            detail=f"required executable is unavailable: {missing}",
            build=_missing_tool_result(missing),
        )
    process_environment = dict(os.environ)
    if java_home is not None:
        process_environment["JAVA_HOME"] = str(java_home)
        process_environment["PATH"] = (
            f"{java_home / 'bin'}{os.pathsep}{process_environment['PATH']}"
        )
    build = execute_example(
        [maven, "-q", "-DskipTests", "package"],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=process_environment,
    )
    if build.return_code != 0:
        blocked = _java_toolchain_blocked(build)
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="java",
            outcome="BLOCKED_TOOLCHAIN" if blocked else "BUILD_FAILED",
            detail=(
                "required Java/Maven toolchain is unavailable or incompatible"
                if blocked
                else "source build failed"
            ),
            build=build,
        )

    example_path = workspace / f"{example.class_name}.java"
    example_path.write_text(example.code, encoding="utf-8", newline="\n")
    output_path = workspace / "target" / "readme-agent-example"
    output_path.mkdir(parents=True, exist_ok=True)
    compile_result = execute_example(
        [
            javac,
            "-cp",
            str(workspace / "target" / "classes"),
            "-d",
            str(output_path),
            str(example_path),
        ],
        workspace=workspace,
        timeout_seconds=120,
        base_environment=process_environment,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="java",
        outcome=(
            "SOURCE_BUILD_VERIFIED"
            if compile_result.return_code == 0
            else "BLOCKED_TOOLCHAIN"
            if _java_toolchain_blocked(compile_result)
            else "BUILD_FAILED"
        ),
        detail=(
            "source build and exact README example compilation passed"
            if compile_result.return_code == 0
            else "exact README example compilation failed"
        ),
        build=build,
        example_compile=compile_result,
    )


_VERIFIERS = {"java": _verify_java}


def verify_local_product_example(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
) -> LocalProductVerificationV1:
    """Build a disposable copy and compile the policy's exact example."""

    verify_repository_snapshot(snapshot)
    verifier = _VERIFIERS.get(example.language)
    if verifier is None:
        raise ValueError(f"no local example verifier registered for {example.language!r}")
    key = _cache_key(snapshot, example)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
    if cached is not None:
        return cached

    with tempfile.TemporaryDirectory(prefix="readme-agent-product-verification-") as temp:
        workspace = Path(temp) / "repository"
        shutil.copytree(snapshot.root_path, workspace, ignore=_COPY_IGNORE)
        result = verifier(snapshot, example, workspace)
    verify_repository_snapshot(snapshot)
    with _CACHE_LOCK:
        _CACHE[key] = result
    return result
