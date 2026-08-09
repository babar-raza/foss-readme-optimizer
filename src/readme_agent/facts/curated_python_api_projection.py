"""Project complete typed Python API evidence into a bounded claim-useful view."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

from readme_agent.ecosystems.python_api_schema import (
    PublicApiSurfaceV1,
    PublicSymbolV1,
    PythonPackageLayoutV1,
)
from readme_agent.facts.curated_python_api_ast import (
    class_source_semantics,
    function_imports,
    member_return_annotation,
    member_surface,
    module_from_source,
    source_sha256,
)
from readme_agent.facts.curated_python_api_eligibility import (
    is_readme_presentable_symbol,
    presentation_exclusion,
)
from readme_agent.facts.curated_python_mcp import python_mcp_server

_LIMITS = {
    "modules": 16,
    "exports_per_module": 48,
    "classes": 96,
    "members_per_class": 24,
    "functions": 24,
    "json_bytes": 262_144,
}


def _distributed(symbol: PublicSymbolV1, layout: PythonPackageLayoutV1) -> bool:
    prefix = "" if layout.source_root == "." else f"{layout.source_root.rstrip('/')}/"
    relative = symbol.source_path.removeprefix(prefix)
    return any(
        relative == f"{package}.py" or relative.startswith(f"{package}/")
        for package in layout.package_paths
    )


def _module_source(root: Path, layout: PythonPackageLayoutV1, module: str) -> Path | None:
    source_root = root if layout.source_root == "." else root / layout.source_root
    package = source_root / Path(*module.split("."))
    return next(
        (path for path in (package / "__init__.py", package.with_suffix(".py")) if path.is_file()),
        None,
    )


def _preference_tier(symbol: PublicSymbolV1, canonical: str) -> tuple[object, ...]:
    return (
        symbol.import_module != canonical,
        not symbol.import_module.startswith(f"{canonical}."),
        len(symbol.import_module.split(".")),
    )


def _preferred(symbols: list[PublicSymbolV1], canonical: str) -> PublicSymbolV1:
    return min(
        symbols,
        key=lambda item: (
            *_preference_tier(item, canonical),
            item.import_module,
            item.qualified_name,
        ),
    )


def _definition(
    symbol: PublicSymbolV1, by_qualified_name: dict[str, PublicSymbolV1]
) -> PublicSymbolV1:
    current, seen = symbol, set()
    while current.reexported_from and current.reexported_from not in seen:
        seen.add(current.qualified_name)
        origin = by_qualified_name.get(current.reexported_from)
        if origin is None:
            break
        current = origin
    return current


def _modules(
    root: Path, layout: PythonPackageLayoutV1, top_level: list[PublicSymbolV1]
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, set[str]], list[str]]:
    exports: dict[str, set[str]] = {}
    for symbol in top_level:
        exports.setdefault(symbol.import_module, set()).add(symbol.name)
    ranked = sorted(
        exports,
        key=lambda module: (
            module != layout.canonical_import,
            not module.startswith(f"{layout.canonical_import}."),
            len(module.split(".")),
            module,
        ),
    )
    complete_rows: list[dict[str, object]] = []
    locations = [layout.manifest_path]
    for module in ranked:
        source = _module_source(root, layout, module)
        if source is None:
            source = root / min(
                symbol.source_path for symbol in top_level if symbol.import_module == module
            )
        source_path = source.relative_to(root).as_posix()
        complete_rows.append(
            {
                "module": module,
                "exports": sorted(exports[module]),
                "source_path": source_path,
                "source_sha256": source_sha256(source),
            }
        )
        locations.append(source_path)
    projected_rows = [
        {
            **row,
            "exports": cast(list[str], row["exports"])[: _LIMITS["exports_per_module"]],
        }
        for row in complete_rows[: _LIMITS["modules"]]
    ]
    return projected_rows, complete_rows, exports, locations


def _unambiguous_class(
    candidates: list[PublicSymbolV1], by_name: dict[str, PublicSymbolV1], canonical: str
) -> tuple[PublicSymbolV1, PublicSymbolV1] | None:
    best_rank = min(_preference_tier(item, canonical) for item in candidates)
    best = [item for item in candidates if _preference_tier(item, canonical) == best_rank]
    definitions = {_definition(item, by_name).qualified_name for item in best}
    if len(definitions) != 1:
        return None
    exposed = _preferred(best, canonical)
    return exposed, _definition(exposed, by_name)


def _members(
    symbols: list[PublicSymbolV1], definition: PublicSymbolV1, targets: set[str]
) -> list[PublicSymbolV1]:
    prefix = f"{definition.qualified_name}."
    return sorted(
        (
            item
            for item in symbols
            if item.qualified_name.startswith(prefix)
            and "." not in item.qualified_name.removeprefix(prefix)
            and item.kind in {"method", "property", "enum_member", "typed_field"}
        ),
        key=lambda item: (item.name.rsplit(".", 1)[-1] not in targets, item.qualified_name),
    )


def _classes(
    root: Path,
    layout: PythonPackageLayoutV1,
    symbols: list[PublicSymbolV1],
    top_level: list[PublicSymbolV1],
    by_name: dict[str, PublicSymbolV1],
    locations: list[str],
    targets: set[str],
    *,
    presentation_only: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]], set[str], dict[str, int]]:
    candidates: dict[str, list[PublicSymbolV1]] = {}
    for symbol in top_level:
        if symbol.kind in {"class", "enum"}:
            candidates.setdefault(symbol.name, []).append(symbol)
    resolved = [
        (name, pair, _members(symbols, pair[1], targets))
        for name, items in candidates.items()
        if (pair := _unambiguous_class(items, by_name, layout.canonical_import))
    ]
    resolved.sort(
        key=lambda item: (
            item[0] not in targets,
            item[1][0].import_module != layout.canonical_import,
            not item[1][0].import_module.startswith(f"{layout.canonical_import}."),
            -len(item[2]),
            item[0],
        )
    )
    resolved_by_name = {name: (pair, members) for name, pair, members in resolved}

    def bases(definition: PublicSymbolV1) -> list[str]:
        raw = class_source_semantics(root, definition).get("bases")
        return [str(item) for item in raw] if isinstance(raw, list) else []

    def inherited_members(
        definition: PublicSymbolV1,
        direct: list[PublicSymbolV1],
        visited: frozenset[str] = frozenset(),
    ) -> list[tuple[PublicSymbolV1, str]]:
        if definition.qualified_name in visited:
            return []
        visited = visited | {definition.qualified_name}
        inherited: list[tuple[PublicSymbolV1, str]] = []
        hidden = {item.name.rsplit(".", 1)[-1] for item in direct}
        for expression in bases(definition):
            base_name = str(expression).rsplit(".", 1)[-1]
            base = resolved_by_name.get(base_name)
            if base is None:
                continue
            (_exposed, base_definition), base_members = base
            for member in base_members:
                member_name = member.name.rsplit(".", 1)[-1]
                if member_name not in hidden:
                    inherited.append((member, base_name))
                    hidden.add(member_name)
            for member, owner in inherited_members(base_definition, base_members, visited):
                member_name = member.name.rsplit(".", 1)[-1]
                if member_name not in hidden:
                    inherited.append((member, owner))
                    hidden.add(member_name)
        return inherited

    def constructor(
        definition: PublicSymbolV1, visited: frozenset[str] = frozenset()
    ) -> dict[str, object] | None:
        if definition.qualified_name in visited:
            return None
        visited = visited | {definition.qualified_name}
        semantics = class_source_semantics(root, definition)
        direct = semantics.get("constructor")
        if isinstance(direct, dict):
            return {**direct, "declared_by": definition.name, "inherited": False}
        for expression in bases(definition):
            base_name = str(expression).rsplit(".", 1)[-1]
            base = resolved_by_name.get(base_name)
            if base is None:
                continue
            inherited = constructor(base[0][1], visited)
            if inherited is not None:
                return {**inherited, "inherited": True}
        return None

    complete_rows, keys = [], set()
    for name, (exposed, definition), members in resolved:
        if presentation_only and not is_readme_presentable_symbol(exposed):
            continue
        direct = [(member, name, False) for member in members]
        inherited = [
            (member, owner, True) for member, owner in inherited_members(definition, members)
        ]
        selected = direct + inherited
        semantics = class_source_semantics(root, definition)
        complete_rows.append(
            {
                "name": name,
                "module": exposed.import_module,
                "qualified_name": exposed.qualified_name,
                "bases": semantics.get("bases", []),
                "constructor": constructor(definition),
                "members": [
                    {
                        "name": member.name.rsplit(".", 1)[-1],
                        "kind": member.kind,
                        "surface": member_surface(root, member),
                        "return_annotation": member_return_annotation(root, member),
                        "declared_by": owner,
                        "inherited": is_inherited,
                        "source_path": member.source_path,
                        "source_sha256": source_sha256(root / member.source_path),
                        "line": member.source_line,
                    }
                    for member, owner, is_inherited in selected
                ],
                "source_path": definition.source_path,
                "source_sha256": source_sha256(root / definition.source_path),
                "line": definition.source_line,
            }
        )
        module = module_from_source(definition.source_path, layout.source_root)
        if module:
            keys.add(f"{module}:{name}")
        locations.extend([definition.source_path, *(item.source_path for item, _, _ in selected)])
    projected_rows = [
        {
            **row,
            "members": cast(list[dict[str, object]], row["members"])[
                : _LIMITS["members_per_class"]
            ],
        }
        for row in complete_rows[: _LIMITS["classes"]]
    ]
    stats = {
        "classes": len(candidates),
        "ambiguous_classes": len(candidates) - len(resolved),
        "max_members": max((len(item[2]) for item in resolved), default=0),
        "readme_target_classes": sum(name in targets for name in candidates),
        "projected_readme_target_classes": sum(row["name"] in targets for row in projected_rows),
    }
    return projected_rows, complete_rows, keys, stats


def _functions(
    root: Path,
    layout: PythonPackageLayoutV1,
    top_level: list[PublicSymbolV1],
    class_keys: set[str],
    locations: list[str],
    *,
    presentation_only: bool = False,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    for definition in sorted(
        (item for item in top_level if item.kind == "function"),
        key=lambda item: item.qualified_name,
    ):
        if not definition.annotation or not definition.annotation.isidentifier():
            continue
        module = module_from_source(definition.source_path, layout.source_root)
        if module is None:
            continue
        returned = function_imports(root / definition.source_path, module).get(
            definition.annotation, f"{module}:{definition.annotation}"
        )
        if returned not in class_keys:
            continue
        aliases = [item for item in top_level if item.reexported_from == definition.qualified_name]
        exposed = _preferred(aliases or [definition], layout.canonical_import)
        if presentation_only and not is_readme_presentable_symbol(exposed):
            continue
        rows.append(
            {
                "module": exposed.import_module,
                "name": exposed.name,
                "return_class": returned,
                "source_path": definition.source_path,
                "source_sha256": source_sha256(root / definition.source_path),
            }
        )
        locations.append(definition.source_path)
    return rows[: _LIMITS["functions"]], rows


def _coordinate_catalog(value: dict[str, object]) -> dict[str, object]:
    """Return an inspectable, hash-addressed proof catalog outside the agent projection."""

    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        **value,
        "content_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _bounded_projection_bytes(value: dict[str, object]) -> int:
    projected = {key: item for key, item in value.items() if key != "coordinate_catalog"}
    return len(json.dumps(projected, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def project_public_surface(
    root: Path,
    layout: PythonPackageLayoutV1,
    surface: PublicApiSurfaceV1,
    readme_targets: set[str] | None = None,
) -> tuple[dict[str, object], list[str]] | None:
    """Return a deterministic bounded projection while retaining a hash of full evidence."""

    targets = readme_targets or set()
    symbols = [item for item in surface.symbols if _distributed(item, layout)]
    top_level = [
        item
        for item in symbols
        if item.name
        and "." not in item.name
        and item.kind in {"module", "class", "enum", "function"}
    ]
    presentable_top_level = [item for item in top_level if is_readme_presentable_symbol(item)]
    modules, presentable_modules, exports, locations = _modules(root, layout, presentable_top_level)
    if not top_level:
        return None
    by_name = {item.qualified_name: item for item in symbols}
    classes, _presentable_classes, keys, _presentable_stats = _classes(
        root,
        layout,
        symbols,
        top_level,
        by_name,
        locations,
        targets,
        presentation_only=True,
    )
    functions, _presentable_functions = _functions(
        root,
        layout,
        top_level,
        keys,
        locations,
        presentation_only=True,
    )
    _all_modules, complete_modules, complete_exports, catalog_locations = _modules(
        root, layout, top_level
    )
    _all_classes, complete_classes, complete_keys, stats = _classes(
        root,
        layout,
        symbols,
        top_level,
        by_name,
        catalog_locations,
        targets,
    )
    _all_functions, complete_functions = _functions(
        root, layout, top_level, complete_keys, catalog_locations
    )
    locations.extend(catalog_locations)
    presented_definitions = {
        _definition(item, by_name).qualified_name for item in presentable_top_level
    }
    excluded = [
        presentation_exclusion(item)
        for item in top_level
        if not is_readme_presentable_symbol(item)
        and item.qualified_name not in presented_definitions
    ]
    coordinate_catalog = _coordinate_catalog(
        {
            "schema_version": 1,
            "public_api_source_sha256": surface.source_sha256,
            "modules": complete_modules,
            "classes": complete_classes,
            "functions": complete_functions,
            "presentation_exclusions": excluded,
        }
    )
    package_namespaces = sorted(
        str(row["module"])
        for row in presentable_modules
        if str(row["source_path"]).endswith("/__init__.py") or row["source_path"] == "__init__.py"
    )
    value: dict[str, object] = {
        "modules": modules,
        "package_namespaces": package_namespaces,
        "classes": classes,
        "functions": functions,
        "package": layout.model_dump(mode="json"),
        "public_api_source_sha256": surface.source_sha256,
        "unresolved_reexports": surface.unresolved_reexports,
        "inventory_counts": {
            "typed_symbols": len(surface.symbols),
            "distributed_symbols": len(symbols),
            "modules": len(complete_exports),
            "presentation_eligible_modules": len(exports),
            "presentation_excluded_symbols": len(excluded),
            **stats,
        },
        "projection_limits": _LIMITS,
        "coordinate_catalog": coordinate_catalog,
        "projection_truncated": (
            len(exports) > _LIMITS["modules"]
            or any(len(items) > _LIMITS["exports_per_module"] for items in exports.values())
            or stats["classes"] > _LIMITS["classes"]
            or stats["max_members"] > _LIMITS["members_per_class"]
        ),
    }
    if (mcp := python_mcp_server(root)) is not None:
        value["mcp_server"], mcp_locations = mcp
        locations.extend(mcp_locations)
    while _bounded_projection_bytes(value) > _LIMITS["json_bytes"]:
        value["projection_truncated"] = True
        if classes:
            classes.pop()
        elif functions:
            functions.pop()
        elif len(modules) > 1:
            modules.pop()
        else:
            return None
    return value, sorted(set(locations))
