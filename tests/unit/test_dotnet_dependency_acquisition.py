"""NuGet dependencies are acquired once and consumed from a validated cache."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from readme_agent.facts import dotnet_dependency_acquisition
from readme_agent.facts.dotnet_dependency_acquisition import (
    DOTNET_8_SDK_IMAGE,
    acquire_dotnet_dependencies,
    materialize_dotnet_dependencies,
)
from readme_agent.facts.dotnet_dependency_schema import NUGET_ORG_V3_SOURCE
from readme_agent.facts.isolated_docker_control import IsolatedExecutionError
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _completed(
    argv: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class AcquisitionRunner:
    """Fake Docker boundary that materializes the package cache it reports."""

    def __init__(
        self,
        *,
        transient_failures: int = 0,
        cleanup_fails: bool = False,
        permanent_failure: bool = False,
    ) -> None:
        self.commands: list[list[str]] = []
        self.transient_failures = transient_failures
        self.cleanup_fails = cleanup_fails
        self.permanent_failure = permanent_failure

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(argv)
        if argv[:2] == ["image", "inspect"]:
            return _completed(
                argv,
                stdout=json.dumps(
                    [
                        {
                            "RepoDigests": [DOTNET_8_SDK_IMAGE],
                            "Id": "sha256:" + "b" * 64,
                            "Os": "linux",
                            "Architecture": "amd64",
                        }
                    ]
                ),
            )
        if argv[:2] == ["version", "--format"]:
            return _completed(argv, stdout="28.4.0\n")
        if argv[0] == "run":
            if self.permanent_failure:
                return _completed(argv, returncode=1, stderr="MSBuild project is invalid")
            if self.transient_failures:
                self.transient_failures -= 1
                return _completed(argv, returncode=1, stderr="temporary registry outage")
            mounted = argv[argv.index("--volume") + 1]
            workspace = Path(mounted.removesuffix(":/workspace"))
            package = workspace / "packages" / "newtonsoft.json" / "13.0.3"
            package.mkdir(parents=True)
            (package / "newtonsoft.json.13.0.3.nupkg.sha512").write_text(
                "fixture-package-hash\n", encoding="utf-8"
            )
            (package / "lib" / "net6.0").mkdir(parents=True)
            (package / "lib" / "net6.0" / "Newtonsoft.Json.dll").write_bytes(b"fixture assembly")
            return _completed(argv, stdout="Restore completed\n")
        if argv[:2] == ["rm", "--force"]:
            return _completed(argv, returncode=1 if self.cleanup_fails else 0)
        if argv[:2] == ["container", "inspect"]:
            if self.cleanup_fails:
                return _completed(argv, stdout='[{"State":{"Running":false}}]')
            return _completed(argv, returncode=1, stderr="No such container")
        if argv[:2] == ["ps", "-aq"]:
            return _completed(argv, stdout="still-present\n" if self.cleanup_fails else "")
        raise AssertionError(f"unexpected Docker command: {argv}")


def _source(root: Path) -> None:
    (root / "src" / "Product").mkdir(parents=True)
    (root / "src" / "Product" / "Product.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        "  <PropertyGroup><TargetFramework>net8.0</TargetFramework></PropertyGroup>\n"
        '  <ItemGroup><PackageReference Include="Newtonsoft.Json" Version="13.0.3" />'
        "</ItemGroup>\n</Project>\n",
        encoding="utf-8",
    )
    (root / "src" / "Product" / "Document.cs").write_text(
        "namespace Aspose.Widget; public class Document {}\n", encoding="utf-8"
    )


def _snapshot(root: Path) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="fixture/Aspose.Widget-FOSS-for-.NET",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        inventory_sha256="0" * 64,
        captured_at="2026-08-04T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/fixture/widget.git",
            git_tree_sha256="0" * 64,
        ),
    )


def test_acquisition_is_hardened_cached_and_materializes_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    runner = AcquisitionRunner()
    cache = tmp_path / "cache"
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    bundle = acquire_dotnet_dependencies(
        snapshot,
        "src/Product/Product.csproj",
        cache_root=cache,
        runner=runner,
    )

    assert bundle.acquisition.package_source == NUGET_ORG_V3_SOURCE
    assert bundle.acquisition.selected_manifest_path == "src/Product/Product.csproj"
    assert bundle.acquisition.target_framework == "net8.0"
    assert [item.relative_path for item in bundle.acquisition.artifacts] == [
        "newtonsoft.json/13.0.3"
    ]
    docker_argv = next(argv for argv in runner.commands if argv[0] == "run")
    joined = "\0".join(docker_argv)
    for expected in (
        ["--network", "bridge"],
        ["--read-only"],
        ["--cap-drop", "ALL"],
        ["--security-opt", "no-new-privileges:true"],
        ["--user", "65534:65534"],
        ["--source", NUGET_ORG_V3_SOURCE],
        ["--no-cache"],
        ["-p:TargetFramework=net8.0"],
        ["-p:TargetFrameworks=net8.0"],
    ):
        assert "\0".join(expected) in joined
    assert not any("TOKEN" in item or "SECRET" in item for item in docker_argv)
    assert any(argv[:2] == ["rm", "--force"] for argv in runner.commands)
    assert any(argv[:2] == ["container", "inspect"] for argv in runner.commands)

    destination = tmp_path / "offline-packages"
    materialize_dotnet_dependencies(bundle, destination)
    assert (destination / "newtonsoft.json/13.0.3/lib/net6.0/Newtonsoft.Json.dll").is_file()

    second_runner = AcquisitionRunner()
    second = acquire_dotnet_dependencies(
        snapshot,
        "src/Product/Product.csproj",
        cache_root=cache,
        runner=second_runner,
    )
    assert second.acquisition == bundle.acquisition
    assert second_runner.commands == []


def test_corrupt_cache_is_discarded_and_reacquired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)
    bundle = acquire_dotnet_dependencies(
        snapshot,
        "src/Product/Product.csproj",
        cache_root=tmp_path / "cache",
        runner=AcquisitionRunner(),
    )
    assembly = bundle.root / "packages/newtonsoft.json/13.0.3/lib/net6.0/Newtonsoft.Json.dll"
    assembly.write_bytes(b"tampered")

    runner = AcquisitionRunner()
    repaired = acquire_dotnet_dependencies(
        snapshot,
        "src/Product/Product.csproj",
        cache_root=tmp_path / "cache",
        runner=runner,
    )

    assert repaired.root == bundle.root
    assert (
        repaired.root / "packages/newtonsoft.json/13.0.3/lib/net6.0/Newtonsoft.Json.dll"
    ).read_bytes() == b"fixture assembly"
    assert len([argv for argv in runner.commands if argv[0] == "run"]) == 1


def test_transient_registry_failure_retries_with_fresh_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    runner = AcquisitionRunner(transient_failures=1)
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    bundle = acquire_dotnet_dependencies(
        snapshot,
        "src/Product/Product.csproj",
        cache_root=tmp_path / "cache",
        runner=runner,
        retry_sleep=lambda _seconds: None,
    )

    docker_runs = [argv for argv in runner.commands if argv[0] == "run"]
    assert len(docker_runs) == 2
    first_mount = docker_runs[0][docker_runs[0].index("--volume") + 1]
    second_mount = docker_runs[1][docker_runs[1].index("--volume") + 1]
    assert first_mount != second_mount
    assert bundle.acquisition.artifacts[0].package_id == "newtonsoft.json"


def test_unproven_cleanup_blocks_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    cache = tmp_path / "cache"
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    with pytest.raises(IsolatedExecutionError, match="cleanup could not be confirmed"):
        acquire_dotnet_dependencies(
            snapshot,
            "src/Product/Product.csproj",
            cache_root=cache,
            runner=AcquisitionRunner(cleanup_fails=True),
        )

    assert list(cache.glob("*/acquisition.json")) == []


def test_permanent_restore_failure_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    runner = AcquisitionRunner(permanent_failure=True)
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    with pytest.raises(IsolatedExecutionError, match="MSBuild project is invalid"):
        acquire_dotnet_dependencies(
            _snapshot(source),
            "src/Product/Product.csproj",
            cache_root=tmp_path / "cache",
            runner=runner,
            retry_sleep=lambda _seconds: None,
        )

    assert len([argv for argv in runner.commands if argv[0] == "run"]) == 1


def test_manifest_path_must_stay_inside_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    with pytest.raises(ValueError, match="stay inside"):
        acquire_dotnet_dependencies(
            _snapshot(source),
            "../outside.csproj",
            cache_root=tmp_path / "cache",
            runner=AcquisitionRunner(),
        )


def test_mutable_sdk_image_is_rejected_before_docker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    _source(source)
    runner = AcquisitionRunner()
    monkeypatch.setattr(dotnet_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    with pytest.raises(ValueError, match="must be pinned"):
        acquire_dotnet_dependencies(
            _snapshot(source),
            "src/Product/Product.csproj",
            cache_root=tmp_path / "cache",
            runner=runner,
            immutable_image="mcr.microsoft.com/dotnet/sdk:8.0",
        )

    assert runner.commands == []
