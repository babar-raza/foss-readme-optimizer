"""Acquire binary Python dependencies for later offline consumer proof."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import tomllib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1
from readme_agent.evidence.redaction import redact
from readme_agent.facts.isolated_cleanup import remove_docker_resource
from readme_agent.facts.isolated_docker_control import (
    DockerCommandRunner,
    IsolatedExecutionError,
    inspect_container_image,
)
from readme_agent.facts.isolated_execution import LocalDockerCommandRunner
from readme_agent.facts.python_dependency_schema import (
    PythonDependencyAcquisitionV1,
    PythonWheelArtifactV1,
)
from readme_agent.facts.python_toolchain import PYTHON_311_IMAGE
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot
from readme_agent.retry import RetryableOperationError, run_with_retry

_ENVIRONMENT = {"HOME": "/tmp", "PIP_CACHE_DIR": "/tmp/pip-cache"}


@dataclass(frozen=True)
class PythonDependencyBundle:
    """Checksum-validated cache location and immutable acquisition record."""

    root: Path
    acquisition: PythonDependencyAcquisitionV1


def declared_python_runtime_dependencies(root: Path, manifest_path: str) -> list[str]:
    """Read literal PEP 621 runtime requirements without executing repository code."""

    manifest = root / manifest_path
    if manifest.name != "pyproject.toml" or not manifest.is_file():
        return []
    data = tomllib.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
    dependencies = data.get("project", {}).get("dependencies", [])
    if not isinstance(dependencies, list) or any(
        not isinstance(item, str) for item in dependencies
    ):
        raise ValueError("project.dependencies must be a literal string list")
    return sorted(dict.fromkeys(item.strip() for item in dependencies if item.strip()))


def declared_python_build_dependencies(root: Path, manifest_path: str) -> list[str]:
    """Read literal PEP 517 build requirements without executing repository code."""

    manifest = root / manifest_path
    if manifest.name != "pyproject.toml" or not manifest.is_file():
        return []
    data = tomllib.loads(manifest.read_text(encoding="utf-8-sig", errors="replace"))
    requirements = data.get("build-system", {}).get("requires", [])
    if not isinstance(requirements, list) or any(
        not isinstance(item, str) for item in requirements
    ):
        raise ValueError("build-system.requires must be a literal string list")
    return sorted(dict.fromkeys(item.strip() for item in requirements if item.strip()))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifacts(root: Path) -> list[PythonWheelArtifactV1]:
    files = sorted(path for path in root.iterdir() if path.is_file()) if root.is_dir() else []
    if any(path.suffix != ".whl" for path in files):
        raise ValueError("Python dependency cache contains a non-wheel artifact")
    return [
        PythonWheelArtifactV1(
            filename=path.name,
            sha256=_sha256(path),
            size_bytes=path.stat().st_size,
        )
        for path in files
    ]


def _inventory_sha256(artifacts: list[PythonWheelArtifactV1]) -> str:
    payload = json.dumps(
        [artifact.model_dump(mode="json") for artifact in artifacts],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_root() -> Path:
    return Path(__file__).resolve().parents[3] / "runs" / "tooling" / "python-dependencies"


def _cache_key(
    snapshot: RepositorySnapshotV1,
    package: PythonPackageLayoutV1,
    requirements: list[str],
    image: str,
) -> str:
    digest = hashlib.sha256()
    for value in (
        snapshot.org_repo,
        snapshot.source_revision,
        snapshot.inventory_sha256,
        package.source_sha256,
        image,
        *requirements,
    ):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    for path in (Path(__file__), Path(__file__).with_name("python_dependency_schema.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _docker_argv(name: str, workspace: Path, image: str, requirements: list[str]) -> list[str]:
    command = [
        "-m",
        "pip",
        "download",
        "--disable-pip-version-check",
        "--only-binary=:all:",
        "--dest",
        "/workspace/wheelhouse",
        *requirements,
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
        "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "--user",
        "65534:65534",
        "--volume",
        f"{workspace.resolve()}:/workspace",
        "--workdir",
        "/workspace",
    ]
    for key, value in sorted(_ENVIRONMENT.items()):
        argv.extend(["--env", f"{key}={value}"])
    return [*argv, "--entrypoint", "python", image, *command]


def _run_acquisition(
    runner: DockerCommandRunner,
    workspace: Path,
    image: str,
    requirements: list[str],
) -> list[str]:
    name = f"readme-agent-python-acquire-{uuid.uuid4().hex}"
    argv = _docker_argv(name, workspace, image, requirements)
    result: subprocess.CompletedProcess[str] | None = None
    try:
        result = runner.run(argv, timeout_seconds=600)
    finally:
        removed = remove_docker_resource(runner, "container", name)
    if not removed:
        raise IsolatedExecutionError(
            f"networked Python acquisition cleanup could not be confirmed: {name}"
        )
    if result is None:
        raise IsolatedExecutionError("networked Python acquisition returned no process result")
    if result.returncode != 0:
        detail = redact(f"{result.stdout}\n{result.stderr}".strip())
        raise RetryableOperationError(
            f"networked binary-wheel acquisition failed (exit {result.returncode}): {detail}"
        )
    return argv[argv.index(image) + 1 :]


def _load_bundle(path: Path) -> PythonDependencyBundle:
    record_path = path / "acquisition.json"
    if not record_path.is_file():
        raise ValueError(f"Python dependency cache has no acquisition record: {path}")
    acquisition = PythonDependencyAcquisitionV1.model_validate_json(
        record_path.read_text(encoding="utf-8")
    )
    artifacts = _artifacts(path / "wheelhouse")
    if (
        artifacts != acquisition.artifacts
        or _inventory_sha256(artifacts) != acquisition.inventory_sha256
    ):
        raise ValueError(f"Python dependency cache failed checksum validation: {path}")
    return PythonDependencyBundle(root=path, acquisition=acquisition)


def acquire_python_dependencies(
    snapshot: RepositorySnapshotV1,
    package: PythonPackageLayoutV1,
    *,
    cache_root: Path | None = None,
    runner: DockerCommandRunner | None = None,
    immutable_image: str = PYTHON_311_IMAGE,
) -> PythonDependencyBundle | None:
    """Resolve binary wheels in a bounded networked container for offline use."""

    verify_repository_snapshot(snapshot)
    requirements = sorted(
        set(
            declared_python_runtime_dependencies(snapshot.root_path, package.manifest_path)
            + declared_python_build_dependencies(snapshot.root_path, package.manifest_path)
        )
    )
    if not requirements:
        return None
    root = cache_root or _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / _cache_key(snapshot, package, requirements, immutable_image)
    with FileLock(str(root / ".acquisition.lock"), timeout=600):
        if target.exists():
            bundle = _load_bundle(target)
            record = bundle.acquisition
            if (
                record.org_repo != snapshot.org_repo
                or record.source_revision != snapshot.source_revision
                or record.snapshot_inventory_sha256 != snapshot.inventory_sha256
                or record.package_source_sha256 != package.source_sha256
                or record.requirements != requirements
                or record.image.requested_reference != immutable_image
            ):
                raise ValueError("Python dependency cache provenance does not match the snapshot")
            return bundle
        active_runner = runner or LocalDockerCommandRunner()
        image = inspect_container_image(active_runner, immutable_image)
        with tempfile.TemporaryDirectory(prefix=".pending-python-", dir=root) as temp:
            workspace = Path(temp) / "workspace"
            wheelhouse = workspace / "wheelhouse"
            wheelhouse.mkdir(parents=True)
            try:
                command = run_with_retry(
                    "package_registry",
                    lambda: _run_acquisition(
                        active_runner, workspace, immutable_image, requirements
                    ),
                )
            except RetryableOperationError as exc:
                raise IsolatedExecutionError(str(exc)) from exc
            artifacts = _artifacts(wheelhouse)
            if not artifacts:
                raise IsolatedExecutionError("binary-wheel acquisition produced no artifacts")
            publish = Path(temp) / "publish"
            publish.mkdir()
            shutil.copytree(wheelhouse, publish / "wheelhouse")
            acquisition = PythonDependencyAcquisitionV1(
                org_repo=snapshot.org_repo,
                source_revision=snapshot.source_revision,
                snapshot_inventory_sha256=snapshot.inventory_sha256,
                package_source_sha256=package.source_sha256,
                image=image,
                environment_names=sorted(_ENVIRONMENT),
                requirements=requirements,
                command=command,
                artifacts=artifacts,
                inventory_sha256=_inventory_sha256(artifacts),
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


def materialize_python_dependencies(bundle: PythonDependencyBundle, destination: Path) -> None:
    """Copy a checksum-validated wheelhouse into a disposable workspace."""

    validated = _load_bundle(bundle.root)
    if validated.acquisition != bundle.acquisition:
        raise ValueError("Python dependency bundle changed after acquisition")
    shutil.copytree(bundle.root / "wheelhouse", destination)
