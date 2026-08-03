"""Corroborate primary Python format directions against executable source structure."""

from __future__ import annotations

import ast
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1


def _parsed(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return None


def _document_class(module: ast.Module) -> ast.ClassDef | None:
    return next(
        (
            node
            for node in module.body
            if isinstance(node, ast.ClassDef) and node.name == "Document"
        ),
        None,
    )


def _method(owner: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return next(
        (
            node
            for node in owner.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        ),
        None,
    )


def _argument_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = function.args
    return {
        item.arg
        for item in [
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        ]
    }


def _call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _loads_source(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or _call_name(node) != "load_from" or not node.args:
            continue
        if isinstance(node.args[0], ast.Name) and node.args[0].id == "source":
            return True
    return False


def _save_evidence(
    repository_root: Path,
    module: ast.Module,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    family: str,
) -> bool:
    if not {"destination", "save_format"} <= _argument_names(function):
        return False
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    helper_calls = {
        name
        for call in calls
        if (name := _call_name(call)) is not None
        and name.lstrip("_") == f"require_{family}_save_format"
    }
    writes = any(_call_name(call) in {"write", "write_bytes", "save"} for call in calls)
    if not helper_calls or not writes:
        return False
    imports: dict[str, str] = {}
    for node in module.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        for alias in node.names:
            imports[alias.asname or alias.name] = f"{node.module}:{alias.name}"
    for helper in helper_calls:
        binding = imports.get(helper)
        if binding is None:
            continue
        module_name, symbol = binding.split(":", maxsplit=1)
        helper_path = repository_root / "src" / Path(*module_name.split("."))
        helper_path = helper_path.with_suffix(".py")
        helper_module = _parsed(helper_path)
        if helper_module is None:
            continue
        helper_function = next(
            (
                node
                for node in helper_module.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
            ),
            None,
        )
        if helper_function is None:
            continue
        literals = {
            node.value.casefold()
            for node in ast.walk(helper_module)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if family.casefold() in literals:
            return True
    return False


def corroborate_python_primary_format_directions(
    repository_root: Path,
    *,
    family: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Upgrade only source-proven primary import/export records to functional evidence."""

    normalized_family = family.casefold()
    primary_entries = [item for item in formats if item.format.casefold() == normalized_family]
    document_entry = next(
        (item for item in primary_entries if Path(item.file).stem.casefold() == "document"),
        None,
    )
    enum_entry = next((item for item in primary_entries if item.direction == "enum_only"), None)
    if document_entry is None:
        return formats
    document_path = repository_root / document_entry.file
    module = _parsed(document_path)
    owner = _document_class(module) if module is not None else None
    if module is None or owner is None:
        return formats
    constructor = _method(owner, "__init__")
    save = _method(owner, "save")
    import_proven = (
        constructor is not None
        and "source" in _argument_names(constructor)
        and _loads_source(constructor)
    )
    export_proven = (
        enum_entry is not None
        and save is not None
        and _save_evidence(repository_root, module, save, normalized_family)
    )
    upgraded = [
        item.model_copy(update={"functional": True})
        if import_proven and item is document_entry and item.direction in {"import", "both"}
        else item
        for item in formats
    ]
    if export_proven and not any(
        item.format.casefold() == normalized_family
        and item.direction in {"export", "both"}
        and item.functional is True
        for item in upgraded
    ):
        assert save is not None
        assert enum_entry is not None
        upgraded.append(
            AsposeOrgFormatEvidenceV1(
                format=enum_entry.format,
                direction="export",
                file=document_entry.file,
                line=save.lineno,
                functional=True,
            )
        )
    return upgraded
