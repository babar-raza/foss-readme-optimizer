"""Shared preparation and provenance helpers for isolated compiled consumers."""

from __future__ import annotations

import fnmatch
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Literal

from readme_agent.facts.compiled_consumer_schema import CompiledConsumerProofV1
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1
from readme_agent.repository_snapshot import RepositorySnapshotV1

_COPY_IGNORE_NAMES = (
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


def copy_snapshot(
    snapshot: RepositorySnapshotV1,
    destination: Path,
    *,
    ignored_names: tuple[str, ...] = (),
    included_paths: tuple[str, ...] = (),
) -> None:
    """Copy only immutable source inputs into a disposable executor workspace."""

    if (snapshot.root_path / ".git").is_dir():
        _copy_git_archive(
            snapshot,
            destination,
            ignored_names=ignored_names,
            included_paths=included_paths,
        )
        return
    if included_paths:
        destination.mkdir(parents=True)
        for relative in included_paths:
            portable = PurePosixPath(relative)
            if portable.is_absolute() or ".." in portable.parts:
                raise ValueError(f"immutable snapshot export path escapes the root: {relative}")
            source = snapshot.root_path / relative
            target = destination / relative
            if source.is_dir():
                shutil.copytree(
                    source,
                    target,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*ignored_names),
                )
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            else:
                raise ValueError(f"immutable snapshot export path is unavailable: {relative}")
        return
    shutil.copytree(
        snapshot.root_path,
        destination,
        ignore=shutil.ignore_patterns(*_COPY_IGNORE_NAMES, *ignored_names),
    )


def _copy_git_archive(
    snapshot: RepositorySnapshotV1,
    destination: Path,
    *,
    ignored_names: tuple[str, ...],
    included_paths: tuple[str, ...],
) -> None:
    """Export tracked immutable bytes without relying on hydrated checkout files."""

    patterns = tuple(ignored_names if included_paths else (*_COPY_IGNORE_NAMES, *ignored_names))
    with tempfile.TemporaryDirectory(prefix="readme-agent-git-export-") as temp:
        archive = Path(temp) / "snapshot.tar"
        argv = [
            "git",
            "-c",
            "filter.lfs.process=",
            "-c",
            "filter.lfs.required=false",
            "-C",
            str(snapshot.root_path),
            "archive",
            "--format=tar",
            f"--output={archive}",
            snapshot.source_revision,
        ]
        if included_paths:
            argv.extend(["--", *included_paths])
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise ValueError(f"immutable Git snapshot export failed: {result.stderr.strip()}")
        destination.mkdir(parents=True)
        with tarfile.open(archive, mode="r:") as source:
            for member in source:
                relative = PurePosixPath(member.name)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or any(
                        fnmatch.fnmatch(part.casefold(), pattern.casefold())
                        for part in relative.parts
                        for pattern in patterns
                    )
                ):
                    continue
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise ValueError(
                        f"immutable Git snapshot contains unsupported entry: {member.name}"
                    )
                payload = source.extractfile(member)
                if payload is None:
                    raise ValueError(f"immutable Git snapshot entry is unreadable: {member.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with payload, target.open("wb") as output:
                    shutil.copyfileobj(payload, output)
                target.chmod(member.mode & 0o777)


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
