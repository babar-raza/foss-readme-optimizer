"""Reject generated README examples that are unsuitable as minimal public guidance."""

from __future__ import annotations

import ast

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, String

_MAX_PYTHON_TOP_LEVEL_STATEMENTS = 8
_LEXER_BY_LANGUAGE = {
    "cpp": "cpp",
    "dotnet": "csharp",
    "go": "go",
    "java": "java",
    "python": "python",
    "rust": "rust",
    "typescript": "typescript",
}


def _contains_comment(language: str, source: str) -> bool:
    lexer_name = _LEXER_BY_LANGUAGE.get(language)
    if lexer_name is None:
        return False
    return any(
        token in Comment or token in String.Doc
        for token, _value in lex(source, get_lexer_by_name(lexer_name))
    )


def generated_example_quality_failures(language: str, source: str) -> list[str]:
    """Return deterministic public-API and minimality failures for generated code.

    Syntax and type correctness remain the ecosystem compiler's authority.
    This check owns contracts a syntax-only Python compilation cannot prove:
    README examples must use public APIs, must demonstrate an operation, and
    must not substitute an exhaustive import inventory for a working example.
    """

    failures: list[str] = []
    if _contains_comment(language, source):
        failures.append(
            "minimal README example contains a source comment or documentation comment; "
            "regenerate it as comment-free visitor-facing code"
        )
    if language != "python":
        return failures
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return failures
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
    if len(tree.body) > _MAX_PYTHON_TOP_LEVEL_STATEMENTS:
        failures.append(
            "minimal Python README example has "
            f"{len(tree.body)} executable statements; regenerate it with at most "
            f"{_MAX_PYTHON_TOP_LEVEL_STATEMENTS}"
        )
    imported_names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            imported_names.update(
                alias.asname or alias.name.split(".", 1)[0] for alias in statement.names
            )
        elif isinstance(statement, ast.ImportFrom):
            imported_names.update(alias.asname or alias.name for alias in statement.names)
    if len(imported_names) > 3:
        failures.append(
            "minimal Python README example imports "
            f"{len(imported_names)} symbols; regenerate it with at most 3"
        )

    executable_statements = [
        statement
        for statement in tree.body
        if not isinstance(statement, (ast.Import, ast.ImportFrom))
    ]
    if not executable_statements:
        failures.append(
            "minimal Python README example contains only imports; regenerate it with "
            "a repository-evidenced public API operation"
        )

    loaded_names = {
        node.id
        for statement in executable_statements
        for node in ast.walk(statement)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    unused_imports = sorted(imported_names - loaded_names)
    if unused_imports:
        failures.append(
            "minimal Python README example has unused imported symbol(s) "
            f"{unused_imports}; keep only symbols exercised by the example"
        )
    return failures
