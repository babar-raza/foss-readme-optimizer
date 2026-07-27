"""Python package-layout and public-API truth controls."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from readme_agent.ecosystems.python_api_schema import ConsumerExampleV1
from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.ecosystems.python_public_api import inspect_python_public_api
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.python_consumer import PYTHON_311_IMAGE, prove_python_consumer
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _write_package(root: Path, *, manifest: str = "pyproject") -> None:
    if manifest == "pyproject":
        (root / "pyproject.toml").write_text(
            '[project]\nname = "widget-foss"\nversion = "1.2.3"\n'
            'requires-python = ">=3.11"\n'
            '[tool.setuptools.package-dir]\n"" = "src"\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\ninclude = ["aspose.widget", "aspose.widget.*"]\n',
            encoding="utf-8",
        )
        source = root / "src"
    elif manifest == "setup.cfg":
        (root / "setup.cfg").write_text(
            "[metadata]\nname = widget-foss\nversion = 2.0\n"
            "[options]\npackage_dir =\n    =src\npackages = find_namespace:\n"
            "python_requires = >=3.11\n",
            encoding="utf-8",
        )
        source = root / "src"
    else:
        (root / "setup.py").write_text(
            "from setuptools import find_packages, setup\n"
            'setup(name="widget-foss", version="3.0", packages=find_packages())\n',
            encoding="utf-8",
        )
        source = root
    package = source / "aspose" / "widget"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        "from .models import Color, Config, Widget\n"
        "from .wildcard import *\n"
        "__all__ = ['Widget', 'Color', 'Config']\n",
        encoding="utf-8",
    )
    (package / "models.py").write_text(
        "from abc import abstractmethod\n"
        "from dataclasses import dataclass\n"
        "from enum import Enum\n"
        "from typing import TypedDict\n\n"
        "class Widget:\n"
        "    @property\n"
        "    @abstractmethod\n"
        "    def name(self) -> str: ...\n\n"
        "    @name.setter\n"
        "    @abstractmethod\n"
        "    def name(self, value: str) -> None: ...\n\n"
        "    def render(self) -> bytes: return b''\n\n"
        "class Color(Enum):\n"
        "    RED = 'red'\n\n"
        "class Config(TypedDict):\n"
        "    quality: int\n\n"
        "@dataclass\n"
        "class Result:\n"
        "    size: int\n\n"
        "def helper() -> str: return 'ok'\n"
        "def _private() -> None: pass\n",
        encoding="utf-8",
    )
    (package / "wildcard.py").write_text("from .models import *\n", encoding="utf-8")


def _git_snapshot(root: Path) -> RepositorySnapshotV1:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True
    ).stdout.strip()
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--full-tree", "HEAD"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    inventory = hashlib.sha256(listing.encode("utf-8")).hexdigest()
    return RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision=revision,
        snapshot_root=str(root.resolve()),
        inventory_sha256=inventory,
        captured_at=datetime.now(UTC).isoformat(),
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/acme/widget.git",
            git_tree_sha256=inventory,
        ),
    )


@pytest.mark.parametrize("manifest", ["pyproject", "setup.cfg", "setup.py"])
def test_package_layout_detects_src_namespace_and_setup_variants(tmp_path, manifest):
    _write_package(tmp_path, manifest=manifest)

    layout = inspect_python_package_layout(tmp_path)

    assert layout.distribution_name == "widget-foss"
    assert layout.canonical_import == "aspose.widget"
    assert "aspose.widget" in [path.replace("/", ".") for path in layout.package_paths]
    if manifest != "setup.py":
        assert layout.source_root == "src"
        assert layout.namespace_packages == ["aspose"]


def test_package_layout_detects_pep420_leaf_without_initializer(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "namespace-widget"\n'
        '[tool.setuptools.package-dir]\n"" = "src"\n'
        '[tool.setuptools.packages.find]\nwhere = ["src"]\nnamespaces = true\n',
        encoding="utf-8",
    )
    package = tmp_path / "src" / "acme" / "widget"
    package.mkdir(parents=True)
    (package / "core.py").write_text("class Widget: pass\n", encoding="utf-8")

    layout = inspect_python_package_layout(tmp_path)

    assert layout.canonical_import == "acme.widget"
    assert layout.package_paths == ["acme/widget"]
    assert layout.namespace_packages == ["acme"]


def test_public_surface_tracks_reexports_types_fields_and_full_property_stack(tmp_path):
    _write_package(tmp_path)

    surface = inspect_python_public_api(
        tmp_path,
        org_repo="acme/widget",
        source_revision="revision-123",
    )
    symbols = {symbol.qualified_name: symbol for symbol in surface.symbols}

    assert symbols["aspose.widget.Widget"].reexported_from == "aspose.widget.models.Widget"
    assert (
        symbols["aspose.widget.Widget.name"].reexported_from == "aspose.widget.models.Widget.name"
    )
    assert symbols["aspose.widget.models.Widget.name"].kind == "property"
    assert symbols["aspose.widget.models.Widget.name"].writable is True
    assert symbols["aspose.widget.models.Widget.name"].decorators == [
        "property",
        "abstractmethod",
    ]
    assert symbols["aspose.widget.models.Color.RED"].kind == "enum_member"
    assert symbols["aspose.widget.models.Config.quality"].kind == "typed_field"
    assert symbols["aspose.widget.models.Result.size"].kind == "typed_field"
    assert "aspose.widget.models._private" not in symbols
    assert "aspose.widget.models.abstractmethod" not in symbols
    assert surface.unresolved_reexports == ["aspose.widget:2:from .wildcard import *"]


def _successful_executor(
    request: IsolatedExecutionRequestV1,
) -> IsolatedExecutionResultV1:
    specifications = json.loads(
        (request.source_root / ".readme-agent-symbols.json").read_text(encoding="utf-8")
    )
    verified = [item["qualified_name"] for item in specifications]
    now = datetime.now(UTC).isoformat()
    return IsolatedExecutionResultV1(
        truth_eligible=True,
        org_repo=request.org_repo,
        source_revision=request.source_revision,
        argv=request.argv,
        environment_names=sorted(request.environment),
        input_sha256="a" * 64,
        input_file_count=10,
        policy_sha256="b" * 64,
        policy=request.policy,
        image=ContainerImageIdentityV1(
            requested_reference=PYTHON_311_IMAGE,
            repo_digest=PYTHON_311_IMAGE,
            image_id="sha256:" + "c" * 64,
            operating_system="linux",
            architecture="amd64",
            engine_version="test",
        ),
        container_id="fixture",
        process_inventory=["python consumer"],
        return_code=0,
        stdout=(
            "README_AGENT_PYTHON_CONSUMER="
            + json.dumps({"verified_symbols": verified}, sort_keys=True)
        ),
        stderr="",
        timed_out=False,
        oom_killed=False,
        started_at=now,
        finished_at=now,
        cleanup=ContainerCleanupV1(
            execution_container_removed=True,
            seed_container_removed=True,
            workspace_volume_removed=True,
        ),
    )


def test_consumer_requires_public_symbols_and_installed_import_use(tmp_path):
    _write_package(tmp_path)
    snapshot = _git_snapshot(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    example = ConsumerExampleV1(
        code="from aspose.widget import Widget\nprint(Widget.name)\n",
        required_symbols=["aspose.widget.Widget", "aspose.widget.Widget.name"],
    )

    proof = prove_python_consumer(snapshot, surface, example, executor=_successful_executor)

    assert proof.accepted is True
    assert proof.verified_symbols == ["aspose.widget.Widget", "aspose.widget.Widget.name"]
    assert proof.isolated_execution.policy.network_mode == "none"
    assert proof.isolated_execution.policy.read_only_rootfs is True


def test_consumer_rejects_missing_reexport_private_and_detached_compile(tmp_path):
    _write_package(tmp_path)
    snapshot = _git_snapshot(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )

    with pytest.raises(ValueError, match="non-public"):
        prove_python_consumer(
            snapshot,
            surface,
            ConsumerExampleV1(
                code="from aspose.widget import Result\nprint(Result)\n",
                required_symbols=["aspose.widget.Result"],
            ),
            executor=_successful_executor,
        )
    with pytest.raises(ValueError, match="non-public"):
        prove_python_consumer(
            snapshot,
            surface,
            ConsumerExampleV1(
                code="from aspose.widget.models import _private\n_private()\n",
                required_symbols=["aspose.widget.models._private"],
            ),
            executor=_successful_executor,
        )
    with pytest.raises(ValueError, match="must import and use"):
        prove_python_consumer(
            snapshot,
            surface,
            ConsumerExampleV1(
                code="print('syntax alone is insufficient')\n",
                required_symbols=["aspose.widget.Widget"],
            ),
            executor=_successful_executor,
        )
