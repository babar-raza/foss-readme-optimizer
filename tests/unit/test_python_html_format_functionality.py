"""Python HTML format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_html_format_functionality import (
    corroborate_python_html_format_directions,
)


def test_replaces_extractor_noise_with_proven_html_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_html_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[
            AsposeOrgFormatEvidenceV1(
                format="blob",
                direction="export",
                file="src/aspose_html/dom/noise.py",
                line=1,
            )
        ],
    )

    assert [(item.format, item.direction, item.file, item.functional) for item in result] == [
        ("HTML", "import", "src/aspose_html/html_document.py", True),
        ("HTML", "export", "src/aspose_html/dom/_document.py", True),
    ]


def test_missing_round_trip_test_withholds_only_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_save_test=False)

    result = corroborate_python_html_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert [(item.format, item.direction) for item in result] == [("HTML", "import")]


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_html_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_html_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(root: Path, *, include_save_test: bool = True) -> str:
    tests = """
from aspose_html.dom import Document
from aspose_html.html_document import HTMLDocument

def test_load_returns_document(tmp_path):
    html_file = tmp_path / "page.html"
    html_file.write_bytes(b"<p>Hello</p>")
    doc = HTMLDocument.load(html_file)
    assert isinstance(doc, Document)
""".lstrip()
    if include_save_test:
        tests += """

def test_save_round_trip(tmp_path):
    doc = HTMLDocument.parse("<p>Round trip</p>")
    out_file = tmp_path / "out.html"
    doc.save(out_file)
    content = out_file.read_text(encoding="utf-8")
    doc2 = HTMLDocument.parse(content)
    assert doc2.get_elements_by_tag_name("p")
"""
    files = {
        "src/aspose_html/__init__.py": "from aspose_html.html_document import HTMLDocument\n",
        "src/aspose_html/dom/__init__.py": "from aspose_html.dom._document import Document\n",
        "src/aspose_html/html_document.py": """
class HTMLDocument:
    @classmethod
    def load(cls, path):
        return cls.parse(path.read_bytes())
""".lstrip(),
        "src/aspose_html/dom/_document.py": """
class Document:
    def save(self, path, encoding="utf-8"):
        path.write_text(self.serialise(), encoding=encoding)
""".lstrip(),
        "tests/test_file_io.py": tests,
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
