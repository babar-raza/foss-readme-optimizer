"""Resolve Rust modules, re-exports, public types, members, traits, and docs."""

from __future__ import annotations

import hashlib
from importlib.metadata import version
from pathlib import Path

from readme_agent.ecosystems.rust_api_schema import (
    RustModuleV1,
    RustPackageLayoutV1,
    RustPublicApiSurfaceV1,
    RustPublicSymbolV1,
    RustVisibilityEvidence,
)
from readme_agent.ecosystems.rust_package_layout import inspect_rust_package_layout
from readme_agent.ecosystems.rust_snippets import extract_rust_snippets
from readme_agent.ecosystems.rust_symbol_extraction import (
    RustDefinition,
    associate_rust_implementations,
    extract_rust_definitions,
)
from readme_agent.ecosystems.rust_syntax import (
    RustSourceModule,
    load_rust_modules,
    top_level_nodes,
)
from readme_agent.ecosystems.rust_use_resolution import (
    RustUseLeaf,
    absolute_source_parts,
    public_use_leaves,
)


def _relative(path: Path, repository_root: Path) -> str:
    return path.relative_to(repository_root.resolve()).as_posix()


def _use_records(modules: list[RustSourceModule]) -> dict[tuple[str, ...], list[RustUseLeaf]]:
    records: dict[tuple[str, ...], list[RustUseLeaf]] = {}
    for module in modules:
        records[module.module] = [
            leaf
            for node in top_level_nodes(module)
            if node.type == "use_declaration"
            for leaf in public_use_leaves(node, module.source)
        ]
    return records


def _exports(
    modules: list[RustSourceModule],
    definitions: dict[tuple[str, ...], RustDefinition],
) -> dict[tuple[str, ...], dict[str, tuple[str, ...]]]:
    exports: dict[tuple[str, ...], dict[str, tuple[str, ...]]] = {
        module.module: {} for module in modules
    }
    for key, definition in definitions.items():
        exports[definition.module.module][definition.name] = key
    use_records = _use_records(modules)
    for _ in range(max(1, len(modules) * 3)):
        changed = False
        for module_path, leaves in use_records.items():
            for leaf in leaves:
                absolute = absolute_source_parts(module_path, leaf.source_parts)
                if leaf.wildcard:
                    source_exports = exports.get(absolute, {})
                    for name, key in source_exports.items():
                        if exports[module_path].get(name) != key:
                            exports[module_path][name] = key
                            changed = True
                    continue
                if not absolute:
                    continue
                source_module, source_name = absolute[:-1], absolute[-1]
                resolved: tuple[str, ...] | None
                if absolute in definitions:
                    resolved = absolute
                else:
                    resolved = exports.get(source_module, {}).get(source_name)
                if resolved and exports[module_path].get(leaf.exported_name) != resolved:
                    exports[module_path][leaf.exported_name] = resolved
                    changed = True
        if not changed:
            break
    return exports


def _module_is_public(
    module_path: tuple[str, ...],
    modules: dict[tuple[str, ...], RustSourceModule],
) -> bool:
    return all(
        modules[module_path[:index]].public_from_parent for index in range(1, len(module_path) + 1)
    )


def _symbol_records(
    repository_root: Path,
    package: RustPackageLayoutV1,
    modules: list[RustSourceModule],
    definitions: dict[tuple[str, ...], RustDefinition],
    exports: dict[tuple[str, ...], dict[str, tuple[str, ...]]],
) -> list[RustPublicSymbolV1]:
    module_map = {module.module: module for module in modules}
    symbols: list[RustPublicSymbolV1] = []
    for module_path, names in sorted(exports.items()):
        if not _module_is_public(module_path, module_map):
            continue
        for exported_name, key in sorted(names.items()):
            definition = definitions[key]
            import_parts = [package.crate_name, *module_path, exported_name]
            import_path = "::".join(import_parts)
            reexported = key != (*module_path, exported_name)
            evidence: RustVisibilityEvidence = "public_reexport" if reexported else "bare_pub"
            symbols.append(
                RustPublicSymbolV1(
                    qualified_name=import_path,
                    import_path=import_path,
                    name=exported_name,
                    kind=definition.kind,
                    visibility_evidence=evidence,
                    declaration_path=_relative(definition.module.source_path, repository_root),
                    source_line=definition.node.start_point.row + 1,
                    type_text=definition.type_text,
                    rustdoc=definition.docs,
                    derives=definition.derive_traits,
                    supertraits=definition.supertraits,
                    implemented_traits=sorted(definition.implemented_traits),
                )
            )
            for member in definition.members:
                member_module: RustSourceModule = member["module"]
                symbols.append(
                    RustPublicSymbolV1(
                        qualified_name=f"{import_path}.{member['name']}",
                        import_path=import_path,
                        name=member["name"],
                        parent_name=exported_name,
                        kind=member["kind"],
                        visibility_evidence="public_parent",
                        declaration_path=_relative(member_module.source_path, repository_root),
                        source_line=member["node"].start_point.row + 1,
                        type_text=member["type_text"],
                        rustdoc=member["rustdoc"],
                    )
                )
    unique = {symbol.qualified_name: symbol for symbol in symbols}
    return [unique[name] for name in sorted(unique)]


def inspect_rust_public_api(
    repository_root: Path,
    *,
    org_repo: str,
    source_revision: str,
) -> RustPublicApiSurfaceV1:
    """Return the syntax-resolved, crate-reachable public Rust API."""

    package = inspect_rust_package_layout(repository_root)
    modules = load_rust_modules(repository_root / package.lib_path)
    definitions = extract_rust_definitions(modules)
    associate_rust_implementations(modules, definitions)
    exports = _exports(modules, definitions)
    source_hash = hashlib.sha256(
        "".join(
            f"{module.source_path.as_posix()}:{hashlib.sha256(module.source).hexdigest()}\n"
            for module in modules
        ).encode("utf-8")
    ).hexdigest()
    return RustPublicApiSurfaceV1(
        org_repo=org_repo,
        source_revision=source_revision,
        package=package,
        modules=[
            RustModuleV1(
                module_path="::".join((package.crate_name, *module.module)),
                source_path=_relative(module.source_path, repository_root),
                public_from_parent=module.public_from_parent,
                path_attribute=module.path_attribute,
            )
            for module in modules
        ],
        symbols=_symbol_records(
            repository_root,
            package,
            modules,
            definitions,
            exports,
        ),
        snippets=extract_rust_snippets(repository_root, package, modules),
        parser=f"tree-sitter@{version('tree-sitter')}+tree-sitter-rust@"
        f"{version('tree-sitter-rust')}",
        source_sha256=source_hash,
    )
