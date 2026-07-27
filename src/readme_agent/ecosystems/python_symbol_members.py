"""Build typed Python symbols and extract public class members."""

from __future__ import annotations

import ast
from pathlib import Path

from readme_agent.ecosystems.python_api_schema import PublicSymbolV1, PythonSymbolKind


def decorators(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    return [ast.unparse(decorator) for decorator in node.decorator_list]


def annotation(node: ast.AST | None) -> str | None:
    return ast.unparse(node) if node is not None else None


def python_symbol(
    *,
    module: str,
    name: str,
    kind: PythonSymbolKind,
    path: Path,
    repository_root: Path,
    line: int,
    public_by: str,
    decorators_: list[str] | None = None,
    annotation_: str | None = None,
    writable: bool | None = None,
    reexported_from: str | None = None,
) -> PublicSymbolV1:
    return PublicSymbolV1(
        qualified_name=f"{module}.{name}" if name else module,
        import_module=module,
        name=name,
        kind=kind,
        source_path=path.relative_to(repository_root).as_posix(),
        source_line=line,
        decorators=decorators_ or [],
        annotation=annotation_,
        writable=writable,
        reexported_from=reexported_from,
        public_by=public_by,  # type: ignore[arg-type]
    )


def class_symbols(
    node: ast.ClassDef,
    module: str,
    path: Path,
    repository_root: Path,
) -> list[PublicSymbolV1]:
    results: list[PublicSymbolV1] = []
    bases = {ast.unparse(base).split(".")[-1] for base in node.bases}
    class_kind: PythonSymbolKind = "enum" if bases & {"Enum", "IntEnum", "StrEnum"} else "class"
    is_typed_dict = "TypedDict" in bases
    is_dataclass = any(item.split(".")[-1] == "dataclass" for item in decorators(node))
    results.append(
        python_symbol(
            module=module,
            name=node.name,
            kind=class_kind,
            path=path,
            repository_root=repository_root,
            line=node.lineno,
            public_by="name",
            decorators_=decorators(node),
        )
    )
    property_setters = {
        decorator.value.id
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        for decorator in child.decorator_list
        if isinstance(decorator, ast.Attribute)
        and decorator.attr == "setter"
        and isinstance(decorator.value, ast.Name)
    }
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith(
            "_"
        ):
            child_decorators = decorators(child)
            if any(
                item.endswith(".setter") or item.endswith(".deleter") for item in child_decorators
            ):
                continue
            is_property = any(item.split(".")[-1] == "property" for item in child_decorators)
            results.append(
                python_symbol(
                    module=module,
                    name=f"{node.name}.{child.name}",
                    kind="property" if is_property else "method",
                    path=path,
                    repository_root=repository_root,
                    line=child.lineno,
                    public_by="name",
                    decorators_=child_decorators,
                    annotation_=annotation(child.returns),
                    writable=child.name in property_setters if is_property else None,
                )
            )
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            if child.target.id.startswith("_"):
                continue
            if is_typed_dict or is_dataclass:
                results.append(
                    python_symbol(
                        module=module,
                        name=f"{node.name}.{child.target.id}",
                        kind="typed_field",
                        path=path,
                        repository_root=repository_root,
                        line=child.lineno,
                        public_by="name",
                        annotation_=annotation(child.annotation),
                    )
                )
            elif class_kind == "enum":
                results.append(
                    python_symbol(
                        module=module,
                        name=f"{node.name}.{child.target.id}",
                        kind="enum_member",
                        path=path,
                        repository_root=repository_root,
                        line=child.lineno,
                        public_by="name",
                        annotation_=annotation(child.annotation),
                    )
                )
        elif (
            class_kind == "enum"
            and isinstance(child, ast.Assign)
            and len(child.targets) == 1
            and isinstance(child.targets[0], ast.Name)
            and not child.targets[0].id.startswith("_")
        ):
            results.append(
                python_symbol(
                    module=module,
                    name=f"{node.name}.{child.targets[0].id}",
                    kind="enum_member",
                    path=path,
                    repository_root=repository_root,
                    line=child.lineno,
                    public_by="name",
                )
            )
    return results
