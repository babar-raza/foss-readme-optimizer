"""Classify explicit Python function constraints from parsed source."""

from __future__ import annotations

import ast


def function_is_unimplemented(source: str, line_number: int) -> bool:
    """Return whether the function at ``line_number`` only raises an unsupported error."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.lineno <= line_number <= (node.end_lineno or node.lineno)
    ]
    if not functions:
        return False
    function = min(functions, key=lambda node: (node.end_lineno or node.lineno) - node.lineno)
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Raise) or body[0].exc is None:
        return False
    exception = body[0].exc
    if isinstance(exception, ast.Call):
        exception = exception.func
    if isinstance(exception, ast.Name):
        name = exception.id
    elif isinstance(exception, ast.Attribute):
        name = exception.attr
    else:
        return False
    return name.startswith(("NotImplemented", "NotSupported", "Unsupported"))
