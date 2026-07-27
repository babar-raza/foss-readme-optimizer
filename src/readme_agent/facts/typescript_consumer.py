"""Build a pinned TypeScript package and compile an exact isolated consumer."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from readme_agent.ecosystems.typescript_api_schema import (
    TypeScriptConsumerExampleV1,
    TypeScriptPackageLayoutV1,
    TypeScriptPublicApiSurfaceV1,
    TypeScriptPublicSymbolV1,
    TypeScriptSymbolKind,
)
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.typescript_consumer_schema import TypeScriptConsumerProofV1
from readme_agent.facts.typescript_toolchain import (
    TOOLCHAIN_LOCK,
    ensure_typescript_toolchain,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

_RESULT_PREFIX = "README_AGENT_TYPESCRIPT_CONSUMER="
_COPY_IGNORE = shutil.ignore_patterns(".git", "node_modules", "build", "dist", "coverage")
_DRIVER_PATH = Path(__file__).with_name("typescript_consumer_driver.js")
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]


def _example_imports_selected_symbols(example: TypeScriptConsumerExampleV1) -> None:
    escaped = re.escape(example.import_specifier)
    matches = re.findall(
        rf"import\s*\{{([^}}]+)\}}\s*from\s*['\"]{escaped}['\"]",
        example.code,
        flags=re.MULTILINE,
    )
    imported = {
        item.split(" as ", 1)[-1].strip()
        for group in matches
        for item in group.split(",")
        if item.strip()
    }
    roots = {symbol.split(".", 1)[0] for symbol in example.required_symbols}
    missing = sorted(roots - imported)
    unused = sorted(
        root for root in roots if len(re.findall(rf"\b{re.escape(root)}\b", example.code)) < 2
    )
    if missing or unused:
        raise ValueError(
            f"TypeScript example must import and use every selected symbol; "
            f"missing={missing}, unused={unused}"
        )


def _payload(result: IsolatedExecutionResultV1) -> dict[str, Any]:
    rows = [
        line.removeprefix(_RESULT_PREFIX)
        for line in result.stdout.splitlines()
        if line.startswith(_RESULT_PREFIX)
    ]
    if len(rows) != 1:
        return {}
    loaded = json.loads(rows[0])
    return loaded if isinstance(loaded, dict) else {}


def _surface(
    snapshot: RepositorySnapshotV1,
    package: TypeScriptPackageLayoutV1,
    example: TypeScriptConsumerExampleV1,
    payload: dict[str, Any],
) -> TypeScriptPublicApiSurfaceV1 | None:
    resolved = payload.get("resolvedDeclarationPath")
    compiler_version = payload.get("compilerVersion")
    symbols_payload = payload.get("symbols")
    if not isinstance(resolved, str) or not isinstance(compiler_version, str):
        return None
    if not isinstance(symbols_payload, list):
        return None
    symbols = [
        TypeScriptPublicSymbolV1(
            qualified_name=str(row["qualifiedName"]),
            export_name=str(row["exportName"]),
            member_name=str(row["memberName"]) if row.get("memberName") is not None else None,
            kind=cast(TypeScriptSymbolKind, str(row["kind"])),
            declaration_path=str(row["declarationPath"]),
            source_line=int(row["sourceLine"]),
            type_text=str(row["typeText"]) if row.get("typeText") is not None else None,
            readonly=bool(row.get("readonly", False)),
            compiler_resolved=bool(row.get("compilerResolved", False)),
        )
        for row in symbols_payload
        if isinstance(row, dict)
    ]
    digest = hashlib.sha256(
        json.dumps(symbols_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TypeScriptPublicApiSurfaceV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        package=package,
        resolved_import=example.import_specifier,
        resolved_declaration_path=resolved,
        symbols=symbols,
        compiler_version=compiler_version,
        source_sha256=digest,
    )


def prove_typescript_consumer(
    snapshot: RepositorySnapshotV1,
    package: TypeScriptPackageLayoutV1,
    example: TypeScriptConsumerExampleV1,
    *,
    executor: IsolatedExecutor = execute_isolated,
    toolchain_cache: Path | None = None,
) -> TypeScriptConsumerProofV1:
    """Build the immutable source and compile the consumer with a pinned compiler."""

    verify_repository_snapshot(snapshot)
    if package.canonical_import is None:
        patterns = ", ".join(package.unsupported_export_patterns) or "<none>"
        raise ValueError(
            "TypeScript package has no supported concrete export entry point; "
            f"unsupported patterns: {patterns}"
        )
    if package.canonical_import != example.import_specifier and example.import_specifier not in {
        entry.import_specifier for entry in package.entry_points
    }:
        raise ValueError("TypeScript example selects an undeclared or inaccessible package subpath")
    if package.build_config_path is None:
        raise ValueError("TypeScript package has no build configuration for isolated proof")
    _example_imports_selected_symbols(example)
    archives = ensure_typescript_toolchain(toolchain_cache)
    with tempfile.TemporaryDirectory(prefix="readme-agent-typescript-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        shutil.copytree(snapshot.root_path, workspace, ignore=_COPY_IGNORE)
        archive_root = workspace / ".readme-agent-toolchain-archives"
        archive_root.mkdir()
        for artifact in TOOLCHAIN_LOCK.artifacts:
            shutil.copy2(archives[artifact.name], archive_root / artifact.filename)
        shutil.copy2(_DRIVER_PATH, workspace / ".readme-agent-typescript-driver.js")
        (workspace / ".readme-agent-typescript-config.json").write_text(
            json.dumps(
                {
                    "package": {
                        "packageName": package.package_name,
                        "buildConfigPath": package.build_config_path,
                        "outputRoot": package.output_root,
                    },
                    "example": {
                        "code": example.code,
                        "importSpecifier": example.import_specifier,
                        "requiredSymbols": example.required_symbols,
                    },
                    "toolchain": TOOLCHAIN_LOCK.model_dump(mode="json"),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
            newline="\n",
        )
        request = IsolatedExecutionRequestV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            source_root=workspace,
            argv=["node", ".readme-agent-typescript-driver.js"],
            environment={"HOME": "/tmp"},
            policy=IsolatedExecutionPolicyV1(
                immutable_image=TOOLCHAIN_LOCK.immutable_image,
                timeout_seconds=300,
                memory_mebibytes=1024,
                pids_limit=96,
            ),
        )
        result = executor(request)
    verify_repository_snapshot(snapshot)
    payload = _payload(result)
    surface = _surface(snapshot, package, example, payload)
    available = {symbol.qualified_name for symbol in surface.symbols} if surface else set()
    verified = sorted(set(example.required_symbols) & available)
    missing = sorted(set(example.required_symbols) - available)
    diagnostics = [str(item) for item in payload.get("diagnostics", [])]
    artifact_hash = payload.get("builtArtifactSha256")
    accepted = (
        bool(payload.get("accepted"))
        and result.truth_eligible
        and result.return_code == 0
        and not missing
        and surface is not None
        and isinstance(artifact_hash, str)
    )
    return TypeScriptConsumerProofV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        package=package,
        example=example,
        toolchain=TOOLCHAIN_LOCK,
        surface=surface,
        built_artifact_sha256=artifact_hash if isinstance(artifact_hash, str) else None,
        verified_symbols=verified,
        missing_symbols=missing,
        diagnostics=diagnostics,
        isolated_execution=result,
        accepted=accepted,
    )
