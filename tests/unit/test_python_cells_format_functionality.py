"""Python Cells format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_cells_format_functionality import (
    corroborate_python_cells_format_directions,
)


def test_replaces_extractor_noise_with_proven_cells_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_cells_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[
            AsposeOrgFormatEvidenceV1(
                format="blob",
                direction="export",
                file="aspose/cells_foss/noise.py",
                line=1,
            )
        ],
    )

    assert [(item.format, item.direction, item.functional) for item in result] == [
        ("XLSX", "export", True),
        ("XLSX", "import", True),
        ("CSV", "export", True),
        ("CSV", "import", True),
        ("JSON", "export", True),
        ("MARKDOWN", "export", True),
    ]


def test_missing_csv_roundtrip_test_withholds_only_csv(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_csv_roundtrip_test=False)

    result = corroborate_python_cells_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert [(item.format, item.direction) for item in result] == [
        ("XLSX", "export"),
        ("XLSX", "import"),
        ("JSON", "export"),
        ("MARKDOWN", "export"),
    ]


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_cells_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_cells_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(root: Path, *, include_csv_roundtrip_test: bool = True) -> str:
    workbook = """
class Workbook:
    def __init__(self, file_path=None):
        self._file_path = file_path
        if file_path:
            self._load(file_path)

    def _load(self, file_path):
        self._loaded_from = file_path

    def save(self, file_path):
        pass

    def save_as_csv(self, file_path):
        pass

    def load_csv(self, file_path):
        pass

    def save_as_json(self, file_path):
        pass

    def save_as_markdown(self, file_path):
        pass
""".lstrip()
    csv_roundtrip_test = """
class TestCSVBasicImportExport(unittest.TestCase):
    def test_csv_roundtrip(self):
        wb = Workbook()
        wb.save_as_csv("out.csv")
        wb2 = Workbook()
        wb2.load_csv("out.csv")
"""
    files = {
        "aspose/cells_foss/__init__.py": "from .workbook import Workbook\n",
        "aspose/cells_foss/workbook.py": workbook,
        "examples/test_cell_protection_locked.py": (
            "import unittest\n"
            "from aspose.cells_foss import Workbook\n\n"
            "class TestCellProtectionLocked(unittest.TestCase):\n"
            "    def test_cell_locked_false_roundtrip(self):\n"
            "        wb = Workbook()\n"
            "        wb.save('out.xlsx')\n"
            "        wb_loaded = Workbook('out.xlsx')\n"
        ),
        "examples/test_csv_import_export.py": (
            "import unittest\n"
            "from aspose.cells_foss import Workbook\n\n"
            + (csv_roundtrip_test if include_csv_roundtrip_test else "")
        ),
        "examples/test_xlsx_to_json.py": (
            "import unittest\n"
            "from aspose.cells_foss import Workbook\n\n"
            "class TestXLSXToJSONConversion(unittest.TestCase):\n"
            "    def test_sales_report_to_json(self):\n"
            "        wb = Workbook('input.xlsx')\n"
            "        wb.save_as_json('out.json')\n"
        ),
        "examples/test_xlsx_to_markdown.py": (
            "import unittest\n"
            "from aspose.cells_foss import Workbook\n\n"
            "class TestXLSXToMarkdownConversion(unittest.TestCase):\n"
            "    def test_convert_all_xlsx_to_markdown(self):\n"
            "        wb = Workbook('input.xlsx')\n"
            "        wb.save_as_markdown('out.md')\n"
        ),
    }
    for relative_path, content in files.items():
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
