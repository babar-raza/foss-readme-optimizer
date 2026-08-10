"""Render verified public API inventories as namespace-scoped tables."""

from __future__ import annotations

import re
from typing import Any

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_api_descriptions import (
    describe_api_export,
    namespace_display_name,
)


def _accepted_api_value(facts: ProductFactsV2) -> dict[str, Any] | None:
    try:
        fact = facts.selected_fact("api.public_surface")
    except KeyError:
        return None
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return None
    return fact.value


def _table_cell(value: object) -> str:
    return " ".join(str(value).split()).replace("|", "\\|")


def _class_indexes(
    value: dict[str, Any],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    exact: dict[tuple[str, str], dict[str, Any]] = {}
    by_name: dict[str, list[dict[str, Any]]] = {}
    classes = value.get("classes")
    if not isinstance(classes, list):
        return exact, by_name
    for item in classes:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        module = str(item.get("module") or "").strip()
        if not name:
            continue
        by_name.setdefault(name, []).append(item)
        if module:
            exact[(module, name)] = item
    return exact, by_name


def _complete_catalog(value: dict[str, Any]) -> dict[str, Any]:
    """Prefer the complete evidence catalog over the bounded planning projection."""

    catalog = value.get("coordinate_catalog")
    return catalog if isinstance(catalog, dict) else value


def _excluded_exports(value: dict[str, Any]) -> set[tuple[str, str]]:
    catalog = value.get("coordinate_catalog")
    source = catalog if isinstance(catalog, dict) else value
    exclusions = source.get("presentation_exclusions")
    if not isinstance(exclusions, list):
        return set()
    return {
        (str(item.get("import_module") or "").strip(), str(item.get("name") or "").strip())
        for item in exclusions
        if isinstance(item, dict)
        and str(item.get("import_module") or "").strip()
        and str(item.get("name") or "").strip()
    }


def _function_keys(value: dict[str, Any]) -> set[tuple[str, str]]:
    functions = value.get("functions")
    if not isinstance(functions, list):
        return set()
    return {
        (str(item.get("module") or "").strip(), str(item.get("name") or "").strip())
        for item in functions
        if isinstance(item, dict)
        and str(item.get("module") or "").strip()
        and str(item.get("name") or "").strip()
    }


def _is_namespace_alias(
    module: str,
    export: str,
    *,
    namespaces: set[str],
    class_keys: set[tuple[str, str]],
    function_keys: set[tuple[str, str]],
) -> bool:
    """Identify exported child modules without guessing that all lowercase exports are modules."""

    return bool(
        (module, export) not in class_keys
        and (module, export) not in function_keys
        and f"{module}.{export}" in namespaces
    )


def _is_single_type_wrapper_namespace(
    module: str,
    exports: list[object],
    classes_by_name: dict[str, list[dict[str, Any]]],
) -> bool:
    """Reject generated implementation modules that only wrap one canonically exported type."""

    if len(exports) != 1:
        return False
    export = str(exports[0]).strip()
    if not export or module.rsplit(".", 1)[-1] != export:
        return False
    candidates = classes_by_name.get(export, [])
    return any(str(item.get("module") or "").strip() != module for item in candidates)


def _class_surface(name: str, item: dict[str, Any]) -> str:
    constructor = item.get("constructor")
    if isinstance(constructor, dict):
        surface = " ".join(str(constructor.get("surface") or "").split())
        if surface:
            return surface
    return name


def _namespace_table(
    module: str,
    exports: list[object],
    exact_classes: dict[tuple[str, str], dict[str, Any]],
    classes_by_name: dict[str, list[dict[str, Any]]],
    primary_export_modules: dict[str, str],
    family: str,
) -> tuple[list[str], int]:
    display_name = namespace_display_name(module, family)
    rows: list[str] = [
        f"### {display_name} Namespace (`{_table_cell(module)}`)",
        "",
        "| Type | Description |",
        "| --- | --- |",
    ]
    count = 0
    for raw_export in exports:
        name = str(raw_export).strip()
        if not name:
            continue
        candidates = classes_by_name.get(name, [])
        item = exact_classes.get((module, name)) or (candidates[0] if candidates else None)
        canonical_module = str(item.get("module") or "").strip() if item is not None else ""
        primary_module = canonical_module or primary_export_modules.get(name, module)
        if primary_module != module:
            description = (
                f"The `{_table_cell(module)}` namespace re-exports `{name}` from the primary "
                f"`{_table_cell(primary_module)}` namespace."
            )
        else:
            description = describe_api_export(item, module=module, name=name, family=family)
        identifier = _class_surface(name, item) if item is not None else name
        rows.append(f"| `{_table_cell(identifier)}` | {description} |")
        count += 1
    return rows, count


def _product_family(facts: ProductFactsV2) -> str:
    value = facts.selected_fact("product.identity").value
    if isinstance(value, dict) and str(value.get("family") or "").strip():
        return str(value["family"]).strip()
    identity = visitor_fact_render_view(facts, "product.identity")
    phrase = identity.phrases[0] if identity is not None and identity.phrases else ""
    match = re.match(r"Aspose\.([^ ]+)", phrase)
    if match is not None:
        return match.group(1)
    return ""


def api_reference_markdown(facts: ProductFactsV2) -> str | None:
    """Render every verified namespace as one Type/Description table."""

    value = _accepted_api_value(facts)
    if value is None:
        return None
    complete = _complete_catalog(value)
    modules = value.get("modules")
    modules = modules if isinstance(modules, list) else []
    exact_classes, classes_by_name = _class_indexes(complete)
    family = _product_family(facts)
    body: list[str] = []
    entry_count = 0
    namespace_count = 0
    namespace_exports: dict[str, list[object]] = {}
    excluded = _excluded_exports(value)
    for module in modules:
        if not isinstance(module, dict):
            continue
        name = str(module.get("module") or "").strip()
        exports = module.get("exports")
        if not name or not isinstance(exports, list):
            continue
        selected = namespace_exports.setdefault(name, [])
        for export in exports:
            if (name, str(export).strip()) not in excluded and export not in selected:
                selected.append(export)
    projected_namespaces = set(namespace_exports)
    package_namespaces = value.get("package_namespaces")
    if isinstance(package_namespaces, list):
        projected_namespaces.update(
            str(item).strip() for item in package_namespaces if str(item).strip()
        )
    # Some collectors provide the class inventory before a separate module
    # export index. A class with an explicit module is still sufficient
    # repository evidence for one namespace-scoped public API table.
    classes = complete.get("classes")
    if isinstance(classes, list):
        for item in classes:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            module = str(item.get("module") or "").strip()
            if (
                name
                and module
                and module in projected_namespaces
                and (module, name) not in excluded
            ):
                selected = namespace_exports.setdefault(module, [])
                if name not in selected:
                    selected.append(name)
    namespaces = set(namespace_exports)
    if isinstance(package_namespaces, list):
        namespaces.update(str(item).strip() for item in package_namespaces if str(item).strip())
    class_keys = set(exact_classes)
    function_keys = _function_keys(complete)
    namespace_exports = {
        module: [
            export
            for export in exports
            if not str(export).strip()[:1].islower()
            if (module, str(export).strip()) not in function_keys
            if not _is_namespace_alias(
                module,
                str(export).strip(),
                namespaces=namespaces,
                class_keys=class_keys,
                function_keys=function_keys,
            )
        ]
        for module, exports in namespace_exports.items()
        if not _is_single_type_wrapper_namespace(module, exports, classes_by_name)
    }
    primary_export_modules = {
        str(export).strip(): module
        for module, exports in reversed(list(namespace_exports.items()))
        for export in reversed(exports)
        if str(export).strip()
    }
    for name, exports in namespace_exports.items():
        table, count = _namespace_table(
            name,
            exports,
            exact_classes,
            classes_by_name,
            primary_export_modules,
            family,
        )
        if count == 0:
            continue
        if body:
            body.append("")
        body.extend(table)
        entry_count += count
        namespace_count += 1
    if not body:
        return None
    namespace_inventory = (
        [str(namespace).strip() for namespace in package_namespaces if str(namespace).strip()]
        if isinstance(package_namespaces, list)
        else []
    )
    namespace_context = ""
    if namespace_inventory:
        rendered_namespaces = ", ".join(
            f"`{_table_cell(namespace)}`" for namespace in namespace_inventory
        )
        namespace_context = f" Package namespaces include {rendered_namespaces}."
    details = "\n".join(
        [
            "<details>",
            "<summary>View public API by namespace</summary>",
            "",
            *body,
            "",
            "</details>",
        ]
    )
    return (
        f"The package documents {entry_count} public types across "
        f"{namespace_count} namespaces.{namespace_context} See the complete API reference under "
        f"Documentation and Resources for members, signatures, and inherited APIs.\n\n{details}"
    )


__all__ = ["api_reference_markdown"]
