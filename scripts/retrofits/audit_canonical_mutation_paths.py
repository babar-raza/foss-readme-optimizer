"""Prove production mutation primitives are reachable only through registered capabilities."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "readme_agent"

MUTATION_SYMBOLS = {
    "commit_verified_readme": "capabilities/commit_readme_write.py",
    "push_branch": "capabilities/open_presentation_pr.py",
    "create_pull_request": "capabilities/open_presentation_pr.py",
}


def _source_files() -> list[Path]:
    return sorted(SOURCE_ROOT.rglob("*.py"))


def _symbol_users(symbol: str, files: list[Path]) -> list[str]:
    users: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported = any(
            isinstance(node, ast.ImportFrom) and any(alias.name == symbol for alias in node.names)
            for node in ast.walk(tree)
        )
        called = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == symbol
            for node in ast.walk(tree)
        )
        if imported or called:
            users.append(path.relative_to(SOURCE_ROOT).as_posix())
    return users


def main() -> None:
    files = _source_files()
    symbol_users = {symbol: _symbol_users(symbol, files) for symbol in MUTATION_SYMBOLS}
    violations = {
        symbol: users
        for symbol, users in symbol_users.items()
        if users != [MUTATION_SYMBOLS[symbol]]
    }

    compatibility_files = [
        SOURCE_ROOT / "commands_compatibility.py",
        SOURCE_ROOT / "commands.py",
    ]
    compatibility_source = "\n".join(
        path.read_text(encoding="utf-8") for path in compatibility_files
    )
    forbidden_legacy_calls = [
        name
        for name in ("generate_repo(", "run_repo(", "commit_verified_readme(")
        if name in compatibility_source
    ]
    if "supervise_repo(" not in compatibility_source:
        forbidden_legacy_calls.append("missing supervise_repo routing")

    report = {
        "schema": "canonical-mutation-path-audit-v1",
        "source_tree_sha256": hashlib.sha256(
            b"".join(path.read_bytes() for path in files)
        ).hexdigest(),
        "mutation_symbol_users": symbol_users,
        "expected_symbol_users": MUTATION_SYMBOLS,
        "compatibility_forbidden_calls": forbidden_legacy_calls,
        "passed": not violations and not forbidden_legacy_calls,
        "violations": violations,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
