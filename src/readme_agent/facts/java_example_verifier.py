"""Compile exact Java consumers against immutable repository source in Docker."""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from readme_agent.facts import java_toolchain
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

JAVA_21_IMAGE = (
    "eclipse-temurin@sha256:da9d3a4f7650db39b918fc5a2c3da76556fb8cc8e5f3767cdea0bb409286951a"
)
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]


def _selected_sources(snapshot: RepositorySnapshotV1, code: str) -> tuple[list[str], list[str]]:
    imports = sorted(set(re.findall(r"(?m)^\s*import\s+((?:[A-Za-z_]\w*\.)+[A-Z]\w*)\s*;", code)))
    if not imports:
        raise ValueError("Java example imports no concrete repository type")
    paths = [
        f"src/main/java/{qualified.replace('.', '/')}.java"
        for qualified in imports
        if (snapshot.root_path / f"src/main/java/{qualified.replace('.', '/')}.java").is_file()
    ]
    if not paths:
        raise ValueError("Java example imports do not resolve to immutable repository source")
    pom = snapshot.root_path / "pom.xml"
    if pom.is_file():
        paths.append("pom.xml")
    return sorted(set(paths)), imports


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    *,
    executor: IsolatedExecutor = execute_isolated,
    immutable_image: str = JAVA_21_IMAGE,
) -> LocalProductVerificationV1:
    """Compile repository sources and the exact Java example with no network."""

    verify_repository_snapshot(snapshot)
    if re.fullmatch(r"[A-Za-z_]\w*", example.class_name) is None:
        raise ValueError("Java example class name is not a valid identifier")
    source_paths, symbols = _selected_sources(snapshot, example.code)
    release = java_toolchain.required_java_major_version(snapshot.root_path / "pom.xml")
    with tempfile.TemporaryDirectory(prefix="readme-agent-java-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        copy_snapshot(snapshot, workspace)
        consumer_dir = workspace / ".readme-agent"
        consumer_dir.mkdir()
        consumer_path = consumer_dir / f"{example.class_name}.java"
        consumer_path.write_text(example.code, encoding="utf-8", newline="\n")
        command = (
            "javac -version; "
            "find src/main/java -type f -name '*.java' -print | sort > /tmp/java-sources.txt; "
            "test -s /tmp/java-sources.txt; "
            f"javac --release {release} -d /tmp/classes @/tmp/java-sources.txt; "
            f"javac --release {release} -cp /tmp/classes -d /tmp/example "
            f".readme-agent/{example.class_name}.java"
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
                    memory_mebibytes=1024,
                    pids_limit=96,
                ),
            )
        )
    verify_repository_snapshot(snapshot)
    proof = compiled_proof(
        snapshot=snapshot,
        ecosystem="java",
        source_paths=source_paths,
        selected_symbols=symbols,
        example_code=example.code,
        execution=execution,
    )
    result = diagnostic(execution)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="java",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "exact Java consumer compiled against immutable repository source"
            if proof.accepted
            else "isolated Java source or exact consumer compilation failed"
        ),
        build=result,
        example_compile=result,
        isolated_execution=execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.selected_symbols if proof.accepted else [],
        public_api_sha256=proof.source_sha256,
        acquisition_dependency_pins=dependency_pins(proof, f"java_release={release}"),
        compiled_consumer=proof,
    )
