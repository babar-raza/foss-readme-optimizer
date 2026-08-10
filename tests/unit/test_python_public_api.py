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
from readme_agent.facts.python_consumer import prove_python_consumer
from readme_agent.facts.python_toolchain import PYTHON_312_IMAGE
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
        "@dataclass(slots=True)\n"
        "class Result:\n"
        "    size: int\n\n"
        "class Runtime:\n"
        "    def __init__(self) -> None:\n"
        "        self.DisplayName: str | None = None\n"
        "        self._internal: str | None = None\n\n"
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


def test_package_layout_uses_static_setuptools_dynamic_version(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "widget-foss"\ndynamic = ["version"]\n'
        '[tool.setuptools]\npackage-dir = {"" = "src"}\n'
        '[tool.setuptools.packages.find]\nwhere = ["src"]\ninclude = ["widget"]\n'
        '[tool.setuptools.dynamic]\nversion = {attr = "widget._version.VERSION"}\n',
        encoding="utf-8",
    )
    package = tmp_path / "src" / "widget"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "_version.py").write_text('VERSION = "2.0.0rc1"\n', encoding="utf-8")

    layout = inspect_python_package_layout(tmp_path)

    assert layout.version == "2.0.0rc1"


def test_package_layout_expands_setuptools_trailing_wildcard_include(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "cssforge"\nrequires-python = ">=3.13"\n'
        '[tool.setuptools.packages.find]\ninclude = ["engine*"]\n',
        encoding="utf-8",
    )
    package = tmp_path / "engine"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "driver.py").write_text("def render(): pass\n", encoding="utf-8")

    layout = inspect_python_package_layout(tmp_path)

    assert layout.canonical_import == "engine"
    assert layout.package_paths == ["engine"]


def test_hatch_package_declaration_excludes_repository_example_packages(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aspose-words-foss"\nversion = "1.0.0"\n'
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["aspose"]\n',
        encoding="utf-8",
    )
    (tmp_path / "ApiExamples").mkdir()
    (tmp_path / "ApiExamples" / "__init__.py").write_text("", encoding="utf-8")
    package = tmp_path / "aspose" / "words_foss"
    package.mkdir(parents=True)
    (tmp_path / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("class Document: pass\n", encoding="utf-8")

    layout = inspect_python_package_layout(tmp_path)

    assert layout.canonical_import == "aspose.words_foss"
    assert layout.package_paths == ["aspose", "aspose/words_foss"]


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
    assert symbols["aspose.widget.models.Runtime.DisplayName"].kind == "typed_field"
    assert symbols["aspose.widget.models.Runtime.DisplayName"].annotation == "str | None"
    assert "aspose.widget.models.Runtime._internal" not in symbols
    assert "aspose.widget.models._private" not in symbols
    assert "aspose.widget.models.abstractmethod" not in symbols
    assert surface.unresolved_reexports == ["aspose.widget:2:from .wildcard import *"]


def test_public_surface_does_not_parse_private_modules(tmp_path):
    _write_package(tmp_path)
    private_module = tmp_path / "src" / "aspose" / "widget" / "_broken.py"
    private_module.write_text("for item in []:\nprint(item)\n", encoding="utf-8")

    surface = inspect_python_public_api(
        tmp_path,
        org_repo="acme/widget",
        source_revision="revision-private-module",
    )

    assert any(symbol.qualified_name == "aspose.widget.Widget" for symbol in surface.symbols)
    assert not any("_broken" in symbol.qualified_name for symbol in surface.symbols)


def test_public_surface_resolves_members_from_an_explicit_private_reexport(tmp_path):
    _write_package(tmp_path)
    package = tmp_path / "src" / "aspose" / "widget"
    (package / "__init__.py").write_text(
        "from ._font_base import Font\n__all__ = ['Font']\n",
        encoding="utf-8",
    )
    (package / "_font_base.py").write_text(
        "class Font:\n    def save(self, path: str) -> None:\n        return None\n",
        encoding="utf-8",
    )

    surface = inspect_python_public_api(
        tmp_path,
        org_repo="acme/widget",
        source_revision="revision-private-reexport",
    )
    symbols = {symbol.qualified_name: symbol for symbol in surface.symbols}

    assert symbols["aspose.widget.Font"].kind == "class"
    assert symbols["aspose.widget.Font"].source_path.endswith("_font_base.py")
    assert symbols["aspose.widget.Font.save"].kind == "method"
    assert symbols["aspose.widget.Font.save"].reexported_from == (
        "aspose.widget._font_base.Font.save"
    )
    assert not any("aspose.widget._font_base" in name for name in symbols)


def test_public_surface_records_and_skips_a_malformed_public_module(tmp_path):
    _write_package(tmp_path)
    public_module = tmp_path / "src" / "aspose" / "widget" / "broken.py"
    public_module.write_text("for item in []:\nprint(item)\n", encoding="utf-8")

    surface = inspect_python_public_api(
        tmp_path,
        org_repo="acme/widget",
        source_revision="revision-public-module",
    )

    assert any(symbol.qualified_name == "aspose.widget.Widget" for symbol in surface.symbols)
    assert "aspose.widget:2:from .wildcard import *" in surface.unresolved_reexports
    assert any(
        item.startswith("aspose.widget.broken:2:syntax-error:src/aspose/widget/broken.py:")
        for item in surface.unresolved_reexports
    )


def test_package_layout_and_public_api_accept_utf8_bom_source(tmp_path):
    _write_package(tmp_path, manifest="setup.py")
    setup = tmp_path / "setup.py"
    setup.write_text(setup.read_text(encoding="utf-8"), encoding="utf-8-sig")
    models = tmp_path / "aspose" / "widget" / "models.py"
    models.write_text(models.read_text(encoding="utf-8"), encoding="utf-8-sig")

    layout = inspect_python_package_layout(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo="acme/widget",
        source_revision="revision-bom",
    )

    assert layout.distribution_name == "widget-foss"
    assert any(symbol.qualified_name == "aspose.widget.models.Widget" for symbol in surface.symbols)


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
            requested_reference=request.policy.immutable_image,
            repo_digest=request.policy.immutable_image,
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
    assert proof.isolated_execution.policy.tmpfs_mebibytes == 256


def test_consumer_records_a_typed_source_tree_fallback(tmp_path):
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

    def source_tree_executor(request):
        result = _successful_executor(request)
        payload = {
            "execution_mode": "source_tree",
            "source_install_failure": "invalid_build_backend",
            "verified_symbols": example.required_symbols,
        }
        return result.model_copy(
            update={"stdout": "README_AGENT_PYTHON_CONSUMER=" + json.dumps(payload, sort_keys=True)}
        )

    proof = prove_python_consumer(snapshot, surface, example, executor=source_tree_executor)

    assert proof.accepted is True
    assert proof.execution_mode == "source_tree"
    assert proof.source_install_failure == "invalid_build_backend"


def test_consumer_selects_python_312_for_repository_requirement(tmp_path):
    _write_package(tmp_path)
    manifest = tmp_path / "pyproject.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            'requires-python = ">=3.11"',
            'requires-python = ">=3.12"',
        ),
        encoding="utf-8",
    )
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
    assert proof.isolated_execution.policy.immutable_image == PYTHON_312_IMAGE


def test_consumer_accepts_and_requires_use_of_an_aliased_package_import(tmp_path):
    _write_package(tmp_path)
    snapshot = _git_snapshot(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    example = ConsumerExampleV1(
        code="import aspose.widget as widget\nprint(widget.Widget.name)\n",
        required_symbols=["aspose.widget"],
    )

    proof = prove_python_consumer(snapshot, surface, example, executor=_successful_executor)

    assert proof.accepted is True
    assert proof.verified_symbols == ["aspose.widget"]

    with pytest.raises(ValueError, match="must import and use"):
        prove_python_consumer(
            snapshot,
            surface,
            ConsumerExampleV1(
                code="import aspose.widget as widget\nprint('unused alias')\n",
                required_symbols=["aspose.widget"],
            ),
            executor=_successful_executor,
        )


def test_consumer_stages_repository_fixture_for_placeholder_input(tmp_path):
    _write_package(tmp_path)
    fixture = tmp_path / "testdata" / "minimal.ps"
    fixture.parent.mkdir()
    fixture.write_text("%!PS\nshowpage\n", encoding="utf-8")
    snapshot = _git_snapshot(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    example = ConsumerExampleV1(
        code=("from aspose.widget import Widget\nWidget.from_file('input.ps')\n"),
        required_symbols=["aspose.widget.Widget"],
    )

    def asserting_executor(request):
        assert (request.source_root / "input.ps").read_bytes() == fixture.read_bytes()
        return _successful_executor(request)

    proof = prove_python_consumer(snapshot, surface, example, executor=asserting_executor)

    assert proof.accepted is True
    assert [binding.model_dump() for binding in proof.fixture_bindings] == [
        {
            "source_path": "testdata/minimal.ps",
            "target_path": "input.ps",
            "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "size_bytes": fixture.stat().st_size,
        }
    ]


def test_consumer_binds_fixture_already_copied_at_exact_repository_path(tmp_path):
    _write_package(tmp_path)
    fixture = tmp_path / "testfiles" / "TagSizes.one"
    fixture.parent.mkdir()
    fixture.write_bytes(b"exact repository fixture\n")
    snapshot = _git_snapshot(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    example = ConsumerExampleV1(
        code=("from aspose.widget import Widget\nWidget('testfiles/TagSizes.one')\n"),
        required_symbols=["aspose.widget.Widget"],
    )

    def asserting_executor(request):
        copied = request.source_root / "testfiles" / "TagSizes.one"
        assert copied.read_bytes() == fixture.read_bytes()
        return _successful_executor(request)

    proof = prove_python_consumer(snapshot, surface, example, executor=asserting_executor)

    assert proof.accepted is True
    assert [binding.model_dump() for binding in proof.fixture_bindings] == [
        {
            "source_path": "testfiles/TagSizes.one",
            "target_path": "testfiles/TagSizes.one",
            "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "size_bytes": fixture.stat().st_size,
        }
    ]


def test_consumer_does_not_substitute_an_unrelated_fixture_for_constructor_input(tmp_path):
    _write_package(tmp_path)
    fixture = tmp_path / "testfiles" / "Different.one"
    fixture.parent.mkdir()
    fixture.write_bytes(b"unrelated repository fixture\n")
    snapshot = _git_snapshot(tmp_path)
    surface = inspect_python_public_api(
        tmp_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    example = ConsumerExampleV1(
        code=("from aspose.widget import Widget\nWidget('testfiles/Missing.one')\n"),
        required_symbols=["aspose.widget.Widget"],
    )

    def asserting_executor(request):
        assert not (request.source_root / "testfiles" / "Missing.one").exists()
        return _successful_executor(request)

    proof = prove_python_consumer(snapshot, surface, example, executor=asserting_executor)

    assert proof.fixture_bindings == []


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
