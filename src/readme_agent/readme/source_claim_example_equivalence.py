"""Prove comment-only equivalence between inherited and verified examples."""

from __future__ import annotations

import ast
import re

from readme_agent.facts.example_quality import source_contains_comments, strip_source_comments

_FENCE = re.compile(
    r"^\s*```(?P<language>[A-Za-z0-9_+#.-]+)\s*\r?\n(?P<code>.*)\r?\n```\s*$",
    re.DOTALL | re.IGNORECASE,
)
_FENCE_LANGUAGE = {
    "c++": "cpp",
    "cpp": "cpp",
    "csharp": "dotnet",
    "cs": "dotnet",
    "cxx": "cpp",
    "dotnet": "dotnet",
    "go": "go",
    "golang": "go",
    "java": "java",
    "py": "python",
    "python": "python",
    "rs": "rust",
    "rust": "rust",
    "ts": "typescript",
    "typescript": "typescript",
}


def fenced_source_code(value: str) -> tuple[str, str] | None:
    """Return one normalized supported language and its exact fenced payload."""

    match = _FENCE.fullmatch(value)
    if match is None:
        return None
    language = _FENCE_LANGUAGE.get(match.group("language").casefold())
    return (language, match.group("code") + "\n") if language is not None else None


def normalized_source_language(value: str) -> str:
    """Normalize a policy or fence language through the supported aliases."""

    folded = value.strip().casefold()
    return _FENCE_LANGUAGE.get(folded, folded)


def _python_ast(value: str) -> str | None:
    try:
        return ast.dump(ast.parse(value), include_attributes=False)
    except SyntaxError:
        return None


def _compiled_code_identity(value: str) -> str:
    """Ignore comment-created blank lines while preserving executable text and indentation."""

    return "\n".join(line.rstrip() for line in value.splitlines() if line.strip())


def _java_unwrapped_consumer_identity(value: str) -> str | None:
    """Return the exact Java fragment wrapped by the governed consumer verifier."""

    lines = value.rstrip().splitlines()
    wrapper = next(
        (
            index
            for index, line in enumerate(lines)
            if re.fullmatch(r"public (?:final )?class ReadmeExample \{", line)
        ),
        None,
    )
    if wrapper is None or wrapper + 3 >= len(lines):
        return None
    if lines[wrapper + 1] != "    public static void main(String[] args) throws Exception {":
        return None
    if lines[-2:] != ["    }", "}"]:
        return None
    prefix = lines[:wrapper]
    if any(line and not line.startswith("import ") for line in prefix):
        return None
    body: list[str] = []
    for line in lines[wrapper + 2 : -2]:
        if line and not line.startswith("        "):
            return None
        body.append(line[8:] if line else "")
    return _compiled_code_identity("\n".join([*prefix, *body]))


def verified_rewrapped_example(claim_text: str, verified_code: str) -> bool:
    """Prove that a Java README fragment equals its verified standalone wrapper.

    The repository verifier wraps inherited Java statements in one fixed ``ReadmeExample``
    class so ``javac`` can compile them. This comparison removes only that exact wrapper; it
    never ignores, adds, reorders, or rewrites executable statements.
    """

    fenced = fenced_source_code(claim_text)
    if fenced is None or fenced[0] != "java":
        return False
    source_code = strip_source_comments("java", fenced[1]).rstrip() + "\n"
    candidate_code = strip_source_comments("java", verified_code).rstrip() + "\n"
    unwrapped = _java_unwrapped_consumer_identity(candidate_code)
    return unwrapped is not None and _compiled_code_identity(source_code) == unwrapped


def verified_comment_free_example(claim_text: str, verified_code: str) -> str | None:
    """Return a comment-free fence only when executable code remains identical.

    Python retains its AST-equivalence contract. Compiled languages use the same
    Pygments-backed comment stripper already applied before isolated verification;
    after comments and trailing whitespace are removed, every remaining byte must
    equal the verified example payload.
    """

    fenced = fenced_source_code(claim_text)
    match = _FENCE.fullmatch(claim_text)
    if fenced is None or match is None:
        return None
    language, source_code = fenced
    cleaned_source = strip_source_comments(language, source_code).rstrip() + "\n"
    cleaned_verified = strip_source_comments(language, verified_code).rstrip() + "\n"
    if language == "python":
        expected_ast = _python_ast(verified_code)
        if expected_ast is None or _python_ast(source_code) != expected_ast:
            return None
        if _python_ast(cleaned_source) != expected_ast:
            return None
    elif _compiled_code_identity(cleaned_source) != _compiled_code_identity(cleaned_verified):
        return None
    return f"```{match.group('language')}\n{cleaned_source}```"


def source_claim_has_comments(claim_text: str) -> bool:
    """Return whether one supported fenced source claim contains comments."""

    fenced = fenced_source_code(claim_text)
    return bool(fenced and source_contains_comments(fenced[0], fenced[1]))


__all__ = [
    "fenced_source_code",
    "normalized_source_language",
    "source_claim_has_comments",
    "verified_comment_free_example",
    "verified_rewrapped_example",
]
