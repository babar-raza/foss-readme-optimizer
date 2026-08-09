"""README eligibility regressions for inventoried Python API symbols."""

from readme_agent.ecosystems.python_api_schema import PublicSymbolV1
from readme_agent.facts.curated_python_api_eligibility import (
    is_readme_presentable_symbol,
    presentation_exclusion,
)


def _symbol(**changes: object) -> PublicSymbolV1:
    payload: dict[str, object] = {
        "qualified_name": "acme.internal.write_output",
        "import_module": "acme.internal",
        "name": "write_output",
        "kind": "function",
        "source_path": "src/acme/internal.py",
        "source_line": 7,
        "public_by": "name",
    }
    payload.update(changes)
    return PublicSymbolV1.model_validate(payload)


def test_name_only_implementation_symbol_is_inventoried_but_not_presentable() -> None:
    symbol = _symbol()

    assert is_readme_presentable_symbol(symbol) is False
    assert presentation_exclusion(symbol)["reason"] == (
        "name_only_symbol_without_package_export_or_verified_consumer_import"
    )


def test_explicit_and_consumer_verified_symbols_are_presentable() -> None:
    assert is_readme_presentable_symbol(_symbol(public_by="__all__")) is True
    assert is_readme_presentable_symbol(
        _symbol(public_by="reexport", reexported_from="acme.internal.write_output")
    )
    assert is_readme_presentable_symbol(_symbol(import_verified=True)) is True
    assert is_readme_presentable_symbol(
        _symbol(source_path="src/acme/__init__.py", import_module="acme")
    )


def test_package_module_alias_is_not_repeated_as_an_api_operation() -> None:
    symbol = _symbol(
        qualified_name="aspose.threed",
        import_module="aspose",
        name="threed",
        kind="module",
        source_path="aspose/__init__.py",
        source_line=1,
        public_by="reexport",
        reexported_from="aspose.threed",
    )

    assert is_readme_presentable_symbol(symbol) is False
    assert presentation_exclusion(symbol)["reason"] == (
        "package_module_alias_is_represented_by_its_namespace_table"
    )
