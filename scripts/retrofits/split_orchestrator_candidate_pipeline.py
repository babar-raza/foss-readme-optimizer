"""Extract README candidate construction from the audited orchestrator."""

import ast
import hashlib
from pathlib import Path

SOURCE = Path("src/readme_agent/orchestrator.py")
TARGET = Path("src/readme_agent/readme/candidate_pipeline.py")
EXPECTED_SHA256 = "3e754ba385f64dfba51a7484dc5e72ea0319e388d343182f59b95ccc1ec160d7"
MOVED = {
    "ReadmeCandidate",
    "require_permitted",
    "_policy_content_hash",
    "_work_clone_fingerprint_sidecar",
    "_is_valid_work_clone",
    "_ensure_work_clone",
    "prepare_readme_candidate",
}


def _name(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    return None


def _segment(text: str, node: ast.AST) -> str:
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.decorator_list
    ):
        lines = text.splitlines(keepends=True)
        start = min(decorator.lineno for decorator in node.decorator_list) - 1
        return "".join(lines[start : node.end_lineno])
    segment = ast.get_source_segment(text, node)
    if segment is None:
        raise RuntimeError(f"cannot recover source for {type(node).__name__}")
    return segment


def main() -> None:
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(
            f"refusing to split orchestrator.py: expected {EXPECTED_SHA256}, observed {digest}"
        )
    text = raw.decode("utf-8")
    tree = ast.parse(text)
    imports = [
        _segment(text, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    moved = [
        _segment(text, node)
        for node in tree.body
        if _name(node) in MOVED and _name(node) != "require_permitted"
    ]
    missing = (MOVED - {"require_permitted"}) - {
        _name(node) for node in tree.body if _name(node) is not None
    }
    if missing:
        raise SystemExit(f"candidate pipeline nodes missing: {sorted(missing)}")

    target_text = (
        '"""Build and validate an immutable README candidate without applying effects."""\n\n'
        + "\n".join(imports)
        + "\nfrom readme_agent.registry.access import require_permitted\n\n\n"
        + "\n\n\n".join(moved)
        + "\n"
    )
    TARGET.write_text(target_text, encoding="utf-8", newline="\n")

    retained = [
        _segment(text, node)
        for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom))
        and not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        and _name(node) not in MOVED
    ]
    orchestrator_text = (
        '"""Compatibility orchestration and reporting around canonical capabilities."""\n\n'
        + "\n".join(imports)
        + "\nfrom readme_agent.readme.candidate_pipeline import "
        "ReadmeCandidate, prepare_readme_candidate\n"
        + "from readme_agent.registry.access import require_permitted\n\n\n"
        + "\n\n\n".join(retained)
        + "\n"
    )
    SOURCE.write_text(orchestrator_text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
