"""Classify inventoried Python symbols for visitor-facing API presentation."""

from __future__ import annotations

from pathlib import PurePosixPath

from readme_agent.ecosystems.python_api_schema import PublicSymbolV1


def is_readme_presentable_symbol(symbol: PublicSymbolV1) -> bool:
    """Require a visitor-facing export, never a package-module alias."""

    return bool(
        symbol.kind != "module"
        and (
            symbol.public_by in {"__all__", "reexport"}
            or symbol.reexported_from
            or symbol.import_verified
            or PurePosixPath(symbol.source_path).name == "__init__.py"
        )
    )


def presentation_exclusion(symbol: PublicSymbolV1) -> dict[str, object]:
    """Record why a mechanically inventoried symbol is absent from README tables."""

    reason = (
        "package_module_alias_is_represented_by_its_namespace_table"
        if symbol.kind == "module"
        else "name_only_symbol_without_package_export_or_verified_consumer_import"
    )
    return {
        "qualified_name": symbol.qualified_name,
        "import_module": symbol.import_module,
        "name": symbol.name,
        "kind": symbol.kind,
        "source_path": symbol.source_path,
        "source_line": symbol.source_line,
        "reason": reason,
    }


__all__ = ["is_readme_presentable_symbol", "presentation_exclusion"]
