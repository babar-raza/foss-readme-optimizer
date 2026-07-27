"""Install a pinned Python source snapshot and prove exact public consumer use."""

from __future__ import annotations

import ast
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

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
from readme_agent.facts.python_consumer_schema import PythonConsumerProofV1
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

PYTHON_311_IMAGE = "python@sha256:13f0881a239ca0d27fb8b2539536ace85f7d680a707bfaa178571e1dbfe85a91"
_RESULT_PREFIX = "README_AGENT_PYTHON_CONSUMER="
_COPY_IGNORE = shutil.ignore_patterns(".git", ".venv", "__pycache__", "build", "dist")
_DRIVER = r"""
import importlib
import json
import pathlib
import subprocess
import sys

target = pathlib.Path("/workspace/.readme-agent-installed")
install = subprocess.run(
    [
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
        "--no-deps", "--no-build-isolation", "--target", str(target), ".",
    ],
    text=True, capture_output=True,
)
if install.returncode:
    sys.stderr.write(install.stdout + install.stderr)
    raise SystemExit(20)
sys.path.insert(0, str(target))
specs = json.loads(pathlib.Path(".readme-agent-symbols.json").read_text())
verified = []
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
code = pathlib.Path(".readme-agent-consumer.py").read_text()
exec(compile(code, ".readme-agent-consumer.py", "exec"), {"__name__": "__main__"})
print("README_AGENT_PYTHON_CONSUMER=" + json.dumps({"verified_symbols": verified}, sort_keys=True))
""".strip()

IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]


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
    imported_modules: set[str] = set()
    used_names: set[str] = set()
    used_attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.update((node.module, alias.name) for alias in node.names)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
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
                or symbol.import_module.split(".")[0] not in used_names
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
    immutable_image: str = PYTHON_311_IMAGE,
) -> PythonConsumerProofV1:
    """Install the immutable source with no dependencies/network, then import and use symbols."""

    verify_repository_snapshot(snapshot)
    if surface.org_repo != snapshot.org_repo or surface.source_revision != snapshot.source_revision:
        raise ValueError("Python surface does not belong to the immutable repository snapshot")
    selected = _required_surface_symbols(surface, example)
    _example_imports_and_uses(example.code, selected)
    with tempfile.TemporaryDirectory(prefix="readme-agent-python-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        _copy_snapshot(snapshot, workspace)
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
        request = IsolatedExecutionRequestV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            source_root=workspace,
            argv=["python", "-I", ".readme-agent-consumer-driver.py"],
            environment={"HOME": "/tmp", "PIP_CACHE_DIR": "/tmp/pip-cache"},
            policy=IsolatedExecutionPolicyV1(
                immutable_image=immutable_image,
                timeout_seconds=300,
                memory_mebibytes=512,
                pids_limit=64,
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
    if len(payloads) == 1:
        payload = json.loads(payloads[0])
        if isinstance(payload.get("verified_symbols"), list):
            verified = [str(name) for name in payload["verified_symbols"]]
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
        verified_symbols=verified,
        isolated_execution=result,
        accepted=accepted,
    )
