"""Audit Python prompt consumers, model routes, hashes, and inline literals."""

from __future__ import annotations

import ast
from pathlib import Path


def source_path_for_module(repo_root: Path, module: str) -> Path:
    return repo_root / "src" / Path(*module.split(".")).with_suffix(".py")


def _call_name(node: ast.Call) -> tuple[str | None, str | None]:
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id, node.func.attr
    if isinstance(node.func, ast.Name):
        return None, node.func.id
    return None, None


def _resolved_string(node: ast.AST, constants: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _literal_first_argument(node: ast.Call, constants: dict[str, str]) -> str | None:
    if not node.args:
        return None
    return _resolved_string(node.args[0], constants)


def _literal_keyword(
    node: ast.Call,
    keyword_name: str,
    constants: dict[str, str],
) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == keyword_name:
            return _resolved_string(keyword.value, constants)
    return None


def _has_direct_prompt_literal(node: ast.AST) -> bool:
    return isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp))


def scan_prompt_source(
    repo_root: Path,
) -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
    list[tuple[str, str]],
    list[str],
]:
    """Return static prompt references plus prohibited inline message literals."""

    content_refs: dict[str, set[str]] = {}
    hash_refs: dict[str, set[str]] = {}
    route_refs: dict[str, set[str]] = {}
    prompt_id_keywords: list[tuple[str, str]] = []
    inline_errors: list[str] = []
    source_root = repo_root / "src" / "readme_agent"
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(repo_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants: dict[str, str] = {}
        for assignment in tree.body:
            if (
                isinstance(assignment, ast.Assign)
                and isinstance(assignment.value, ast.Constant)
                and isinstance(assignment.value.value, str)
            ):
                for target in assignment.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = assignment.value.value
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                owner, name = _call_name(node)
                literal = _literal_first_argument(node, constants)
                if owner == "prompt_registry" and name == "get" and literal is not None:
                    content_refs.setdefault(literal, set()).add(relative)
                elif owner == "prompt_registry" and name == "prompt_hash" and literal is not None:
                    hash_refs.setdefault(literal, set()).add(relative)
                elif name == "llm_model_for_job" and literal is not None:
                    route_refs.setdefault(literal, set()).add(relative)
                prompt_id = _literal_keyword(node, "prompt_id", constants)
                if prompt_id is not None:
                    prompt_id_keywords.append((prompt_id, relative))
            if not isinstance(node, ast.Dict):
                continue
            values = {
                key.value: value
                for key, value in zip(node.keys, node.values, strict=True)
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            role = values.get("role")
            content = values.get("content")
            if (
                isinstance(role, ast.Constant)
                and role.value in {"system", "user"}
                and content is not None
                and _has_direct_prompt_literal(content)
            ):
                inline_errors.append(
                    f"inline prompt message at {relative}:{getattr(node, 'lineno', 0)}"
                )
    return content_refs, hash_refs, route_refs, prompt_id_keywords, inline_errors
