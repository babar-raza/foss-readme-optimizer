"""Python dependency wheels are acquired once and consumed offline."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.facts import python_dependency_acquisition
from readme_agent.facts.python_dependency_acquisition import (
    PYTHON_311_IMAGE,
    acquire_python_dependencies,
    materialize_python_dependencies,
)
from readme_agent.facts.python_toolchain import PYTHON_312_IMAGE, select_python_image
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _completed(argv, *, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class AcquisitionRunner:
    """Fake Docker boundary that materializes the wheel it reports."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, argv, *, timeout_seconds, input_bytes=None):
        self.commands.append(argv)
        if argv[:2] == ["image", "inspect"]:
            return _completed(
                argv,
                stdout=json.dumps(
                    [
                        {
                            "RepoDigests": [PYTHON_311_IMAGE],
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
            mounted = argv[argv.index("--volume") + 1]
            workspace = Path(mounted.removesuffix(":/workspace"))
            (workspace / "wheelhouse" / "lxml-5.4.0-cp311-cp311-manylinux.whl").write_bytes(
                b"fixture wheel"
            )
            return _completed(argv)
        if argv[:2] == ["rm", "--force"]:
            return _completed(argv)
        if argv[:2] == ["container", "inspect"]:
            return _completed(argv, returncode=1, stderr="not found")
        if argv[:2] == ["ps", "-aq"]:
            return _completed(argv)
        raise AssertionError(f"unexpected Docker command: {argv}")


def _source(root: Path) -> None:
    root.mkdir()
    (root / "pyproject.toml").write_text(
        """[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
[project]
name = "widget"
version = "1.0.0"
dependencies = ["lxml>=4.9"]
[tool.setuptools]
packages = ["widget"]
""",
        encoding="utf-8",
    )
    package = root / "widget"
    package.mkdir()
    (package / "__init__.py").write_text("class Document: pass\n", encoding="utf-8")


def _snapshot(root: Path) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="fixture/widget",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        inventory_sha256="0" * 64,
        captured_at="2026-08-01T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/fixture/widget.git",
            git_tree_sha256="0" * 64,
        ),
    )


def test_binary_wheel_acquisition_is_bounded_cached_and_checksum_validated(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_python_package_layout(source)
    cache = tmp_path / "cache"
    runner = AcquisitionRunner()
    monkeypatch.setattr(
        python_dependency_acquisition,
        "verify_repository_snapshot",
        lambda _: None,
    )

    bundle = acquire_python_dependencies(
        snapshot,
        package,
        cache_root=cache,
        runner=runner,
    )
    assert bundle is not None
    assert bundle.acquisition.requirements == ["lxml>=4.9", "setuptools"]
    assert len(bundle.acquisition.artifacts) == 1
    docker_argv = next(argv for argv in runner.commands if argv[0] == "run")
    joined = "\0".join(docker_argv)
    for expected in (
        ["--network", "bridge"],
        ["--read-only"],
        ["--cap-drop", "ALL"],
        ["--security-opt", "no-new-privileges:true"],
        ["--user", "65534:65534"],
        ["--only-binary=:all:"],
    ):
        assert "\0".join(expected) in joined
    assert not any("TOKEN" in item or "SECRET" in item for item in docker_argv)

    destination = tmp_path / "offline"
    materialize_python_dependencies(bundle, destination)
    assert (destination / bundle.acquisition.artifacts[0].filename).is_file()

    second_runner = AcquisitionRunner()
    second = acquire_python_dependencies(
        snapshot,
        package,
        cache_root=cache,
        runner=second_runner,
    )
    assert second is not None
    assert second.acquisition == bundle.acquisition
    assert second_runner.commands == []

    (bundle.root / "wheelhouse" / bundle.acquisition.artifacts[0].filename).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum validation"):
        acquire_python_dependencies(
            snapshot,
            package,
            cache_root=cache,
            runner=AcquisitionRunner(),
        )


def test_packages_without_declared_dependencies_need_no_network(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    (source / "pyproject.toml").write_text(
        (source / "pyproject.toml")
        .read_text(encoding="utf-8")
        .replace('dependencies = ["lxml>=4.9"]\n', "")
        .replace('requires = ["setuptools"]\n', "requires = []\n"),
        encoding="utf-8",
    )
    snapshot = _snapshot(source)
    package = inspect_python_package_layout(source)
    monkeypatch.setattr(
        python_dependency_acquisition,
        "verify_repository_snapshot",
        lambda _: None,
    )

    assert (
        acquire_python_dependencies(
            snapshot,
            package,
            cache_root=tmp_path / "cache",
            runner=AcquisitionRunner(),
        )
        is None
    )


@pytest.mark.parametrize(
    ("requires_python", "expected"),
    [
        (None, PYTHON_311_IMAGE),
        (">=3.7", PYTHON_311_IMAGE),
        (">=3.11,<3.13", PYTHON_311_IMAGE),
        (">=3.12", PYTHON_312_IMAGE),
    ],
)
def test_selects_lowest_compatible_approved_python_runtime(requires_python, expected):
    assert select_python_image(requires_python) == expected


def test_rejects_unsupported_or_invalid_python_runtime_ranges():
    with pytest.raises(ValueError, match="no approved immutable Python runtime"):
        select_python_image(">=3.13")
    with pytest.raises(ValueError, match="invalid requires-python"):
        select_python_image("not-a-version")
