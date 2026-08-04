"""Acquire exact public Git LFS inputs in a hardened disposable container."""

from __future__ import annotations

import hashlib
import re
import shlex
import shutil
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

from readme_agent.evidence.redaction import redact
from readme_agent.facts.dotnet_dependency_schema import DotnetRepositoryArtifactV1
from readme_agent.facts.isolated_cleanup import remove_docker_resource
from readme_agent.facts.isolated_docker_control import DockerCommandRunner, IsolatedExecutionError
from readme_agent.retry import RetryableOperationError, run_with_retry

_LFS_POINTER_RE = re.compile(
    r"\Aversion https://git-lfs\.github\.com/spec/v1\n"
    r"oid sha256:([0-9a-f]{64})\nsize ([1-9][0-9]*)\n?\Z"
)
_TRANSIENT_MARKERS = (
    "connection",
    "name resolution",
    "timed out",
    "timeout",
    "http 429",
    "http 502",
    "http 503",
    "http 504",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pointers(repository: Path, org_repo: str, revision: str) -> list[DotnetRepositoryArtifactV1]:
    artifacts: list[DotnetRepositoryArtifactV1] = []
    for path in sorted(item for item in repository.rglob("*") if item.is_file()):
        if path.stat().st_size > 256:
            continue
        try:
            match = _LFS_POINTER_RE.fullmatch(path.read_text(encoding="ascii"))
        except (OSError, UnicodeDecodeError):
            continue
        if match is None:
            continue
        relative = path.relative_to(repository).as_posix()
        url = (
            "https://media.githubusercontent.com/media/"
            + quote(org_repo, safe="/")
            + "/"
            + quote(revision, safe="")
            + "/"
            + quote(relative, safe="/")
        )
        artifacts.append(
            DotnetRepositoryArtifactV1(
                relative_path=relative,
                source_url=url,
                sha256=match.group(1),
                size_bytes=int(match.group(2)),
            )
        )
    return artifacts


def _download_once(
    runner: DockerCommandRunner,
    workspace: Path,
    image: str,
    artifacts: list[DotnetRepositoryArtifactV1],
) -> None:
    downloads = workspace / "lfs"
    downloads.mkdir()
    downloads.chmod(0o777)
    commands: list[str] = []
    for index, artifact in enumerate(artifacts):
        destination = f"/workspace/lfs/{index}"
        commands.extend(
            [
                "curl --fail --silent --show-error --location --max-time 120 "
                + f"--output {shlex.quote(destination)} {shlex.quote(artifact.source_url)}",
                f"printf '%s  %s\\n' {shlex.quote(artifact.sha256)} "
                + f"{shlex.quote(destination)} | sha256sum --check --status",
                f'test "$(wc -c < {shlex.quote(destination)})" -eq {artifact.size_bytes}',
            ]
        )
    name = f"readme-agent-dotnet-lfs-{uuid.uuid4().hex}"
    argv = [
        "run",
        "--rm",
        "--name",
        name,
        "--label",
        "readme-agent=true",
        "--network",
        "bridge",
        "--read-only",
        "--cpus",
        "1.0",
        "--memory",
        "512m",
        "--memory-swap",
        "512m",
        "--pids-limit",
        "64",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=64m",
        "--user",
        "65534:65534",
        "--volume",
        f"{workspace.resolve()}:/workspace",
        "--entrypoint",
        "/bin/sh",
        image,
        "-euc",
        "; ".join(commands),
    ]
    result: subprocess.CompletedProcess[str] | None = None
    try:
        result = runner.run(argv, timeout_seconds=max(180, len(artifacts) * 120))
    finally:
        removed = remove_docker_resource(runner, "container", name)
    if not removed:
        raise IsolatedExecutionError(f"Git LFS acquisition cleanup could not be confirmed: {name}")
    if result is None:
        raise IsolatedExecutionError("Git LFS acquisition returned no result")
    if result.returncode != 0:
        detail = redact(f"{result.stdout}\n{result.stderr}".strip())
        message = f"Git LFS acquisition failed (exit {result.returncode}): {detail}"
        if result.returncode == 124 or any(
            marker in detail.casefold() for marker in _TRANSIENT_MARKERS
        ):
            raise RetryableOperationError(message)
        raise IsolatedExecutionError(message)


def acquire_repository_lfs_dependencies(
    repository: Path,
    *,
    org_repo: str,
    source_revision: str,
    runner: DockerCommandRunner,
    immutable_image: str,
    retry_sleep: Callable[[float], None] | None = None,
) -> list[DotnetRepositoryArtifactV1]:
    """Hydrate exact LFS pointers without credentials and verify their immutable identities."""

    artifacts = _pointers(repository, org_repo, source_revision)
    if not artifacts:
        return []

    def attempt() -> None:
        downloads = repository.parent / "lfs"
        if downloads.exists():
            shutil.rmtree(downloads)
        _download_once(runner, repository.parent, immutable_image, artifacts)

    try:
        run_with_retry("github_read", attempt, sleep=retry_sleep)
    except RetryableOperationError as exc:
        raise IsolatedExecutionError(str(exc)) from exc
    downloads = repository.parent / "lfs"
    for index, artifact in enumerate(artifacts):
        source = downloads / str(index)
        if source.stat().st_size != artifact.size_bytes or _sha256(source) != artifact.sha256:
            raise ValueError("Git LFS dependency failed post-download identity validation")
        destination = repository / artifact.relative_path
        shutil.copyfile(source, destination)
    return artifacts
