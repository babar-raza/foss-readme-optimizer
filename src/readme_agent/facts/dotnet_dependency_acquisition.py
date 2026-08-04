"""Acquire NuGet dependencies in a hardened container for later offline builds."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock

from readme_agent.evidence.redaction import redact
from readme_agent.facts.compiled_consumer import copy_snapshot
from readme_agent.facts.dotnet_dependency_schema import (
    NUGET_ORG_V3_SOURCE,
    DotnetDependencyAcquisitionV1,
    DotnetPackageArtifactV1,
    DotnetRepositoryArtifactV1,
    canonical_package_inventory_sha256,
)
from readme_agent.facts.dotnet_legacy_reference_fallback import (
    apply_repository_assembly_reference_fallback,
)
from readme_agent.facts.dotnet_lfs_acquisition import acquire_repository_lfs_dependencies
from readme_agent.facts.dotnet_project_closure import dotnet_project_export_paths
from readme_agent.facts.dotnet_source_generator_fallback import (
    apply_checked_in_generator_fallback,
)
from readme_agent.facts.isolated_cleanup import remove_docker_resource
from readme_agent.facts.isolated_docker_control import (
    DockerCommandRunner,
    IsolatedExecutionError,
    ensure_container_image,
)
from readme_agent.facts.isolated_execution import LocalDockerCommandRunner
from readme_agent.facts.root_role_schema import (
    filesystem_repository_path,
    portable_repository_path,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot
from readme_agent.retry import RetryableOperationError, run_with_retry

DOTNET_8_SDK_IMAGE = (
    "mcr.microsoft.com/dotnet/sdk@sha256:"
    "3c0edbfe1549dd93fb789dc96299a40df865ad7bffefcaf38e8c05940686d641"
)
_ENVIRONMENT = {
    "DOTNET_CLI_HOME": "/tmp/dotnet",
    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    "DOTNET_NOLOGO": "1",
    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
    "HOME": "/tmp",
    "NUGET_PACKAGES": "/workspace/packages",
    "TMPDIR": "/tmp",
}
_COPY_IGNORE = (
    "*.Tests",
    "*.TestFx",
    "Package",
    "TestData",
    "TestGold",
)
_IMMUTABLE_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
_TRANSIENT_RESTORE_MARKERS = (
    "connection",
    "name resolution",
    "nu1301",
    "registry outage",
    "temporarily",
    "temporary",
    "timed out",
    "timeout",
    "http 429",
    "http 502",
    "http 503",
    "http 504",
)
_CACHE_IMPLEMENTATION_FILES = (
    "compiled_consumer.py",
    "dotnet_dependency_acquisition.py",
    "dotnet_dependency_schema.py",
    "dotnet_legacy_reference_fallback.py",
    "dotnet_lfs_acquisition.py",
    "dotnet_project_closure.py",
    "dotnet_source_generator_fallback.py",
    "isolated_docker_control.py",
)


@dataclass(frozen=True)
class DotnetDependencyBundle:
    """Checksum-validated package cache plus immutable acquisition receipt."""

    root: Path
    acquisition: DotnetDependencyAcquisitionV1


def _remove_workspace(path: Path) -> None:
    failure: OSError | None = None
    for _attempt in range(3):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            failure = exc
            time.sleep(0.1)
    if os.name == "nt":
        try:
            shutil.rmtree(Path("\\\\?\\" + str(path.resolve())))
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            failure = exc
    raise IsolatedExecutionError(f"NuGet acquisition workspace cleanup failed: {failure}")


@contextmanager
def _disposable_workspace() -> Iterator[Path]:
    path = Path(tempfile.mkdtemp(prefix="ra-nuget-"))
    try:
        yield path
    finally:
        _remove_workspace(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _directory_identity(root: Path) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    count = 0
    size = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"NuGet dependency cache contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
        count += 1
        size += len(content)
    if count == 0:
        raise ValueError(f"NuGet package directory is empty: {root}")
    return digest.hexdigest(), count, size


def _artifacts(packages: Path) -> list[DotnetPackageArtifactV1]:
    if not packages.is_dir():
        raise ValueError("NuGet dependency cache has no packages directory")
    if any(path.is_file() or path.is_symlink() for path in packages.iterdir()):
        raise ValueError("NuGet package cache has an invalid top-level entry")
    artifacts: list[DotnetPackageArtifactV1] = []
    for package_root in sorted(path for path in packages.iterdir() if path.is_dir()):
        entries = list(package_root.iterdir())
        if not entries or any(path.is_file() or path.is_symlink() for path in entries):
            raise ValueError(f"NuGet package directory has an invalid entry: {package_root}")
        for version_root in sorted(path for path in entries if path.is_dir()):
            digest, count, size = _directory_identity(version_root)
            relative = version_root.relative_to(packages).as_posix()
            artifacts.append(
                DotnetPackageArtifactV1(
                    package_id=package_root.name,
                    version=version_root.name,
                    relative_path=relative,
                    sha256=digest,
                    file_count=count,
                    size_bytes=size,
                )
            )
    return sorted(artifacts, key=lambda item: item.relative_path.casefold())


def _cache_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
        return base / "readme-agent" / "dotnet"
    return Path(__file__).resolve().parents[3] / "runs" / "tooling" / "dotnet-dependencies"


def _discard_corrupt_cache(target: Path, root: Path, cache_key: str) -> None:
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    if resolved_target.parent != resolved_root or resolved_target.name != cache_key[:24]:
        raise ValueError("refusing to remove an unexpected dependency-cache path")
    _remove_workspace(resolved_target)


def _cache_key(
    snapshot: RepositorySnapshotV1,
    manifest_path: str,
    manifest_sha256: str,
    target_framework: str,
    immutable_image: str,
    *,
    implementation_files: tuple[Path, ...] | None = None,
) -> str:
    digest = hashlib.sha256()
    for value in (
        snapshot.org_repo,
        snapshot.source_revision,
        snapshot.inventory_sha256,
        manifest_path,
        manifest_sha256,
        target_framework,
        immutable_image,
        NUGET_ORG_V3_SOURCE,
    ):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    bound_files = implementation_files or tuple(
        Path(__file__).with_name(name) for name in _CACHE_IMPLEMENTATION_FILES
    )
    for path in bound_files:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _nuget_config(workspace: Path) -> None:
    (workspace / "NuGet.Config").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<configuration><packageSources><clear />"
        f'<add key="nuget.org" value="{NUGET_ORG_V3_SOURCE}" protocolVersion="3" />'
        "</packageSources></configuration>\n",
        encoding="utf-8",
        newline="\n",
    )


def _docker_argv(
    name: str,
    workspace: Path,
    image: str,
    manifest_path: str,
    target_framework: str,
) -> list[str]:
    command = [
        "restore",
        manifest_path,
        "--configfile",
        "/workspace/NuGet.Config",
        "--source",
        NUGET_ORG_V3_SOURCE,
        "--packages",
        "/workspace/packages",
        "--disable-parallel",
        "--no-cache",
        "--force-evaluate",
        f"-p:TargetFramework={target_framework}",
        f"-p:TargetFrameworks={target_framework}",
        "-p:Configuration=Debug",
        "--verbosity",
        "minimal",
    ]
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
        "1536m",
        "--memory-swap",
        "1536m",
        "--pids-limit",
        "128",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=512m",
        "--user",
        "65534:65534",
        "--volume",
        f"{workspace.resolve()}:/workspace",
        "--workdir",
        "/workspace/repository",
    ]
    for key, value in sorted(_ENVIRONMENT.items()):
        argv.extend(["--env", f"{key}={value}"])
    return [*argv, "--entrypoint", "dotnet", image, *command]


def _run_restore(
    runner: DockerCommandRunner,
    workspace: Path,
    image: str,
    manifest_path: str,
    target_framework: str,
) -> list[str]:
    name = f"readme-agent-dotnet-acquire-{uuid.uuid4().hex}"
    argv = _docker_argv(name, workspace, image, manifest_path, target_framework)
    result: subprocess.CompletedProcess[str] | None = None
    try:
        result = runner.run(argv, timeout_seconds=600)
    finally:
        removed = remove_docker_resource(runner, "container", name)
    if not removed:
        raise IsolatedExecutionError(
            f"networked NuGet acquisition cleanup could not be confirmed: {name}"
        )
    if result is None:
        raise IsolatedExecutionError("networked NuGet acquisition returned no result")
    if result.returncode != 0:
        detail = redact(f"{result.stdout}\n{result.stderr}".strip())
        message = f"networked NuGet acquisition failed (exit {result.returncode}): {detail}"
        if result.returncode == 124 or any(
            marker in detail.casefold() for marker in _TRANSIENT_RESTORE_MARKERS
        ):
            raise RetryableOperationError(message)
        raise IsolatedExecutionError(message)
    return argv[argv.index(image) + 1 :]


def _load_bundle(path: Path) -> DotnetDependencyBundle:
    record_path = path / "acquisition.json"
    if not record_path.is_file():
        raise ValueError(f"NuGet dependency cache has no acquisition record: {path}")
    acquisition = DotnetDependencyAcquisitionV1.model_validate_json(
        record_path.read_text(encoding="utf-8")
    )
    artifacts = _artifacts(path / "packages")
    if (
        artifacts != acquisition.artifacts
        or canonical_package_inventory_sha256(artifacts) != acquisition.inventory_sha256
    ):
        raise ValueError(f"NuGet dependency cache failed checksum validation: {path}")
    repository_artifacts = path / "repository-artifacts"
    for artifact in acquisition.repository_artifacts:
        candidate = repository_artifacts / artifact.relative_path
        if (
            not candidate.is_file()
            or candidate.stat().st_size != artifact.size_bytes
            or _sha256(candidate) != artifact.sha256
        ):
            raise ValueError(f"repository dependency cache failed checksum validation: {path}")
    return DotnetDependencyBundle(root=path, acquisition=acquisition)


def acquire_dotnet_dependencies(
    snapshot: RepositorySnapshotV1,
    selected_manifest_path: str,
    *,
    cache_root: Path | None = None,
    runner: DockerCommandRunner | None = None,
    immutable_image: str = DOTNET_8_SDK_IMAGE,
    target_framework: str = "net8.0",
    retry_sleep: Callable[[float], None] | None = None,
) -> DotnetDependencyBundle:
    """Restore exact NuGet dependencies in a bounded networked container."""

    verify_repository_snapshot(snapshot)
    if not _IMMUTABLE_IMAGE_RE.fullmatch(immutable_image):
        raise ValueError(".NET SDK image must be pinned as repository@sha256:<64 hex>")
    if target_framework not in {"net8.0", "net9.0"}:
        raise ValueError(".NET dependency target must be pinned to net8.0 or net9.0")
    manifest_path = portable_repository_path(selected_manifest_path)
    if Path(selected_manifest_path).is_absolute() or ".." in Path(manifest_path).parts:
        raise ValueError("selected .NET manifest path must stay inside the snapshot")
    manifest = snapshot.root_path / filesystem_repository_path(manifest_path)
    if not manifest.is_file() or manifest.suffix.casefold() != ".csproj":
        raise ValueError("selected .NET manifest is unavailable or not a .csproj")
    manifest_sha256 = _sha256(manifest)
    cache_key = _cache_key(
        snapshot,
        manifest_path,
        manifest_sha256,
        target_framework,
        immutable_image,
    )
    root = cache_root or _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / cache_key[:24]
    with FileLock(str(root / f"{cache_key}.lock"), timeout=600):
        if target.exists():
            try:
                bundle = _load_bundle(target)
                record = bundle.acquisition
                if (
                    record.org_repo != snapshot.org_repo
                    or record.source_revision != snapshot.source_revision
                    or record.snapshot_inventory_sha256 != snapshot.inventory_sha256
                    or record.selected_manifest_path != manifest_path
                    or record.manifest_sha256 != manifest_sha256
                    or record.target_framework != target_framework
                    or record.cache_key != cache_key
                    or record.image.requested_reference != immutable_image
                ):
                    raise ValueError(
                        "NuGet dependency cache provenance does not match the snapshot"
                    )
                return bundle
            except ValueError:
                _discard_corrupt_cache(target, root, cache_key)
        active_runner = runner or LocalDockerCommandRunner()
        image = ensure_container_image(active_runner, immutable_image)
        with _disposable_workspace() as pending:

            def attempt() -> tuple[
                list[str], Path, tuple[str, ...], list[DotnetRepositoryArtifactV1]
            ]:
                workspace = pending / f"a-{uuid.uuid4().hex[:8]}"
                export_paths = dotnet_project_export_paths(snapshot.root_path, manifest)
                copy_snapshot(
                    snapshot,
                    workspace / "repository",
                    ignored_names=_COPY_IGNORE,
                    included_paths=export_paths,
                )
                repository_workspace = workspace / "repository"
                repository_artifacts = acquire_repository_lfs_dependencies(
                    repository_workspace,
                    org_repo=snapshot.org_repo,
                    source_revision=snapshot.source_revision,
                    runner=active_runner,
                    immutable_image=immutable_image,
                    retry_sleep=retry_sleep,
                )
                transformations = (
                    *apply_checked_in_generator_fallback(repository_workspace),
                    *apply_repository_assembly_reference_fallback(repository_workspace),
                )
                (workspace / "packages").mkdir(parents=True)
                _nuget_config(workspace)
                command = _run_restore(
                    active_runner,
                    workspace,
                    immutable_image,
                    manifest_path,
                    target_framework,
                )
                return command, workspace, transformations, repository_artifacts

            try:
                command, workspace, transformations, repository_artifacts = run_with_retry(
                    "package_registry", attempt, sleep=retry_sleep
                )
            except RetryableOperationError as exc:
                raise IsolatedExecutionError(str(exc)) from exc
            artifacts = _artifacts(workspace / "packages")
            with tempfile.TemporaryDirectory(prefix=".p-", dir=root) as stage:
                publish = Path(stage) / "publish"
                publish.mkdir()
                shutil.copytree(workspace / "packages", publish / "packages")
                for artifact in repository_artifacts:
                    source = workspace / "repository" / artifact.relative_path
                    destination = publish / "repository-artifacts" / artifact.relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                acquisition = DotnetDependencyAcquisitionV1(
                    org_repo=snapshot.org_repo,
                    source_revision=snapshot.source_revision,
                    snapshot_inventory_sha256=snapshot.inventory_sha256,
                    selected_manifest_path=manifest_path,
                    manifest_sha256=manifest_sha256,
                    target_framework=target_framework,
                    cache_key=cache_key,
                    image=image,
                    environment_names=sorted(_ENVIRONMENT),
                    command=command,
                    project_transformations=list(transformations),
                    repository_artifacts=repository_artifacts,
                    artifacts=artifacts,
                    inventory_sha256=canonical_package_inventory_sha256(artifacts),
                    acquired_at=datetime.now(UTC).isoformat(),
                    cleanup_complete=True,
                )
                (publish / "acquisition.json").write_text(
                    acquisition.model_dump_json(indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                publish.replace(target)
    verify_repository_snapshot(snapshot)
    return _load_bundle(target)


def materialize_dotnet_dependencies(
    bundle: DotnetDependencyBundle,
    destination: Path,
    *,
    repository_destination: Path | None = None,
) -> None:
    """Copy a checksum-validated global-packages cache into an offline workspace."""

    validated = _load_bundle(bundle.root)
    if validated.acquisition != bundle.acquisition:
        raise ValueError("NuGet dependency bundle changed after acquisition")
    shutil.copytree(bundle.root / "packages", destination)
    if validated.acquisition.repository_artifacts:
        if repository_destination is None:
            raise ValueError("repository destination is required for repository dependencies")
        for artifact in validated.acquisition.repository_artifacts:
            source = bundle.root / "repository-artifacts" / artifact.relative_path
            target = repository_destination / artifact.relative_path
            if not target.is_file():
                raise ValueError(
                    f"repository dependency target is unavailable: {artifact.relative_path}"
                )
            shutil.copyfile(source, target)
