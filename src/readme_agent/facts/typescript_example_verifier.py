"""Verify TypeScript README examples against a pinned built package surface."""

from __future__ import annotations

import re

from readme_agent.ecosystems.typescript_api_schema import TypeScriptConsumerExampleV1
from readme_agent.ecosystems.typescript_package_layout import inspect_typescript_package_layout
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.typescript_consumer import prove_typescript_consumer
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1


def _import_specifier(code: str) -> str:
    matches = re.findall(r"import\s*\{[^}]+\}\s*from\s*['\"]([^'\"]+)['\"]", code)
    if len(set(matches)) != 1:
        raise ValueError("TypeScript example must use one unambiguous named package import")
    return matches[0]


def _selected_symbols(code: str, declared: list[str]) -> list[str]:
    imported_group = re.search(r"import\s*\{([^}]+)\}\s*from", code)
    if imported_group is None:
        raise ValueError("TypeScript example has no named import")
    imported = [
        item.split(" as ", 1)[-1].strip()
        for item in imported_group.group(1).split(",")
        if item.strip()
    ]
    selected = set(imported)
    for declaration in declared:
        parts = declaration.split(".")
        if (
            not parts
            or parts[0] not in imported
            or any(f".{member}" not in code for member in parts[1:])
        ):
            raise ValueError(f"declared TypeScript symbol is not used: {declaration!r}")
        selected.add(declaration)
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
    """Build and compile the exact example against the compiler-resolved entry point."""

    package = inspect_typescript_package_layout(snapshot.root_path)
    consumer = TypeScriptConsumerExampleV1(
        code=example.code,
        import_specifier=_import_specifier(example.code),
        required_symbols=_selected_symbols(example.code, example.required_symbols),
    )
    proof = prove_typescript_consumer(snapshot, package, consumer)
    diagnostic = _diagnostic(proof.isolated_execution)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="typescript",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "pinned built package and exact TypeScript consumer compiled"
            if proof.accepted
            else "package build, export resolution, or exact TypeScript consumer compilation failed"
        ),
        build=diagnostic,
        example_compile=diagnostic,
        isolated_execution=proof.isolated_execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.verified_symbols,
        public_api_sha256=proof.surface.canonical_hash() if proof.surface else None,
        typescript_package=package,
    )
