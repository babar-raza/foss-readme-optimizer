"""Select bounded, evidence-oriented repository context for product-truth drafting."""

from __future__ import annotations

from pathlib import Path

from readme_agent.inspection import file_inventory

ECOSYSTEM_SOURCE_GLOBS: dict[str, tuple[str, ...]] = {
    "java": ("*.java",),
    "net": ("*.cs",),
    "dotnet": ("*.cs",),
    "python": ("*.py",),
    "typescript": ("*.ts",),
    "go": ("*.go",),
    "cpp": ("*.h", "*.hpp", "*.cc", "*.cpp"),
    "rust": ("*.rs",),
}
DOC_GLOBS = ("*.md", "*.rst")
EXAMPLE_DIRECTORY_NAMES = frozenset(
    {"_examples", "demo", "demos", "example", "examples", "sample", "samples"}
)


def _is_noise_path(root: Path, path: Path) -> bool:
    return any(part in file_inventory.NOISE_DIRS for part in path.relative_to(root).parts)


def _is_example_source(root: Path, path: Path) -> bool:
    parts = {part.casefold() for part in path.relative_to(root).parts[:-1]}
    return bool(parts & EXAMPLE_DIRECTORY_NAMES)


def select_bounded_repo_context(
    root: Path,
    ecosystem: str | None,
    *,
    max_context_chars: int,
    max_file_excerpt_chars: int,
) -> str:
    """Return high-signal source evidence before broad implementation detail.

    README prose remains first because it is valuable product-owner evidence,
    but repository-owned examples are placed immediately after manifests.
    This gives the drafting model complete, source-backed usage before broad
    source scans while every claim remains subject to deterministic gates.
    """

    inventory = file_inventory.scan(root)
    sections: list[str] = []
    budget = max_context_chars

    def add(relative_path: str, text: str) -> bool:
        nonlocal budget
        excerpt = text[:max_file_excerpt_chars]
        block = f"--- {relative_path} ---\n{excerpt}\n"
        if len(block) > budget:
            return False
        sections.append(block)
        budget -= len(block)
        return True

    def read(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return None

    if inventory.readme_path is not None:
        text = read(inventory.readme_path)
        if text is not None:
            add(inventory.readme_path.relative_to(root).as_posix(), text)

    for _ecosystem_name, manifest_path in sorted(inventory.manifest_paths.items()):
        text = read(manifest_path)
        if text is not None:
            add(manifest_path.relative_to(root).as_posix(), text)

    source_candidates: set[Path] = set()
    for pattern in ECOSYSTEM_SOURCE_GLOBS.get(ecosystem or "", ()):
        source_candidates.update(root.rglob(pattern))
    doc_candidates: set[Path] = set()
    for pattern in DOC_GLOBS:
        doc_candidates.update(root.rglob(pattern))

    already_shown = {inventory.readme_path, *inventory.manifest_paths.values()}
    eligible_sources = {
        path
        for path in source_candidates
        if path.is_file() and path not in already_shown and not _is_noise_path(root, path)
    }
    example_sources = sorted(
        (path for path in eligible_sources if _is_example_source(root, path)),
        key=lambda path: (len(path.relative_to(root).parts), str(path)),
    )
    production_sources = sorted(
        (
            path
            for path in eligible_sources
            if path not in example_sources
            and not {"test", "tests"} & {part.casefold() for part in path.relative_to(root).parts}
            and not path.stem.casefold().endswith("_test")
        ),
        key=lambda path: (len(path.relative_to(root).parts), str(path)),
    )
    test_sources = sorted(
        (path for path in eligible_sources if path not in example_sources + production_sources),
        key=lambda path: (len(path.relative_to(root).parts), str(path)),
    )
    documentation = sorted(
        (
            path
            for path in doc_candidates
            if path.is_file()
            and path not in already_shown
            and path not in eligible_sources
            and not _is_noise_path(root, path)
        ),
        key=lambda path: (len(path.relative_to(root).parts), str(path)),
    )

    for path in [*example_sources, *production_sources, *test_sources, *documentation]:
        if budget <= 0:
            break
        text = read(path)
        if text is not None:
            add(path.relative_to(root).as_posix(), text)

    return "".join(sections) if sections else "(no repository context could be read)"
