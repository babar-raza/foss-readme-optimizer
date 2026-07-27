"""Verify an exact Python README example against an installed public package."""

from __future__ import annotations

import ast
import re

from readme_agent.ecosystems.python_api_schema import ConsumerExampleV1
from readme_agent.ecosystems.python_public_api import inspect_python_public_api
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.python_consumer import prove_python_consumer
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1


def _selected_imports(
    code: str,
    public_names: set[str],
    package_prefix: str,
    declared_symbols: list[str],
) -> list[str]:
    tree = ast.parse(code, filename=".readme-agent-consumer.py")
    attempted: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == package_prefix or node.module.startswith(f"{package_prefix}."):
                attempted.extend(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            attempted.extend(
                alias.name
                for alias in node.names
                if alias.name == package_prefix or alias.name.startswith(f"{package_prefix}.")
            )
    if not attempted:
        raise ValueError("Python README example imports no symbol from the distributed package")
    missing = sorted(set(attempted) - public_names)
    if missing:
        raise ValueError(f"Python README example imports non-public symbols: {missing}")
    selected = set(attempted)
    for declaration in declared_symbols:
        tokens = re.findall(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", declaration)
        matches = [
            name
            for name in public_names
            if any(name == token or name.endswith(f".{token}") for token in tokens)
            and any(name == imported or name.startswith(f"{imported}.") for imported in attempted)
        ]
        if not matches:
            raise ValueError(
                f"declared Python example symbol is not a selected public API: {declaration!r}"
            )
        selected.add(min(matches, key=lambda name: (name.count("."), name)))
    return sorted(selected)


def _diagnostic(result) -> ExampleExecutionResultV1:
    return ExampleExecutionResultV1(
        argv=result.argv,
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=result.timed_out,
        environment_names=result.environment_names,
        isolation_kind="isolated_result_projection",
    )


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
) -> LocalProductVerificationV1:
    """Install the pinned source and run the exact example through public imports."""

    surface = inspect_python_public_api(
        snapshot.root_path,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    package_prefix = surface.package.canonical_import.split(".")[0]
    required_symbols = _selected_imports(
        example.code,
        {symbol.qualified_name for symbol in surface.symbols},
        package_prefix,
        example.required_symbols,
    )
    proof = prove_python_consumer(
        snapshot,
        surface,
        ConsumerExampleV1(code=example.code, required_symbols=required_symbols),
    )
    diagnostic = _diagnostic(proof.isolated_execution)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="python",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "pinned package installed and exact public Python imports/example executed"
            if proof.accepted
            else "pinned package installation or exact public Python example failed"
        ),
        build=diagnostic,
        example_compile=diagnostic,
        isolated_execution=proof.isolated_execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.verified_symbols,
        public_api_sha256=surface.canonical_hash(),
        python_package=surface.package,
    )
