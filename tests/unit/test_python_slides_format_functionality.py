"""Python Slides format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.python_slides_format_functionality import (
    corroborate_python_slides_format_directions,
)


def test_replaces_extractor_noise_with_proven_slides_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_slides_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert {(item.format, item.direction) for item in result} == {
        ("PPTX", "import"),
        ("PPTX", "export"),
        ("MD", "export"),
    }
    assert all(item.functional for item in result)


def test_missing_markdown_test_withholds_only_markdown(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="tests/test_markdown_export.py")

    result = corroborate_python_slides_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert {(item.format, item.direction) for item in result} == {
        ("PPTX", "import"),
        ("PPTX", "export"),
    }


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_slides_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_slides_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(root: Path, *, omitted: str | None = None) -> str:
    files = {
        "aspose/slides_foss/_internal/opc/opc_package.py": """
class OpcPackage:
    @classmethod
    def open(cls, source):
        return cls()

    def save(self, destination):
        pass
""".lstrip(),
        "aspose/slides_foss/Presentation.py": """
class Presentation:
    def __init__(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        pass
""".lstrip(),
        "aspose/slides_foss/_internal/export/markdown/writers.py": """
def save_presentation_to_markdown(presentation, destination, slides_numbers=None, options=None):
    pass
""".lstrip(),
        "tests/conftest.py": """
from aspose.slides_foss import Presentation
from aspose.slides_foss.export import SaveFormat
import pytest

@pytest.fixture()
def tmp_pptx(tmp_path):
    def _save_and_reopen(pres):
        path = str(tmp_path / "roundtrip.pptx")
        pres.save(path, SaveFormat.PPTX)
        pres.dispose()
        return Presentation(path)

    return _save_and_reopen
""".lstrip(),
        "tests/test_markdown_export.py": """
from aspose.slides_foss import Presentation
from aspose.slides_foss.export import SaveFormat

def test_save_to_file_path(tmp_path):
    with Presentation() as pres:
        path = str(tmp_path / "out.md")
        pres.save(path, SaveFormat.MD)
        with open(path, encoding="utf-8") as f:
            assert f.read()
""".lstrip(),
    }
    for relative_path, content in files.items():
        if relative_path == omitted:
            continue
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Readme Agent Test",
            "-c",
            "user.email=readme-agent@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=root,
        check=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
