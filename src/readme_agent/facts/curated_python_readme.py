"""Verify curated Python README examples against the repository API surface."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from readme_agent.facts.curated_python_example_validation import (
    ExampleDecision,
    validate_python_example,
)
from readme_agent.readme.document_structure import code_blocks_in_span, parse_headings
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations

_IMAGE = re.compile(r"!\[(?P<alt>[^]]*)\]\((?P<path>[^)\s]+)(?:\s+[^)]*)?\)")
_CANONICAL_EXAMPLE_SECTIONS = {"additional examples", "quick start", "usage"}


def _is_example_section(title: str) -> bool:
    """Recognize semantic example headings independently of decoration or product wording."""

    normalized = " ".join(strip_emoji_decorations(title).casefold().split())
    return normalized in _CANONICAL_EXAMPLE_SECTIONS or normalized.endswith(" examples")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_python_examples(
    readme: str,
    public_surface: object,
) -> tuple[list[dict[str, object]], list[ExampleDecision]]:
    """Return statically verified examples and decisions from canonical README sections."""

    headings = parse_headings(readme)
    sections: list[tuple[str, int, int]] = []
    for parent in headings:
        if parent.level != 2 or not _is_example_section(parent.title):
            continue
        children = [
            heading
            for heading in headings
            if heading.level == 3 and parent.heading_end <= heading.start < parent.section_end
        ]
        direct_end = children[0].start if children else parent.section_end
        sections.append((parent.title.strip(), parent.heading_end, direct_end))
        sections.extend(
            (child.title.strip(), child.heading_end, child.section_end) for child in children
        )
    examples: list[dict[str, object]] = []
    decisions: list[ExampleDecision] = []
    for title, start, end in sections:
        context_imports: list[str] = []
        for block in code_blocks_in_span(readme, start, end):
            accepted, modules, reason = validate_python_example(block.content, public_surface)
            if not accepted and reason == "no_product_api_import" and context_imports:
                contextual_code = "\n".join([*context_imports, block.content])
                accepted, modules, contextual_reason = validate_python_example(
                    contextual_code, public_surface
                )
                if accepted:
                    reason = "accepted_with_section_import_context"
                else:
                    reason = contextual_reason
            decisions.append(ExampleDecision(title, accepted, reason, modules))
            if accepted:
                try:
                    tree = ast.parse(block.content)
                except SyntaxError:  # pragma: no cover - accepted code already parsed
                    tree = ast.Module(body=[], type_ignores=[])
                for node in tree.body:
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        statement = ast.unparse(node)
                        if statement not in context_imports:
                            context_imports.append(statement)
                examples.append(
                    {
                        "title": title,
                        "code": block.content.rstrip(),
                        "language": "python",
                        "static_api_verified": True,
                        "execution_verified": False,
                        "evidence_modules": list(modules),
                        "validation_context_imports": list(context_imports),
                    }
                )
    return examples, decisions


def _result_assets(root: Path, readme: str) -> list[dict[str, str]]:
    section = next(
        (
            heading
            for heading in parse_headings(readme)
            if heading.level == 2 and heading.title.strip().casefold() == "example results"
        ),
        None,
    )
    if section is None:
        return []
    body = readme[section.heading_end : section.section_end]
    assets: list[dict[str, str]] = []
    for match in _IMAGE.finditer(body):
        relative = match.group("path").replace("\\", "/")
        path = root / relative
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if not path.is_file():
            continue
        source_sha256 = _sha256(path)
        evidence_path = next(
            (
                candidate
                for candidate in sorted((root / "testdata").rglob(path.name))
                if candidate.is_file() and _sha256(candidate) == source_sha256
            ),
            None,
        )
        if evidence_path is None:
            continue
        assets.append(
            {
                "alt": match.group("alt").strip() or path.stem,
                "path": relative,
                "sha256": source_sha256,
                "evidence_path": evidence_path.relative_to(root).as_posix(),
                "evidence_sha256": source_sha256,
            }
        )
    return assets


def verified_readme_examples(
    root: Path,
    public_surface: object,
) -> tuple[dict[str, object], list[str]] | None:
    """Return README detail only when repository files corroborate every retained item."""

    readme_path = root / "README.md"
    if not readme_path.is_file() or not public_surface:
        return None
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    validation_surface = public_surface
    if isinstance(public_surface, dict):
        complete_surface = public_surface.get("coordinate_catalog")
        if isinstance(complete_surface, dict):
            validation_surface = complete_surface
    inline_examples, _ = verified_python_examples(readme, validation_surface)
    result_assets = _result_assets(root, readme)
    if not inline_examples and not result_assets:
        return None
    locations = ["README.md"]
    if isinstance(validation_surface, dict):
        for rows in validation_surface.values():
            if not isinstance(rows, list):
                continue
            locations.extend(
                str(row["source_path"])
                for row in rows
                if isinstance(row, dict) and isinstance(row.get("source_path"), str)
            )
    locations.extend(str(item["path"]) for item in result_assets)
    locations.extend(str(item["evidence_path"]) for item in result_assets)
    return (
        {
            "inline_examples": inline_examples,
            "result_assets": result_assets,
            "readme_sha256": _sha256(readme_path),
        },
        sorted(set(locations)),
    )
