"""Python Words format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.python_words_format_functionality import (
    corroborate_python_words_format_directions,
)


def test_replaces_extractor_noise_with_proven_words_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_words_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert {(item.format, item.direction) for item in result} == {
        ("DOCX", "import"),
        ("DOCX", "export"),
        ("PDF", "export"),
        ("MD", "import"),
        ("MD", "export"),
        ("DOC", "import"),
    }
    assert all(item.functional for item in result)


def test_missing_doc_test_withholds_only_doc(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="ApiExamples/loading_document.py")

    result = corroborate_python_words_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    remaining = {(item.format, item.direction) for item in result}
    assert ("DOC", "import") not in remaining
    assert ("DOCX", "import") in remaining
    assert ("MD", "export") in remaining


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_words_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_words_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(root: Path, *, omitted: str | None = None) -> str:
    files = {
        "aspose/words_foss/docx_reader/document_reader.py": """
class DocumentReader:
    def load_file(self, filepath):
        pass
""".lstrip(),
        "aspose/words_foss/docx_writer/writer.py": """
class LdmDocxWriter:
    def write(self, doc, output_path):
        pass
""".lstrip(),
        "aspose/words_foss/pdf_writer/writer.py": """
class LdmPdfWriter:
    def write(self, doc, output_path):
        pass
""".lstrip(),
        "aspose/words_foss/markdown_reader.py": """
class MarkdownReader:
    def load_file(self, filepath):
        pass
""".lstrip(),
        "aspose/words_foss/md_writer.py": """
class LdmMarkdownWriter:
    def write(self, doc, output_path):
        pass
""".lstrip(),
        "aspose/words_foss/doc_reader/doc_file_reader.py": """
class DocFileReader:
    def to_light_document(self):
        pass
""".lstrip(),
        "ApiExamples/loading_markdown.py": """
class LoadingMarkdown:
    def test_save_markdown_with_base64_image_to_docx_and_pdf(self):
        doc = aw.Document(io.BytesIO(b""), aw.loading.MarkdownLoadOptions())
        doc.save(docx_path, aw.SaveFormat.DOCX)
        doc.save(pdf_path, aw.SaveFormat.PDF)
        reloaded = aw.Document(docx_path)

    def test_markdown_round_trip_preserves_source(self):
        doc = aw.Document(io.BytesIO(b""), aw.loading.MarkdownLoadOptions())
        doc.save(out_path, aw.SaveFormat.MARKDOWN)
""".lstrip(),
        "ApiExamples/loading_document.py": """
class LoadingDocument:
    def test_open_document_from_file_doc_format(self):
        doc = aw.Document(MY_DIR + "test_bold.doc")
        assert len(doc.get_text()) > 0
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
