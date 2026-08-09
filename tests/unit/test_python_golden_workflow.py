"""Tests for source-derived Python golden-workflow facts."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.curated_readme_evidence import curated_repository_fact_candidates
from readme_agent.facts.python_golden_workflow import (
    collect_python_golden_workflow,
    python_golden_workflow_fact,
)

_REPOSITORY_ROOT = Path(__file__).parents[2]
_NOTE_ROOT = (
    _REPOSITORY_ROOT / "runs" / "baseline" / "aspose-note-foss__Aspose.Note-FOSS-for-Python"
)
_NOTE_REVISION = "6d97a522a9ed24708687911f1aabb76e2dea2da7"


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _generic_workflow(root: Path) -> None:
    _write(
        root,
        "pyproject.toml",
        """
[project]
name = "example"
version = "1.0.0"

[project.optional-dependencies]
render = ["reportlab>=4"]
test-render = ["Pillow>=10", "PyMuPDF>=1.25"]
""".lstrip(),
    )
    _write(root, "tests/goldens/images/alpha.manifest.json", "{}\n")
    _write(root, "tests/goldens/images/beta.png", "image\n")
    _write(
        root,
        "tests/_image_goldens.py",
        """
from pathlib import Path
import shutil
import subprocess
import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GOLDENS_DIR = ROOT / "tests" / "goldens" / "images"
FAILURES_DIR = ROOT / "tests" / "out" / "image_failures"
RENDERER = shutil.which("render-image")
HAS_PILLOW = True
HAS_PYMUPDF = True
HAS_PDFTOPPM = RENDERER is not None

class Case:
    def __init__(self, case_id):
        self.case_id = case_id

IMAGE_CASES = (Case("alpha"), Case("beta"))

def semantic_manifest(value):
    return value

def failure_manifest_path(case_id):
    return FAILURES_DIR / f"{case_id}.json"

def visual_diff_available():
    return HAS_PILLOW and (HAS_PYMUPDF or HAS_PDFTOPPM)

def create_visual_diff_artifacts():
    document = fitz.open("file.pdf")
    Image.open("file.png")
    subprocess.run([RENDERER])
    return document
""".lstrip(),
    )
    _write(
        root,
        "tools/regenerate_image_goldens.py",
        """
import argparse
from tests._image_goldens import IMAGE_CASES, semantic_manifest

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append")
    return parser.parse_args()

def selected_cases():
    return [semantic_manifest(case.case_id) for case in IMAGE_CASES]
""".lstrip(),
    )
    _write(
        root,
        "tests/test_image_goldens.py",
        """
import unittest
import reportlab
from tests._image_goldens import (
    IMAGE_CASES,
    create_visual_diff_artifacts,
    failure_manifest_path,
    semantic_manifest,
    visual_diff_available,
)

class TestImages(unittest.TestCase):
    def test_images(self):
        reportlab.Version
        for case in IMAGE_CASES:
            actual = semantic_manifest({"case": case.case_id})
            failure_manifest_path(case.case_id)
            if actual and visual_diff_available():
                create_visual_diff_artifacts()
            if not actual:
                self.fail("mismatch")
""".lstrip(),
    )
    _write(
        root,
        "src/package/renderer.py",
        """
import os

_RENDER_ENV = "PACKAGE_USE_SYSTEM_FONTS"
_BASE14_FONTS = {"sans": "Helvetica"}
_COMMON_FONT_DIRS = ("/fonts",)
_UNICODE_FONT_CANDIDATES = {"sans": "Unicode"}

def _use_system_fonts():
    value = os.environ.get(_RENDER_ENV, "")
    return value.lower() in {"1", "true"}

def _select_font(require_unicode=False):
    if not (_use_system_fonts() or require_unicode):
        return _BASE14_FONTS["sans"]
    for directory in _COMMON_FONT_DIRS:
        return directory, _UNICODE_FONT_CANDIDATES["sans"]
""".lstrip(),
    )


def test_collects_note_golden_workflow_from_repository_evidence() -> None:
    evidence = collect_python_golden_workflow(_NOTE_ROOT)

    assert evidence is not None
    assert evidence.artifact_inventory.root == "tests/goldens/pdf"
    assert evidence.artifact_inventory.count == 13
    assert evidence.regeneration_tool.path == "tools/regenerate_pdf_goldens.py"
    assert evidence.verification_test.path == "tests/test_aspose_note_pdf_goldens.py"
    assert evidence.helper_module.path == "tests/_pdf_goldens.py"
    assert [(item.kind, item.command) for item in evidence.commands[:2]] == [
        ("install_requirements", 'python -m pip install -e ".[pdf,test-pdf]"'),
        ("regenerate_all", "python tools/regenerate_pdf_goldens.py"),
    ]
    selected = [item for item in evidence.commands if item.kind == "regenerate_selected"]
    assert len(selected) == 12
    assert all(item.case_id and item.case_id in item.command for item in selected)
    assert "<case-id>" not in "\n".join(item.command for item in evidence.commands)
    assert (evidence.commands[-1].kind, evidence.commands[-1].command) == (
        "verify",
        "python -m unittest tests.test_aspose_note_pdf_goldens -v",
    )
    assert evidence.case_ids == (
        "attached_file_with_tag",
        "formatted_richtext",
        "image_with_tag",
        "images_with_alignment",
        "numbered_list_with_tags",
        "one_page_with_file",
        "page_with_subpage",
        "simple_history",
        "simple_image_from_separate_file",
        "simple_table",
        "table_with_tag",
        "tag_sizes",
    )
    assert evidence.representative_case_ids == ("formatted_richtext", "simple_table")
    assert "README.md" in {item.path for item in evidence.source_files}
    assert evidence.comparison_mode == "semantic_manifest"
    assert evidence.failure_output_path == "tests/out/pdf_golden_failures"
    assert [item.name for item in evidence.environment_controls] == [
        "ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS"
    ]
    assert evidence.environment_controls[0].enabled_values == ("1", "on", "true", "yes")
    assert [(item.name, item.mechanism) for item in evidence.renderer_fallbacks] == [
        ("PyMuPDF", "python_import"),
        ("pdftoppm", "executable"),
    ]
    assert [(group.name, group.requirements) for group in evidence.dependency_groups] == [
        ("pdf", ("reportlab>=3.6",)),
        ("test-pdf", ("pypdf>=5.3", "Pillow>=10.0", "PyMuPDF>=1.25")),
    ]
    assert evidence.visual_diff_policy.required_python_packages == ("Pillow",)
    assert evidence.visual_diff_policy.renderer_any_of == ("PyMuPDF", "pdftoppm")
    assert evidence.font_policy is not None
    assert evidence.font_policy.default_strategy == "built_in_fonts_unless_unicode_required"
    assert evidence.font_policy.enabled_strategy == "search_system_font_directories"
    assert all(len(item.sha256) == 64 for item in evidence.source_files)


def test_projects_revision_bound_verified_fact() -> None:
    fact = python_golden_workflow_fact(_NOTE_ROOT, source_revision=_NOTE_REVISION)

    assert fact is not None
    assert fact.fact_id == "development.golden_workflow:python-source"
    assert fact.field == "development.golden_workflow"
    assert fact.source.source_type == "mechanical_test"
    assert fact.source.source_revision == _NOTE_REVISION
    assert "tests/_pdf_goldens.py" in fact.source.location
    assert fact.verification_state == "verified"
    assert fact.authoritative_owner == "repository-owner"
    assert fact.confidence == 1.0
    assert fact.affected_surfaces == ["readme.development_and_testing"]
    assert fact.value["artifact_inventory"]["count"] == 13


def test_shared_curated_collector_registers_the_typed_workflow() -> None:
    selected = {
        fact.field: fact
        for fact in curated_repository_fact_candidates(
            _NOTE_ROOT,
            _NOTE_REVISION,
            None,
            ecosystem="python",
        )
    }

    assert selected["development.golden_workflow"].source.source_revision == _NOTE_REVISION


def test_collects_product_neutral_fixture_and_is_deterministic(tmp_path: Path) -> None:
    _generic_workflow(tmp_path)

    first = collect_python_golden_workflow(tmp_path)
    second = collect_python_golden_workflow(tmp_path)

    assert first is not None
    assert first == second
    assert first.artifact_inventory.root == "tests/goldens/images"
    assert first.artifact_inventory.count == 2
    assert first.case_ids == ("alpha", "beta")
    assert first.representative_case_ids == ()
    assert first.failure_output_path == "tests/out/image_failures"
    assert [item.name for item in first.environment_controls] == ["PACKAGE_USE_SYSTEM_FONTS"]
    assert [(item.name, item.identifier) for item in first.renderer_fallbacks] == [
        ("PyMuPDF", "fitz"),
        ("render-image", "render-image"),
    ]
    assert [group.name for group in first.dependency_groups] == ["render", "test-render"]
    assert first.font_policy is not None


def test_representative_cases_require_one_valid_fenced_source_selection(tmp_path: Path) -> None:
    _generic_workflow(tmp_path)
    _write(
        tmp_path,
        "README.md",
        """
```bash
python tools/regenerate_image_goldens.py --case beta --case alpha
```
""".lstrip(),
    )

    evidence = collect_python_golden_workflow(tmp_path)

    assert evidence is not None
    assert evidence.representative_case_ids == ("beta", "alpha")
    assert "README.md" in {item.path for item in evidence.source_files}

    _write(
        tmp_path,
        "README.md",
        "`python tools/regenerate_image_goldens.py --case beta --case alpha`\n",
    )
    prose_only = collect_python_golden_workflow(tmp_path)
    assert prose_only is not None
    assert prose_only.representative_case_ids == ()

    _write(
        tmp_path,
        "README.md",
        """
```bash
python tools/regenerate_image_goldens.py --case alpha --case unknown
```
""".lstrip(),
    )
    invalid = collect_python_golden_workflow(tmp_path)
    assert invalid is not None
    assert invalid.representative_case_ids == ()
    assert "README.md" not in {item.path for item in invalid.source_files}


def test_readme_claim_alone_cannot_create_golden_workflow(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "README.md",
        "Run tools/regenerate_goldens.py and python -m unittest tests.test_goldens.\n",
    )

    assert collect_python_golden_workflow(tmp_path) is None


def test_unlinked_files_fail_closed(tmp_path: Path) -> None:
    _write(tmp_path, "tests/goldens/pdf/example.json", "{}\n")
    _write(
        tmp_path,
        "tools/regenerate_goldens.py",
        "import argparse\np = argparse.ArgumentParser()\np.add_argument('--case')\n",
    )
    _write(tmp_path, "tests/test_goldens.py", "import unittest\n")

    assert collect_python_golden_workflow(tmp_path) is None


def test_imported_but_uncalled_verifier_contract_fails_closed(tmp_path: Path) -> None:
    _generic_workflow(tmp_path)
    _write(
        tmp_path,
        "tests/test_image_goldens.py",
        """
import unittest
from tests._image_goldens import (
    IMAGE_CASES,
    create_visual_diff_artifacts,
    failure_manifest_path,
    semantic_manifest,
    visual_diff_available,
)

class TestImages(unittest.TestCase):
    def test_placeholder(self):
        contract = (
            IMAGE_CASES,
            create_visual_diff_artifacts,
            failure_manifest_path,
            semantic_manifest,
            visual_diff_available,
        )
        self.assertTrue(contract)
""".lstrip(),
    )

    assert collect_python_golden_workflow(tmp_path) is None


def test_declared_case_without_a_golden_artifact_fails_closed(tmp_path: Path) -> None:
    _generic_workflow(tmp_path)
    (tmp_path / "tests/goldens/images/beta.png").unlink()

    assert collect_python_golden_workflow(tmp_path) is None


def test_unused_environment_constant_is_not_reported(tmp_path: Path) -> None:
    _generic_workflow(tmp_path)
    _write(
        tmp_path,
        "src/package/renderer.py",
        '_UNUSED_ENV = "PACKAGE_USE_SYSTEM_FONTS"\n',
    )

    evidence = collect_python_golden_workflow(tmp_path)

    assert evidence is not None
    assert evidence.environment_controls == ()
    assert evidence.font_policy is None


def test_multiple_source_linked_workflows_fail_closed(tmp_path: Path) -> None:
    _generic_workflow(tmp_path)
    _write(
        tmp_path,
        "tools/regenerate_more_goldens.py",
        """
import argparse
from tests._image_goldens import IMAGE_CASES, semantic_manifest
p = argparse.ArgumentParser()
p.add_argument("--case")
(IMAGE_CASES, semantic_manifest)
""".lstrip(),
    )

    assert collect_python_golden_workflow(tmp_path) is None
