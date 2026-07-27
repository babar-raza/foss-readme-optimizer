"""Shared preparation and provenance helpers for isolated compiled consumers."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Literal

from readme_agent.facts.compiled_consumer_schema import CompiledConsumerProofV1
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.repository_snapshot import RepositorySnapshotV1

_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "artifacts",
    "bin",
    "build",
    "dist",
    "node_modules",
    "obj",
    "target",
)


def copy_snapshot(snapshot: RepositorySnapshotV1, destination: Path) -> None:
    """Copy only immutable source inputs into a disposable executor workspace."""

    shutil.copytree(snapshot.root_path, destination, ignore=_COPY_IGNORE)


def source_paths_sha256(root: Path, relative_paths: list[str]) -> str:
    """Hash exact source paths and bytes in stable order."""

    digest = hashlib.sha256()
    for relative in sorted(set(relative_paths)):
        path = root / relative
        if not path.is_file():
            raise ValueError(f"compiled consumer source path does not exist: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def diagnostic(result: IsolatedExecutionResultV1) -> ExampleExecutionResultV1:
    """Project the isolated result into the compatibility diagnostic contract."""

    return ExampleExecutionResultV1(
        argv=result.argv,
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=result.timed_out,
        environment_names=result.environment_names,
        isolation_kind="isolated_result_projection",
    )


def compiled_proof(
    *,
    snapshot: RepositorySnapshotV1,
    ecosystem: Literal["java", "dotnet", "cpp", "go"],
    source_paths: list[str],
    selected_symbols: list[str],
    example_code: str,
    execution: IsolatedExecutionResultV1,
) -> CompiledConsumerProofV1:
    """Create one compiler proof from deterministic source and example hashes."""

    return CompiledConsumerProofV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem=ecosystem,
        source_paths=sorted(set(source_paths)),
        selected_symbols=sorted(set(selected_symbols)),
        source_sha256=source_paths_sha256(snapshot.root_path, source_paths),
        example_sha256=hashlib.sha256(example_code.encode("utf-8")).hexdigest(),
        isolated_execution=execution,
        accepted=execution.truth_eligible and execution.return_code == 0,
    )


def dependency_pins(
    proof: CompiledConsumerProofV1,
    *extras: str,
) -> list[str]:
    """Bind proof to the exact image, input tree, source surface, and example."""

    execution = proof.isolated_execution
    return [
        f"container_image={execution.policy.immutable_image}",
        f"example_sha256={proof.example_sha256}",
        f"input_sha256={execution.input_sha256}",
        f"source_revision={proof.source_revision}",
        f"source_surface_sha256={proof.source_sha256}",
        *extras,
    ]
