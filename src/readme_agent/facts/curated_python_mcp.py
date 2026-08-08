"""Extract a mechanically bound Python MCP server summary."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


def _function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    return next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name),
        None,
    )


def _literal_defaults(function: ast.FunctionDef) -> dict[str, object]:
    arguments = function.args.args
    defaults = [None] * (len(arguments) - len(function.args.defaults)) + list(
        function.args.defaults
    )
    values: dict[str, object] = {}
    for argument, default in zip(arguments, defaults, strict=True):
        if default is None:
            continue
        try:
            values[argument.arg] = ast.literal_eval(default)
        except (ValueError, TypeError):
            continue
    return values


def _factory_instance_runs(
    runner: ast.FunctionDef,
    *,
    factory_name: str,
) -> bool:
    """Prove that the exported runner invokes ``run`` on the factory result."""

    factory_variables = {
        target.id
        for node in runner.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == factory_name
    }
    for node in ast.walk(runner):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
        ):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Name) and owner.id in factory_variables:
            return True
        if (
            isinstance(owner, ast.Call)
            and isinstance(owner.func, ast.Name)
            and owner.func.id == factory_name
        ):
            return True
    return False


def python_mcp_server(root: Path) -> tuple[dict[str, object], list[str]] | None:
    """Return the exact factory, tools, runner defaults, and dependency from source."""

    server_path = next(iter(sorted((root / "src").glob("**/mcp/server.py"))), None)
    if server_path is None:
        return None
    init_path = server_path.parent / "__init__.py"
    if not server_path.is_file() or not init_path.is_file():
        return None
    try:
        tree = ast.parse(server_path.read_text(encoding="utf-8"))
        init_tree = ast.parse(init_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None
    factory = _function(tree, "create_server")
    runner = _function(tree, "run")
    if factory is None or runner is None:
        return None
    if not _factory_instance_runs(runner, factory_name="create_server"):
        return None
    exports: set[str] = set()
    for node in init_tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            continue
        try:
            exports = {str(item) for item in ast.literal_eval(node.value)}
        except (ValueError, TypeError):
            pass
    if not {"create_server", "run"}.issubset(exports):
        return None
    tools = sorted(
        {
            call.args[0].id
            for call in ast.walk(factory)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "tool"
            and len(call.args) == 1
            and isinstance(call.args[0], ast.Name)
        }
    )
    imports_fastmcp = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "fastmcp"
        and any(alias.name == "FastMCP" for alias in node.names)
        for node in ast.walk(factory)
    )
    if not tools or not imports_fastmcp:
        return None
    test_path = root / "tests/mcp/test_server.py"
    if not test_path.is_file():
        return None
    test_text = test_path.read_text(encoding="utf-8")
    if "create_server" not in test_text or any(tool not in test_text for tool in tools):
        return None
    relative_server = server_path.relative_to(root).as_posix()
    relative_init = init_path.relative_to(root).as_posix()
    relative_module = server_path.parent.relative_to(root / "src").as_posix().replace("/", ".")
    relative_test = test_path.relative_to(root).as_posix()
    return (
        {
            "kind": "mcp_server",
            "module": relative_module,
            "factory": "create_server",
            "runner": "run",
            "factory_instance_run": True,
            "tools": tools,
            "runner_defaults": _literal_defaults(runner),
            "dependency_package": "fastmcp",
            "source_sha256": hashlib.sha256(server_path.read_bytes()).hexdigest(),
            "test_path": relative_test,
            "test_sha256": hashlib.sha256(test_path.read_bytes()).hexdigest(),
        },
        [relative_server, relative_init, relative_test],
    )
