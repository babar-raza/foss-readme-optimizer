"""Install a pinned Python source snapshot and prove exact public consumer use."""

from __future__ import annotations

import ast
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from readme_agent.ecosystems.python_api_schema import (
    ConsumerExampleV1,
    PublicApiSurfaceV1,
    PublicSymbolV1,
)
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.python_consumer_fixtures import stage_repository_input_fixtures
from readme_agent.facts.python_consumer_schema import PythonConsumerProofV1
from readme_agent.facts.python_dependency_acquisition import (
    PythonDependencyBundle,
    acquire_python_dependencies,
    materialize_python_dependencies,
)
from readme_agent.facts.python_toolchain import select_python_image
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

_RESULT_PREFIX = "README_AGENT_PYTHON_CONSUMER="
_COPY_IGNORE = shutil.ignore_patterns(".git", ".venv", "__pycache__", "build", "dist")
_DRIVER = r"""
import importlib
import json
import os
import pathlib
import subprocess
import sys
import traceback

target = pathlib.Path("/workspace/.readme-agent-installed")
wheelhouse = pathlib.Path("/workspace/.readme-agent-wheelhouse")
wheels = sorted(str(path) for path in wheelhouse.glob("*.whl"))
if wheels:
    dependencies = subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
            "--no-index", "--no-deps", "--target", str(target), *wheels,
        ],
        text=True, capture_output=True,
    )
    if dependencies.returncode:
        sys.stderr.write(dependencies.stdout + dependencies.stderr)
        raise SystemExit(19)
install = subprocess.run(
    [
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
        "--no-deps", "--no-build-isolation", "--target", str(target), ".",
    ],
    text=True, capture_output=True,
    env={**os.environ, "PYTHONPATH": str(target)},
)
execution_mode = "installed_package"
source_install_failure = None
if install.returncode and (
    "BackendUnavailable" in install.stderr
    and "ModuleNotFoundError" in install.stderr
):
    package = json.loads(pathlib.Path(".readme-agent-package.json").read_text())
    source_root = pathlib.Path("/workspace") / package["source_root"]
    if not source_root.is_dir():
        sys.stderr.write(install.stdout + install.stderr)
        raise SystemExit(20)
    execution_mode = "source_tree"
    source_install_failure = "invalid_build_backend"
    sys.path.insert(0, str(source_root))
elif install.returncode:
    sys.stderr.write(install.stdout + install.stderr)
    raise SystemExit(20)
sys.path.insert(0, str(target))
specs = json.loads(pathlib.Path(".readme-agent-symbols.json").read_text())
verified = []
try:
    for spec in specs:
        value = importlib.import_module(spec["module"])
        for part in filter(None, spec["name"].split(".")):
            if hasattr(value, part):
                value = getattr(value, part)
            elif part in getattr(value, "__annotations__", {}):
                value = value.__annotations__[part]
            else:
                raise AttributeError(f'{spec["qualified_name"]} is not publicly resolvable')
        verified.append(spec["qualified_name"])
except Exception:
    traceback.print_exc()
    raise SystemExit(21)
code = pathlib.Path(".readme-agent-consumer.py").read_text()
try:
    exec(compile(code, ".readme-agent-consumer.py", "exec"), {"__name__": "__main__"})
except Exception:
    traceback.print_exc()
    raise SystemExit(22)
print("README_AGENT_PYTHON_CONSUMER=" + json.dumps({
    "execution_mode": execution_mode,
    "source_install_failure": source_install_failure,
    "verified_symbols": verified,
}, sort_keys=True))
""".strip()

IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]
DependencyAcquirer = Callable[..., PythonDependencyBundle | None]


def _required_surface_symbols(
    surface: PublicApiSurfaceV1,
    example: ConsumerExampleV1,
) -> list[PublicSymbolV1]:
    by_name = {symbol.qualified_name: symbol for symbol in surface.symbols}
    missing = sorted(set(example.required_symbols) - set(by_name))
    if missing:
        raise ValueError(f"consumer example selects non-public Python symbols: {missing}")
    return [by_name[name] for name in example.required_symbols]


def _example_imports_and_uses(code: str, symbols: list[PublicSymbolV1]) -> None:
    tree = ast.parse(code, filename=".readme-agent-consumer.py")
    imported: set[tuple[str, str]] = set()
    imported_modules: dict[str, set[str]] = {}
    used_names: set[str] = set()
    used_attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.update((node.module, alias.name) for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound_name = alias.asname or alias.name.split(".", 1)[0]
                imported_modules.setdefault(alias.name, set()).add(bound_name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            used_attributes.add(node.attr)
    failures = [
        symbol.qualified_name
        for symbol in symbols
        if (
            symbol.name
            and (
                (symbol.import_module, symbol.name.split(".")[0]) not in imported
                or symbol.name.split(".")[0] not in used_names
                or any(part not in used_attributes for part in symbol.name.split(".")[1:])
            )
        )
        or (
            not symbol.name
            and (
                symbol.import_module not in imported_modules
                or not (imported_modules[symbol.import_module] & used_names)
            )
        )
    ]
    if failures:
        raise ValueError(
            "consumer example must import and use each selected public symbol: "
            + ", ".join(failures)
        )


def _copy_snapshot(snapshot: RepositorySnapshotV1, destination: Path) -> None:
    shutil.copytree(snapshot.root_path, destination, ignore=_COPY_IGNORE)


def prove_python_consumer(
    snapshot: RepositorySnapshotV1,
    surface: PublicApiSurfaceV1,
    example: ConsumerExampleV1,
    *,
    executor: IsolatedExecutor = execute_isolated,
    dependency_acquirer: DependencyAcquirer = acquire_python_dependencies,
    immutable_image: str | None = None,
) -> PythonConsumerProofV1:
    """Install the immutable source with no dependencies/network, then import and use symbols."""

    verify_repository_snapshot(snapshot)
    if surface.org_repo != snapshot.org_repo or surface.source_revision != snapshot.source_revision:
        raise ValueError("Python surface does not belong to the immutable repository snapshot")
    selected = _required_surface_symbols(surface, example)
    _example_imports_and_uses(example.code, selected)
    active_image = immutable_image or select_python_image(surface.package.requires_python)
    dependency_bundle = dependency_acquirer(
        snapshot,
        surface.package,
        immutable_image=active_image,
    )
    with tempfile.TemporaryDirectory(prefix="readme-agent-python-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        _copy_snapshot(snapshot, workspace)
        if dependency_bundle is not None:
            materialize_python_dependencies(
                dependency_bundle,
                workspace / ".readme-agent-wheelhouse",
            )
        fixture_bindings = stage_repository_input_fixtures(
            snapshot,
            workspace,
            example.code,
        )
        (workspace / ".readme-agent-consumer-driver.py").write_text(
            _DRIVER,
            encoding="utf-8",
            newline="\n",
        )
        (workspace / ".readme-agent-consumer.py").write_text(
            example.code,
            encoding="utf-8",
            newline="\n",
        )
        specifications = [
            {
                "qualified_name": symbol.qualified_name,
                "module": symbol.import_module,
                "name": symbol.name,
            }
            for symbol in selected
        ]
        (workspace / ".readme-agent-symbols.json").write_text(
            json.dumps(specifications, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )
        (workspace / ".readme-agent-package.json").write_text(
            json.dumps({"source_root": surface.package.source_root}, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )
        request = IsolatedExecutionRequestV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            source_root=workspace,
            argv=["python", "-I", ".readme-agent-consumer-driver.py"],
            environment={"HOME": "/tmp", "PIP_CACHE_DIR": "/tmp/pip-cache"},
            policy=IsolatedExecutionPolicyV1(
                immutable_image=active_image,
                timeout_seconds=300,
                memory_mebibytes=512,
                pids_limit=64,
                tmpfs_mebibytes=256,
            ),
        )
        result = executor(request)
    verify_repository_snapshot(snapshot)
    payloads = [
        line.removeprefix(_RESULT_PREFIX)
        for line in result.stdout.splitlines()
        if line.startswith(_RESULT_PREFIX)
    ]
    verified: list[str] = []
    execution_mode: Literal["installed_package", "source_tree"] = "installed_package"
    source_install_failure: Literal["invalid_build_backend"] | None = None
    if len(payloads) == 1:
        payload = json.loads(payloads[0])
        if isinstance(payload.get("verified_symbols"), list):
            verified = [str(name) for name in payload["verified_symbols"]]
        if payload.get("execution_mode") in {"installed_package", "source_tree"}:
            execution_mode = payload["execution_mode"]
        if payload.get("source_install_failure") == "invalid_build_backend":
            source_install_failure = "invalid_build_backend"
    accepted = (
        result.truth_eligible
        and result.return_code == 0
        and set(verified) == set(example.required_symbols)
    )
    return PythonConsumerProofV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        package=surface.package,
        example=example,
        fixture_bindings=fixture_bindings,
        dependency_acquisition=(
            dependency_bundle.acquisition if dependency_bundle is not None else None
        ),
        execution_mode=execution_mode,
        source_install_failure=source_install_failure,
        verified_symbols=verified,
        isolated_execution=result,
        accepted=accepted,
    )
