"""Rejects generated README examples that rely on non-public APIs."""

from __future__ import annotations

import ast


def generated_example_quality_failures(language: str, source: str) -> list[str]:
    """Return deterministic public-API quality failures for generated code.

    Syntax and type correctness remain the ecosystem compiler's authority.
    This check owns the narrower contract a compiler cannot prove: README
    examples must not teach Python callers to depend on private attributes.
    """

    if language != "python":
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    failures: list[str] = []
    private_attributes = sorted(
        {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr.startswith("_")
            and not (node.attr.startswith("__") and node.attr.endswith("__"))
        }
    )
    if private_attributes:
        failures.append(
            "minimal Python README example uses private attribute(s) "
            f"{private_attributes}; regenerate it with repository-evidenced public APIs"
        )
    if len(tree.body) > 6:
        failures.append(
            "minimal Python README example has "
            f"{len(tree.body)} executable statements; regenerate it with at most 6"
        )
    return failures
