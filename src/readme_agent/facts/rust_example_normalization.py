"""Derive a minimal Rust consumer from syntax-proven public API traits."""

from __future__ import annotations

import re
from pathlib import Path

from readme_agent.ecosystems.rust_api_schema import RustPublicSymbolV1
from readme_agent.ecosystems.rust_public_api import inspect_rust_public_api
from readme_agent.registry.models import MinimalExamplePolicy


def _uses_every_declared_symbol(example: MinimalExamplePolicy) -> bool:
    if re.search(r"\bfn\s+main\s*\(", example.code) is None:
        return False
    return bool(example.required_symbols) and all(
        len(re.findall(rf"\b{re.escape(symbol.rsplit('::', 1)[-1])}\b", example.code)) >= 2
        for symbol in example.required_symbols
    )


def _constructible_public_types(symbols: list[RustPublicSymbolV1]) -> list[RustPublicSymbolV1]:
    return [
        symbol
        for symbol in symbols
        if symbol.parent_name is None
        and symbol.kind == "struct"
        and ("Default" in symbol.derives or "Default" in symbol.implemented_traits)
    ]


def _preferred_type(
    candidates: list[RustPublicSymbolV1],
    example: MinimalExamplePolicy,
) -> RustPublicSymbolV1 | None:
    preferred_names = [
        example.class_name,
        *(symbol.rsplit("::", 1)[-1] for symbol in example.required_symbols),
    ]
    by_name = {candidate.name: candidate for candidate in candidates}
    for name in preferred_names:
        if candidate := by_name.get(name):
            return candidate
    return (
        sorted(candidates, key=lambda candidate: candidate.qualified_name)[0]
        if candidates
        else None
    )


def _variable_name(type_name: str) -> str:
    rendered = re.sub(r"(?<!^)(?=[A-Z])", "_", type_name).casefold()
    return rendered if rendered.isidentifier() else "product"


def normalize_rust_public_consumer(
    root: Path,
    example: MinimalExamplePolicy,
) -> MinimalExamplePolicy:
    """Repair a non-self-contained draft with one source-proven public construction."""

    if _uses_every_declared_symbol(example):
        return example
    root = root.resolve()
    try:
        surface = inspect_rust_public_api(
            root,
            org_repo="local/source",
            source_revision="local-source",
        )
    except (OSError, UnicodeError, ValueError):
        return example
    selected = _preferred_type(_constructible_public_types(surface.symbols), example)
    if selected is None:
        return example
    variable = _variable_name(selected.name)
    code = (
        f"use {selected.import_path};\n\n"
        "fn main() {\n"
        f"    let _{variable} = {selected.name}::default();\n"
        "}\n"
    )
    return example.model_copy(
        update={
            "class_name": selected.name,
            "code": code,
            "evidence_paths": [selected.declaration_path],
            "required_symbols": [selected.name],
        }
    )
