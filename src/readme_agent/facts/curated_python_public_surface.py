"""Inspect Python packaging and expose a bounded README-facing API fact."""

from __future__ import annotations

import re
from pathlib import Path

from readme_agent.ecosystems.python_api_schema import PythonPackageLayoutV1
from readme_agent.ecosystems.python_package_layout import inspect_python_package_layout
from readme_agent.ecosystems.python_public_api import inspect_python_public_api
from readme_agent.facts.curated_python_api_projection import project_public_surface

_CODE_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _readme_selection_targets(root: Path) -> set[str]:
    """Use README code spans only to prioritize which source symbols are projected."""

    readme = next(
        (path for path in (root / "README.md", root / "readme.md") if path.is_file()), None
    )
    if readme is None:
        return set()
    text = readme.read_text(encoding="utf-8-sig", errors="replace")
    spans = re.findall(r"(?<!`)`([^`\n]+)`(?!`)", text)
    return {identifier for span in spans for identifier in _CODE_IDENTIFIER.findall(span)}


def _normalized_package_layout(root: Path) -> PythonPackageLayoutV1:
    """Recognize a conventional src layout when its manifest omits package-dir metadata."""

    layout = inspect_python_package_layout(root)
    if layout.source_root != "." or not (root / "src").is_dir():
        return layout
    src_packages = [
        path.removeprefix("src/") for path in layout.package_paths if path.startswith("src/")
    ]
    if not src_packages or len(src_packages) != len(layout.package_paths):
        return layout
    return layout.model_copy(
        update={
            "source_root": "src",
            "package_paths": src_packages,
            "canonical_import": layout.canonical_import.removeprefix("src."),
        }
    )


def python_public_surface(root: Path) -> tuple[object, list[str]] | None:
    """Project the typed extractor into the stable README accountability shape."""

    root = root.resolve()
    try:
        layout = _normalized_package_layout(root)
        surface = inspect_python_public_api(
            root,
            org_repo="repository/local",
            source_revision="fact-source-bound-separately",
            package=layout,
        )
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return None
    return project_public_surface(root, layout, surface, _readme_selection_targets(root))
