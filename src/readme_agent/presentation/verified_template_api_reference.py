"""Render verified public API inventories as namespace-scoped tables."""

from __future__ import annotations

import re
from typing import Any

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.public_text import canonicalize_abbreviations


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


_LOW_VALUE_MEMBERS = {
    "Count",
    "Current",
    "Document",
    "FirstChild",
    "GetEnumerator",
    "IsReadOnly",
    "LastChild",
    "ParentNode",
}

_VERB_PHRASES = {
    "accept": "traverse with a visitor",
    "append": "append content",
    "clear": "clear content",
    "clone": "clone content",
    "copy": "copy content",
    "create": "create values",
    "default": "create default values",
    "detect": "detect changes",
    "get": "retrieve data",
    "index": "find content",
    "insert": "insert content",
    "load": "load content",
    "open": "open content",
    "read": "read content",
    "remove": "remove content",
    "replace": "replace content",
    "save": "save output",
    "set": "set values",
    "visit": "visit content",
    "write": "write output",
}

_EXACT_MEMBER_PHRASES = {
    "Accept": "traverse with a visitor",
    "GetChildNodes": "retrieve child nodes",
    "Save": "save document output",
    "SetLicense": "configure package licensing",
    "SetMeteredKey": "configure metered licensing keys",
}


def _human_name(value: str) -> str:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    expanded = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", expanded).replace("_", " ")
    return " ".join(expanded.split()).casefold()


def _member_rows(item: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    members = item.get("members")
    if not isinstance(members, list):
        return []
    rows: list[tuple[int, dict[str, Any]]] = []
    for member in members:
        if not isinstance(member, dict):
            continue
        name = str(member.get("name") or "").strip()
        if not name:
            continue
        score = 0
        if member.get("inherited") is True:
            score += 20
        if str(member.get("kind") or "") != "method":
            score += 10
        if name in _LOW_VALUE_MEMBERS:
            score += 30
        if name.endswith("End"):
            score += 5
        rows.append((score, member))
    return sorted(rows, key=lambda row: (row[0], str(row[1]["name"]).casefold()))


def _series(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _member_phrase(member: dict[str, Any]) -> str:
    name = str(member.get("name") or "").strip()
    if name in _EXACT_MEMBER_PHRASES:
        return _EXACT_MEMBER_PHRASES[name]
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ").split()
    if str(member.get("kind") or "") != "method" or not words:
        return "access to " + _human_name(name)
    verb = words[0].casefold()
    remainder = " ".join(words[1:]).casefold()
    if verb == "append" and remainder.startswith("child"):
        return "append child nodes"
    if verb == "get" and remainder:
        return "retrieve " + remainder
    if verb == "detect" and remainder:
        return "detect " + remainder
    if verb == "visit" and remainder:
        return "visit " + re.sub(r"\s+(?:start|end)$", "", remainder)
    if verb in {"create", "default", "replace", "set"} and remainder:
        prefix = {
            "create": "create",
            "default": "create default",
            "replace": "replace",
            "set": "set",
        }[verb]
        return f"{prefix} {remainder}"
    return _VERB_PHRASES.get(verb, verb)


def _member_summary(item: dict[str, Any], *, limit: int = 3) -> tuple[str, int]:
    rows = _member_rows(item)
    selected: list[str] = []
    for _score, member in rows:
        phrase = _member_phrase(member)
        if phrase not in selected:
            selected.append(phrase)
        if len(selected) == limit:
            break
    return _series(selected), max(0, len(rows) - len(selected))


def _article(value: str) -> str:
    return "an" if value[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"


def _class_description(item: dict[str, Any] | None, *, module: str, name: str) -> str:
    if item is None:
        if name[:1].islower():
            return f"Public function for {_human_name(name)} operations."
        return f"`{name}` is a verified public type exported by the `{module}` namespace."
    bases = [str(base).strip() for base in item.get("bases", []) if str(base).strip()]
    if name.endswith("Exception") or any(base.endswith("Exception") for base in bases):
        condition = _human_name(name.removesuffix("Exception")).replace(" file format", " format")
        inheritance = f"; derives from `{_table_cell(bases[0])}`" if bases else ""
        return f"Signals {_article(condition)} {condition} condition{inheritance}."
    if module.endswith(".enums") or any(base in {"Enum", "IntEnum", "StrEnum"} for base in bases):
        values = [
            f"`{_table_cell(str(member['name']))}`" for _score, member in _member_rows(item)[:3]
        ]
        detail = f" Values include {_series(values)}" if values else ""
        remaining = max(0, len(_member_rows(item)) - len(values))
        if remaining:
            detail += f" and {remaining} more"
        return f"Enumerates {_human_name(name)} values.{detail}".rstrip() + ("." if detail else "")
    summary, remaining = _member_summary(item)
    human_name = _human_name(name)
    if not summary and not bases:
        return f"`{name}` is a verified public type exported by the `{module}` namespace."
    description = human_name.capitalize()
    if summary:
        description += f": {summary}"
    if bases:
        description += ". Inherits from " + ", ".join(f"`{_table_cell(base)}`" for base in bases)
    if remaining:
        description += f". Includes {remaining} additional member"
        if remaining != 1:
            description += "s"
    description += "."
    if len(description.rstrip(".")) < 24:
        return (
            f"`{name}` exposes the verified public `{summary}` operation "
            f"in the `{module}` namespace."
        )
    return description


def _namespace_display_name(module: str, family: str) -> str:
    """Humanize dotted and underscore-root Python namespaces without duplicating family names."""

    def display_part(value: str) -> str:
        words = [
            canonicalize_abbreviations(word[:1].upper() + word[1:])
            for word in value.split("_")
            if word
        ]
        return " ".join(words)

    parts = module.split(".")
    rendered_parts: list[str] = []
    first = parts[0]
    start = 1
    if first.casefold() == "aspose":
        rendered_parts.append("Aspose")
        if len(parts) > 1:
            rendered_parts.append(canonicalize_abbreviations(family or parts[1]))
            start = 2
    elif first.casefold().startswith("aspose_"):
        suffix = first[len("aspose_") :]
        rendered_parts.extend(
            ["Aspose", canonicalize_abbreviations(family or display_part(suffix))]
        )
    else:
        rendered_parts.append(display_part(first))
    for part in parts[start:]:
        rendered_parts.append(display_part(part))
    return ".".join(rendered_parts)


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


def _namespace_table(
    module: str,
    exports: list[object],
    exact_classes: dict[tuple[str, str], dict[str, Any]],
    classes_by_name: dict[str, list[dict[str, Any]]],
    primary_export_modules: dict[str, str],
    family: str,
) -> tuple[list[str], int]:
    display_name = _namespace_display_name(module, family)
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
            description = _class_description(item, module=module, name=name)
        rows.append(f"| `{_table_cell(name)}` | {description} |")
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
    modules = value.get("modules")
    modules = modules if isinstance(modules, list) else []
    exact_classes, classes_by_name = _class_indexes(value)
    family = _product_family(facts)
    body: list[str] = []
    export_count = 0
    namespace_count = 0
    namespace_exports: dict[str, list[object]] = {}
    for module in modules:
        if not isinstance(module, dict):
            continue
        name = str(module.get("module") or "").strip()
        exports = module.get("exports")
        if not name or not isinstance(exports, list):
            continue
        selected = namespace_exports.setdefault(name, [])
        for export in exports:
            if export not in selected:
                selected.append(export)
    # Some collectors provide the class inventory before a separate module
    # export index. A class with an explicit module is still sufficient
    # repository evidence for one namespace-scoped public API table.
    classes = value.get("classes")
    if isinstance(classes, list):
        for item in classes:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            module = str(item.get("module") or "").strip()
            if name and module:
                selected = namespace_exports.setdefault(module, [])
                if name not in selected:
                    selected.append(name)
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
        export_count += count
        namespace_count += 1
    if not body:
        return None
    package_namespaces = value.get("package_namespaces")
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
        f"The package declares {export_count} public exports across "
        f"{namespace_count} export namespaces.{namespace_context}\n\n{details}"
    )


__all__ = ["api_reference_markdown"]
