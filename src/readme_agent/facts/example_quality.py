"""Reject generated README examples that are unsuitable as minimal public guidance."""

from __future__ import annotations

import ast

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, String
from pygments.util import ClassNotFound

_MAX_PYTHON_TOP_LEVEL_STATEMENTS = 8
_MAX_PYTHON_IMPORTED_SYMBOLS = 5
_LEXER_BY_LANGUAGE = {
    "cpp": "cpp",
    "dotnet": "csharp",
    "go": "go",
    "java": "java",
    "python": "python",
    "rust": "rust",
    "typescript": "typescript",
}


def _is_source_comment(token) -> bool:
    """Exclude compiler directives that Pygments classifies as preprocessor comments."""

    return token in Comment and token not in Comment.Preproc and token not in Comment.PreprocFile


def _lexer_name(language: str) -> str | None:
    normalized = language.strip().casefold()
    lexer_name = _LEXER_BY_LANGUAGE.get(normalized, normalized)
    try:
        get_lexer_by_name(lexer_name)
    except ClassNotFound:
        return None
    return lexer_name


def source_contains_comments(language: str, source: str) -> bool:
    """Return whether a recognized source language contains visitor-facing comments."""

    lexer_name = _lexer_name(language)
    if lexer_name is None:
        return False
    return any(
        _is_source_comment(token) or token in String.Doc
        for token, _value in lex(source, get_lexer_by_name(lexer_name))
    )


def strip_source_comments(language: str, source: str) -> str:
    """Remove source comments while preserving code layout and string literals."""

    lexer_name = _lexer_name(language)
    if lexer_name is None:
        return source
    rendered: list[str] = []
    for token, value in lex(source, get_lexer_by_name(lexer_name)):
        if _is_source_comment(token) or token in String.Doc:
            rendered.append("".join("\n" if character == "\n" else " " for character in value))
        else:
            rendered.append(value)
    normalized = "\n".join(line.rstrip() for line in "".join(rendered).splitlines())
    return normalized + ("\n" if source.endswith("\n") else "")


def generated_example_quality_failures(language: str, source: str) -> list[str]:
    """Return deterministic public-API and minimality failures for generated code.

    Type correctness remains the ecosystem compiler's authority. Python syntax
    is parsed here because all later Python quality checks depend on the AST and
    malformed model output must enter the repair loop instead of escaping as a
    system failure. This check also owns contracts a syntax-only compilation
    cannot prove: README examples must use public APIs, demonstrate an
    operation, and not substitute an import inventory for a working example.
    """

    failures: list[str] = []
    if source_contains_comments(language, source):
        failures.append(
            "minimal README example contains a source comment or documentation comment; "
            "regenerate it as comment-free visitor-facing code"
        )
    if language != "python":
        return failures
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        failures.append(
            "minimal Python README example has invalid syntax at "
            f"line {exc.lineno or 'unknown'}: {exc.msg}; regenerate valid Python"
        )
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
    executable_statements = [
        statement
        for statement in tree.body
        if not isinstance(statement, (ast.Import, ast.ImportFrom))
    ]
    if len(executable_statements) > _MAX_PYTHON_TOP_LEVEL_STATEMENTS:
        failures.append(
            "minimal Python README example has "
            f"{len(executable_statements)} executable statements; regenerate it with at most "
            f"{_MAX_PYTHON_TOP_LEVEL_STATEMENTS}"
        )
    statement_lines = [statement.lineno for statement in tree.body if hasattr(statement, "lineno")]
    if len(statement_lines) != len(set(statement_lines)):
        failures.append(
            "minimal Python README example packs multiple statements onto one line; "
            "regenerate it with one short statement per line"
        )
    if any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "__import__"
        for node in ast.walk(tree)
    ):
        failures.append(
            "minimal Python README example uses dynamic __import__; regenerate it with "
            "ordinary, readable import statements"
        )
    if any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "mktemp"
        for node in ast.walk(tree)
    ):
        failures.append(
            "minimal Python README example uses unsafe tempfile.mktemp; regenerate it with "
            "a clear deterministic output path or a safe temporary-file API"
        )
    if any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Name)
        and node.func.value.func.id == "open"
        for node in ast.walk(tree)
    ):
        failures.append(
            "minimal Python README example chains an operation onto an unclosed open() call; "
            "regenerate it with pathlib or a context-managed file"
        )
    imported_names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            imported_names.update(
                alias.asname or alias.name.split(".", 1)[0] for alias in statement.names
            )
        elif isinstance(statement, ast.ImportFrom):
            imported_names.update(alias.asname or alias.name for alias in statement.names)
    if len(imported_names) > _MAX_PYTHON_IMPORTED_SYMBOLS:
        failures.append(
            "minimal Python README example imports "
            f"{len(imported_names)} symbols; regenerate it with at most "
            f"{_MAX_PYTHON_IMPORTED_SYMBOLS}"
        )

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
