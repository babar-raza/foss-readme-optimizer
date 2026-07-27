"""Acquire a locked Cargo dependency bundle in a disposable networked container."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock

from readme_agent.ecosystems.rust_api_schema import RustPackageLayoutV1
from readme_agent.evidence.redaction import redact
from readme_agent.facts.isolated_cleanup import remove_docker_resource
from readme_agent.facts.isolated_docker_control import (
    DockerCommandRunner,
    IsolatedExecutionError,
    inspect_container_image,
)
from readme_agent.facts.isolated_execution import LocalDockerCommandRunner
from readme_agent.facts.rust_dependency_schema import RustDependencyAcquisitionV1
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot
from readme_agent.retry import RetryableOperationError, run_with_retry

RUST_188_IMAGE = "rust@sha256:af306cfa71d987911a781c37b59d7d67d934f49684058f96cf72079c3626bfe0"
_ENVIRONMENT = {
    "CARGO_HOME": "/tmp/cargo",
    "CARGO_TERM_COLOR": "never",
    "HOME": "/tmp",
}
_COPY_IGNORE = shutil.ignore_patterns(".git", "target")


@dataclass(frozen=True)
class RustDependencyBundle:
    """Validated cache location plus its immutable acquisition record."""

    root: Path
    acquisition: RustDependencyAcquisitionV1


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _directory_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError("Cargo vendor bundle is empty")
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _cache_root() -> Path:
    return Path(__file__).resolve().parents[3] / "runs" / "tooling" / "rust-dependencies"


def _cache_key(
    snapshot: RepositorySnapshotV1,
    package: RustPackageLayoutV1,
    immutable_image: str,
) -> str:
    digest = hashlib.sha256()
    for value in (
        snapshot.org_repo,
        snapshot.source_revision,
        snapshot.inventory_sha256,
        package.source_sha256,
        immutable_image,
    ):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    for path in (Path(__file__), Path(__file__).with_name("rust_dependency_schema.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def rust_consumer_manifest(package: RustPackageLayoutV1) -> str:
    """Return the external path-consumer manifest used before and after vendoring."""

    package_path = Path("../package")
    if package.package_root != ".":
        package_path /= Path(package.package_root)
    dependency = json.dumps(package.package_name)
    path = json.dumps(package_path.as_posix())
    return (
        '[package]\nname = "readme-agent-rust-consumer"\nversion = "0.0.0"\n'
        f"edition = {json.dumps(package.edition)}\npublish = false\n\n"
        "[dependencies]\n"
        f"{package.crate_name} = {{ package = {dependency}, path = {path} }}\n"
    )


def _docker_argv(
    *,
    name: str,
    workspace: Path,
    image: str,
    cargo_argv: list[str],
) -> list[str]:
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
        "1024m",
        "--memory-swap",
        "1024m",
        "--pids-limit",
        "96",
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
        "/workspace/consumer",
    ]
    for key, value in sorted(_ENVIRONMENT.items()):
        argv.extend(["--env", f"{key}={value}"])
    return [*argv, "--entrypoint", "cargo", image, *cargo_argv]


def _run_cargo(
    runner: DockerCommandRunner,
    workspace: Path,
    image: str,
    cargo_argv: list[str],
) -> str:
    try:
        return run_with_retry(
            "package_registry",
            lambda: _run_cargo_attempt(runner, workspace, image, cargo_argv),
        )
    except RetryableOperationError as exc:
        raise IsolatedExecutionError(str(exc)) from exc


def _run_cargo_attempt(
    runner: DockerCommandRunner,
    workspace: Path,
    image: str,
    cargo_argv: list[str],
) -> str:
    name = f"readme-agent-rust-acquire-{uuid.uuid4().hex}"
    result: subprocess.CompletedProcess[str] | None = None
    try:
        result = runner.run(
            _docker_argv(
                name=name,
                workspace=workspace,
                image=image,
                cargo_argv=cargo_argv,
            ),
            timeout_seconds=600,
        )
    finally:
        removed = remove_docker_resource(runner, "container", name)
    if not removed:
        raise IsolatedExecutionError(
            f"networked Cargo acquisition resource cleanup could not be confirmed: {name}"
        )
    if result is None:
        raise IsolatedExecutionError("networked Cargo acquisition returned no process result")
    if result.returncode != 0:
        detail = redact(f"{result.stdout}\n{result.stderr}".strip())
        raise RetryableOperationError(
            f"networked Cargo acquisition failed ({' '.join(cargo_argv)}, "
            f"exit {result.returncode}): {detail}"
        )
    return result.stdout


def _load_bundle(path: Path) -> RustDependencyBundle:
    record_path = path / "acquisition.json"
    if not record_path.is_file():
        raise ValueError(f"Rust dependency cache has no acquisition record: {path}")
    acquisition = RustDependencyAcquisitionV1.model_validate_json(
        record_path.read_text(encoding="utf-8")
    )
    lockfile = path / "Cargo.lock"
    vendor = path / "vendor"
    config = path / "config.toml"
    if (
        not lockfile.is_file()
        or not config.is_file()
        or _sha256(lockfile) != acquisition.lockfile_sha256
        or _directory_sha256(vendor) != acquisition.vendor_sha256
        or _sha256(config) != acquisition.config_sha256
    ):
        raise ValueError(f"Rust dependency cache failed checksum validation: {path}")
    return RustDependencyBundle(root=path, acquisition=acquisition)


def acquire_rust_dependencies(
    snapshot: RepositorySnapshotV1,
    package: RustPackageLayoutV1,
    *,
    cache_root: Path | None = None,
    runner: DockerCommandRunner | None = None,
    immutable_image: str = RUST_188_IMAGE,
) -> RustDependencyBundle:
    """Resolve and vendor exact dependencies without running build scripts."""

    verify_repository_snapshot(snapshot)
    root = cache_root or _cache_root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / _cache_key(snapshot, package, immutable_image)
    with FileLock(str(root / ".acquisition.lock"), timeout=600):
        if target.exists():
            bundle = _load_bundle(target)
            if (
                bundle.acquisition.org_repo != snapshot.org_repo
                or bundle.acquisition.source_revision != snapshot.source_revision
                or bundle.acquisition.snapshot_inventory_sha256 != snapshot.inventory_sha256
                or bundle.acquisition.package_source_sha256 != package.source_sha256
                or bundle.acquisition.image.requested_reference != immutable_image
            ):
                raise ValueError("Rust dependency cache provenance does not match the snapshot")
            return bundle

        active_runner = runner or LocalDockerCommandRunner()
        image = inspect_container_image(active_runner, immutable_image)
        with tempfile.TemporaryDirectory(prefix=".pending-rust-", dir=root) as temp:
            workspace = Path(temp) / "workspace"
            package_copy = workspace / "package"
            consumer = workspace / "consumer"
            shutil.copytree(snapshot.root_path, package_copy, ignore=_COPY_IGNORE)
            consumer.mkdir(parents=True)
            (consumer / "Cargo.toml").write_text(
                rust_consumer_manifest(package),
                encoding="utf-8",
                newline="\n",
            )
            (consumer / "src").mkdir()
            (consumer / "src/main.rs").write_text("fn main() {}\n", encoding="utf-8")
            generate = ["generate-lockfile"]
            vendor = ["vendor", "--locked", "vendor"]
            _run_cargo(active_runner, workspace, immutable_image, generate)
            config_text = _run_cargo(active_runner, workspace, immutable_image, vendor)
            lockfile = consumer / "Cargo.lock"
            vendor_root = consumer / "vendor"
            if not lockfile.is_file() or not vendor_root.is_dir():
                raise IsolatedExecutionError(
                    "Cargo acquisition did not produce lock/vendor outputs"
                )
            if "[source." not in config_text:
                raise IsolatedExecutionError(
                    "Cargo vendor did not emit a source replacement config"
                )
            lock_package_count = lockfile.read_text(encoding="utf-8").count("[[package]]")
            if lock_package_count < 1:
                raise IsolatedExecutionError("Cargo lock contains no package records")
            publish = Path(temp) / "publish"
            publish.mkdir()
            shutil.copy2(lockfile, publish / "Cargo.lock")
            shutil.copytree(vendor_root, publish / "vendor")
            (publish / "config.toml").write_text(
                config_text,
                encoding="utf-8",
                newline="\n",
            )
            acquisition = RustDependencyAcquisitionV1(
                org_repo=snapshot.org_repo,
                source_revision=snapshot.source_revision,
                snapshot_inventory_sha256=snapshot.inventory_sha256,
                package_source_sha256=package.source_sha256,
                image=image,
                environment_names=sorted(_ENVIRONMENT),
                commands=[generate, vendor],
                lockfile_sha256=_sha256(publish / "Cargo.lock"),
                vendor_sha256=_directory_sha256(publish / "vendor"),
                config_sha256=_sha256(publish / "config.toml"),
                lock_package_count=lock_package_count,
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


def materialize_rust_dependencies(bundle: RustDependencyBundle, destination_root: Path) -> None:
    """Copy a checksum-validated lock/vendor bundle into a disposable workspace."""

    validated = _load_bundle(bundle.root)
    if validated.acquisition != bundle.acquisition:
        raise ValueError("Rust dependency bundle changed after acquisition")
    shutil.copy2(bundle.root / "Cargo.lock", destination_root / "Cargo.lock")
    shutil.copytree(bundle.root / "vendor", destination_root / "vendor")
    config_root = destination_root / ".cargo"
    config_root.mkdir()
    shutil.copy2(bundle.root / "config.toml", config_root / "config.toml")
