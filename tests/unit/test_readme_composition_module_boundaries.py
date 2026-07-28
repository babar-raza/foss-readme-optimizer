"""Enforce responsibility and public-seam boundaries for README composition."""

from __future__ import annotations

import ast
from pathlib import Path

from readme_agent.readme.agentic_composition import (
    ReadmeAgenticCompositionPlanV1,
    plan_readme_composition,
    validate_readme_composition_plan,
)
from readme_agent.readme.document_renderer import (
    apply_document_operations,
    build_readme_document_candidate,
    document_template_hash,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_ROOT = PROJECT_ROOT / "src/readme_agent/readme"
RESPONSIBILITY_MODULES = (
    "agentic_composition.py",
    "agentic_composition_models.py",
    "agentic_composition_grounding.py",
    "agentic_composition_validation.py",
    "document_renderer.py",
    "document_render_context.py",
    "document_opening.py",
    "document_limitations.py",
    "document_acquisition.py",
    "document_examples.py",
    "document_release.py",
)


def test_extracted_modules_respect_size_and_public_import_boundaries() -> None:
    for name in RESPONSIBILITY_MODULES:
        path = README_ROOT / name
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 300, name
        tree = ast.parse(source, filename=str(path))
        private_sibling_imports = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").startswith("readme_agent.readme.")
            for alias in node.names
            if alias.name.startswith("_")
        ]
        assert private_sibling_imports == [], (name, private_sibling_imports)


def test_public_composition_facades_remain_importable() -> None:
    assert plan_readme_composition.__module__ == "readme_agent.readme.agentic_composition"
    assert (
        validate_readme_composition_plan.__module__
        == "readme_agent.readme.agentic_composition_validation"
    )
    assert (
        ReadmeAgenticCompositionPlanV1.__module__
        == "readme_agent.readme.agentic_composition_models"
    )
    assert build_readme_document_candidate.__module__ == "readme_agent.readme.document_renderer"
    assert apply_document_operations.__module__ == "readme_agent.readme.document_operations"
    assert document_template_hash.__module__ == "readme_agent.readme.document_templates"


def test_only_public_facades_orchestrate_composition_and_document_operations() -> None:
    agentic_source = (README_ROOT / "agentic_composition.py").read_text(encoding="utf-8")
    renderer_source = (README_ROOT / "document_renderer.py").read_text(encoding="utf-8")
    sibling_sources = [
        (README_ROOT / name).read_text(encoding="utf-8")
        for name in RESPONSIBILITY_MODULES
        if name not in {"agentic_composition.py", "document_renderer.py"}
    ]

    assert "resolved_client.call(" in agentic_source
    assert "apply_document_operations(" in renderer_source
    assert all("resolved_client.call(" not in source for source in sibling_sources)
    assert all("apply_document_operations(" not in source for source in sibling_sources)
