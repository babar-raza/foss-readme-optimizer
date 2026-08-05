"""Parse literal setuptools setup.py metadata without executing repository code."""

import ast
from pathlib import Path

_PYTHON_VERSION_CLASSIFIER_PREFIX = "Programming Language :: Python :: "


def _direct_import_bindings(tree: ast.Module) -> dict[str, list[str]]:
    """Classify direct imports that can prove a setuptools call owner."""

    bindings: dict[str, list[str]] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                bound_name = alias.asname or alias.name.split(".", maxsplit=1)[0]
                owner = "setuptools_module" if alias.name == "setuptools" else "foreign_import"
                bindings.setdefault(bound_name, []).append(owner)
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                bound_name = alias.asname or alias.name
                owner = (
                    "setuptools_setup"
                    if statement.level == 0
                    and statement.module == "setuptools"
                    and alias.name == "setup"
                    else "foreign_import"
                )
                bindings.setdefault(bound_name, []).append(owner)
    return bindings


class _ModuleBindingVisitor(ast.NodeVisitor):
    """Collect bindings in module control flow without entering local scopes."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802 - ast visitor API
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802 - ast visitor API
        if isinstance(node.ctx, (ast.Store, ast.Del)) and isinstance(node.value, ast.Name):
            self.names.add(node.value.id)
        self.generic_visit(node)

    def visit_alias(self, node: ast.alias) -> None:  # noqa: N802 - ast visitor API
        self.names.add(node.asname or node.name.split(".", maxsplit=1)[0])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802 - ast visitor API
        self.names.add(node.name)

    def visit_AsyncFunctionDef(  # noqa: N802 - ast visitor API
        self, node: ast.AsyncFunctionDef
    ) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802 - ast visitor API
        self.names.add(node.name)

    def visit_Lambda(self, _node: ast.Lambda) -> None:  # noqa: N802 - ast visitor API
        return


def _non_import_bindings(tree: ast.Module) -> set[str]:
    """Return names that a non-direct-import module statement may bind."""

    visitor = _ModuleBindingVisitor()
    for statement in tree.body:
        if not isinstance(statement, (ast.Import, ast.ImportFrom)):
            visitor.visit(statement)
    return visitor.names


def _has_proven_setuptools_owner(call: ast.Call, bindings: dict[str, list[str]]) -> bool:
    if isinstance(call.func, ast.Name):
        return bindings.get(call.func.id) == ["setuptools_setup"]
    return (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "setup"
        and isinstance(call.func.value, ast.Name)
        and bindings.get(call.func.value.id) == ["setuptools_module"]
    )


def _setup_call(tree: ast.Module) -> ast.Call | None:
    """Return one top-level call proven to originate from setuptools."""

    bindings = _direct_import_bindings(tree)
    for rebound_name in _non_import_bindings(tree):
        if rebound_name in bindings:
            bindings[rebound_name].append("local_binding")
    calls = [
        statement.value
        for statement in tree.body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and _has_proven_setuptools_owner(statement.value, bindings)
    ]
    if any(keyword.arg is None for call in calls for keyword in call.keywords):
        return None
    return calls[0] if len(calls) == 1 else None


def _literal_setup_keywords(setup_py_path: Path) -> dict[str, object]:
    """Read literal setup keyword values without importing or executing the file."""

    try:
        tree = ast.parse(
            setup_py_path.read_text(encoding="utf-8-sig", errors="replace"),
            filename=str(setup_py_path),
        )
    except (OSError, SyntaxError):
        return {}
    call = _setup_call(tree)
    if call is None:
        return {}

    literals: dict[str, object] = {}
    for keyword in call.keywords:
        if keyword.arg is None:
            continue
        try:
            literals[keyword.arg] = ast.literal_eval(keyword.value)
        except (TypeError, ValueError):
            continue
    return literals


def _literal_python_classifier_versions(value: object) -> list[str]:
    """Return exact X.Y Python classifier versions in deterministic order."""

    if not isinstance(value, (list, tuple)):
        return []
    versions: set[tuple[int, int]] = set()
    for classifier in value:
        if not isinstance(classifier, str) or not classifier.startswith(
            _PYTHON_VERSION_CLASSIFIER_PREFIX
        ):
            continue
        version = classifier.removeprefix(_PYTHON_VERSION_CLASSIFIER_PREFIX)
        parts = version.split(".")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            continue
        versions.add((int(parts[0]), int(parts[1])))
    return [f"{major}.{minor}" for major, minor in sorted(versions)]


def parse_setup_py(setup_py_path: Path) -> dict[str, str]:
    """Return only literal metadata from a proven setuptools setup call."""

    literals = _literal_setup_keywords(setup_py_path)
    info: dict[str, str] = {}
    for source, target in (
        ("name", "name"),
        ("version", "version"),
        ("python_requires", "requires_python"),
    ):
        value = literals.get(source)
        if isinstance(value, str) and value.strip():
            info[target] = value.strip()
    classifier_versions = _literal_python_classifier_versions(literals.get("classifiers"))
    if classifier_versions:
        info["python_classifier_versions"] = ",".join(classifier_versions)
    return info
