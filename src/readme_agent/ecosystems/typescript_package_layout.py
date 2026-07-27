"""Resolve TypeScript package entry points from package.json and tsconfig."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from readme_agent.ecosystems.typescript_api_schema import (
    TypeScriptDeclaredBy,
    TypeScriptEntryPointV1,
    TypeScriptPackageLayoutV1,
)


def _target_paths(target: Any) -> tuple[str | None, str | None, list[str]]:
    if isinstance(target, str):
        return None, target, ["default"]
    if isinstance(target, list):
        for index, item in enumerate(target):
            candidate_declaration, candidate_runtime, candidate_conditions = _target_paths(item)
            if candidate_declaration is not None or candidate_runtime is not None:
                return (
                    candidate_declaration,
                    candidate_runtime,
                    [f"array:{index}", *candidate_conditions],
                )
        return None, None, []
    if not isinstance(target, dict):
        return None, None, []
    declaration: str | None = None
    runtime: str | None = None
    conditions: list[str] = []
    for condition, value in target.items():
        nested_declaration, nested_runtime, nested_conditions = _target_paths(value)
        conditions.extend([str(condition), *nested_conditions])
        if condition == "types" and isinstance(value, str):
            declaration = value
            continue
        if condition in {"import", "require", "node", "default"} and isinstance(value, str):
            runtime = runtime or value
            continue
        if declaration is None and nested_declaration is not None:
            declaration = nested_declaration
        if runtime is None and nested_runtime is not None:
            runtime = nested_runtime
    return declaration, runtime, sorted(set(conditions))


def _specifier(package_name: str, subpath: str) -> str:
    return package_name if subpath == "." else f"{package_name}/{subpath.removeprefix('./')}"


def _declared_entries(
    package_name: str,
    manifest: dict[str, Any],
) -> tuple[list[TypeScriptEntryPointV1], list[str]]:
    exports = manifest.get("exports")
    entries: list[TypeScriptEntryPointV1] = []
    unsupported: list[str] = []
    if isinstance(exports, (str, list)):
        declaration, runtime, conditions = _target_paths(exports)
        entries.append(
            TypeScriptEntryPointV1(
                import_specifier=package_name,
                subpath=".",
                declaration_path=declaration,
                runtime_path=runtime,
                declared_by="exports",
                conditions=conditions,
                declaration_preferred=declaration is not None,
            )
        )
    elif isinstance(exports, dict):
        targets = exports if any(str(key).startswith(".") for key in exports) else {".": exports}
        for subpath, target in sorted(targets.items()):
            if "*" in str(subpath):
                unsupported.append(str(subpath))
                continue
            declaration, runtime, conditions = _target_paths(target)
            entries.append(
                TypeScriptEntryPointV1(
                    import_specifier=_specifier(package_name, str(subpath)),
                    subpath=str(subpath),
                    declaration_path=declaration,
                    runtime_path=runtime,
                    declared_by="exports",
                    conditions=conditions,
                    declaration_preferred=declaration is not None,
                )
            )
    if entries or exports is not None:
        return entries, unsupported
    declaration = manifest.get("types") or manifest.get("typings")
    runtime = manifest.get("module") or manifest.get("main")
    declared_by: TypeScriptDeclaredBy = (
        "types" if declaration else "module" if manifest.get("module") else "main"
    )
    return (
        [
            TypeScriptEntryPointV1(
                import_specifier=package_name,
                subpath=".",
                declaration_path=str(declaration) if declaration else None,
                runtime_path=str(runtime) if runtime else None,
                declared_by=declared_by,
                declaration_preferred=bool(declaration),
            )
        ],
        unsupported,
    )


def _legacy_entries(
    repository_root: Path,
    package_name: str,
    source_root: Path,
    output_root: Path,
) -> list[TypeScriptEntryPointV1]:
    entries: list[TypeScriptEntryPointV1] = []
    for source_entry in sorted(source_root.rglob("index.ts")):
        relative = source_entry.relative_to(source_root)
        declaration = (output_root / relative).with_suffix(".d.ts")
        runtime = (output_root / relative).with_suffix(".js")
        subpath = declaration.as_posix().removesuffix(".d.ts")
        if subpath.endswith("/index"):
            subpath = subpath[: -len("/index")]
        entries.append(
            TypeScriptEntryPointV1(
                import_specifier=f"{package_name}/{subpath}",
                subpath=f"./{subpath}",
                declaration_path=declaration.as_posix(),
                runtime_path=runtime.as_posix(),
                source_entry_path=source_entry.relative_to(repository_root).as_posix(),
                declared_by="legacy_index",
                declaration_preferred=True,
            )
        )
    return entries


def inspect_typescript_package_layout(repository_root: Path) -> TypeScriptPackageLayoutV1:
    """Return deterministic package/export candidates without executing repository code."""

    manifest_path = repository_root / "package.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    package_name = manifest.get("name")
    if not isinstance(package_name, str) or not package_name:
        raise ValueError("TypeScript package.json has no package name")
    config_path = repository_root / "tsconfig.json"
    config: dict[str, Any] = {}
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8", errors="strict"))
    options = config.get("compilerOptions", {}) if isinstance(config, dict) else {}
    source_root = Path(str(options.get("rootDir") or "src"))
    if not (repository_root / source_root).is_dir():
        source_root = Path(".")
    output_root = Path(str(options.get("outDir") or "dist"))
    entries, unsupported = _declared_entries(package_name, manifest)
    exports_restrict = "exports" in manifest
    if not exports_restrict:
        existing = {entry.import_specifier for entry in entries}
        entries.extend(
            entry
            for entry in _legacy_entries(
                repository_root,
                package_name,
                repository_root / source_root,
                output_root,
            )
            if entry.import_specifier not in existing
        )
    candidates = [entry for entry in entries if entry.source_entry_path]
    canonical = None
    if entries:
        canonical = (
            min(
                candidates,
                key=lambda entry: (entry.import_specifier.count("/"), entry.import_specifier),
            )
            if candidates
            else entries[0]
        )
    digest = hashlib.sha256()
    for path in [manifest_path, config_path]:
        if path.is_file():
            digest.update(path.relative_to(repository_root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    for entry in entries:
        if entry.source_entry_path:
            path = repository_root / entry.source_entry_path
            digest.update(entry.source_entry_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return TypeScriptPackageLayoutV1(
        manifest_path="package.json",
        package_name=package_name,
        version=str(manifest["version"]) if manifest.get("version") else None,
        build_config_path="tsconfig.json" if config_path.is_file() else None,
        source_root=source_root.as_posix(),
        output_root=output_root.as_posix(),
        entry_points=entries,
        canonical_import=canonical.import_specifier if canonical else None,
        exports_restrict_subpaths=exports_restrict,
        unsupported_export_patterns=unsupported,
        source_sha256=digest.hexdigest(),
    )
