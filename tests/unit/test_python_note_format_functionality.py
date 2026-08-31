"""Python Note format evidence requires immutable public source, tests, and packaging.

PF-NOTE-FORMATS-001: `aspose-note-foss/Aspose.Note-FOSS-for-Python` had no registered family
corroborator at all, so its genuinely real PDF-export capability (`Document.Save()`,
documented and tested upstream with `PdfSaveOptions`/`reportlab`) never became a verified
`product.formats` fact -- the deterministic `format_direction_contradiction` gate then
correctly rejected the composer's (accurate) mention of PDF output as unauthorized. This
adds the missing corroborator; these tests prove it accepts the real capability and still
withholds it when any one of its three independent signals is missing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_note_format_functionality import (
    corroborate_python_note_format_directions,
)


def test_replaces_extractor_noise_with_proven_note_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_note_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[
            AsposeOrgFormatEvidenceV1(
                format="blob",
                direction="export",
                file="src/aspose/note/noise.py",
                line=1,
            )
        ],
    )

    assert [(item.format, item.direction, item.file, item.functional) for item in result] == [
        ("OneNote", "import", "src/aspose/note/model.py", True),
        ("PDF", "export", "src/aspose/note/model.py", True),
    ]


def test_missing_pdf_extra_declaration_withholds_only_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, declare_pdf_extra=False)

    result = corroborate_python_note_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert [(item.format, item.direction) for item in result] == [("OneNote", "import")]


def test_missing_save_test_withholds_only_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_save_test=False)

    result = corroborate_python_note_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert [(item.format, item.direction) for item in result] == [("OneNote", "import")]


def test_missing_construct_test_withholds_only_import(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_construct_test=False)

    result = corroborate_python_note_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert [(item.format, item.direction) for item in result] == [("PDF", "export")]


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_note_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_note_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(
    root: Path,
    *,
    include_save_test: bool = True,
    include_construct_test: bool = True,
    declare_pdf_extra: bool = True,
) -> str:
    model = """
class Document:
    def __init__(self, source, load_options=None):
        self.FirstChild = object()
        self.LastChild = object()

    def Save(self, target, format_or_options=None):
        target.write(b"%PDF-1.4 fixture output")
""".lstrip()

    document_tests = "import unittest\n\n\nclass TestAsposeNoteDocumentBasics(unittest.TestCase):\n"
    if include_construct_test:
        document_tests += """
    def test_construct_from_path(self) -> None:
        from aspose.note import Document

        doc = Document(self.path)
        self.assertIsNotNone(doc.FirstChild)
        self.assertIsNotNone(doc.LastChild)
"""
    else:
        document_tests += "    pass\n"

    save_tests = (
        "import io\nimport unittest\n\n\nclass TestAsposeNoteSaveWithOptions(unittest.TestCase):\n"
    )
    if include_save_test:
        save_tests += """
    def test_save_pdf_with_pdfsaveoptions(self) -> None:
        from aspose.note import Document
        from aspose.note.saving import PdfSaveOptions

        doc = Document(self.path)
        buf = io.BytesIO()
        doc.Save(buf, PdfSaveOptions())
        self.assertTrue(buf.getvalue().startswith(b"%PDF"))
"""
    else:
        save_tests += "    pass\n"

    pyproject = '[project]\nname = "aspose-note-foss"\nversion = "0.1.0"\n'
    if declare_pdf_extra:
        pyproject += '\n[project.optional-dependencies]\npdf = ["reportlab>=3.6"]\n'

    files = {
        "src/aspose/note/__init__.py": "from aspose.note.model import Document\n",
        "src/aspose/note/model.py": model,
        "tests/test_aspose_note_dom_document.py": document_tests,
        "tests/test_aspose_note_save_options.py": save_tests,
        "pyproject.toml": pyproject,
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
