"""Corroborate Python Words directions from public source and round-trip tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_DOCX_READER = "aspose/words_foss/docx_reader/document_reader.py"
_DOCX_WRITER = "aspose/words_foss/docx_writer/writer.py"
_PDF_WRITER = "aspose/words_foss/pdf_writer/writer.py"
_MD_READER = "aspose/words_foss/markdown_reader.py"
_MD_WRITER = "aspose/words_foss/md_writer.py"
_DOC_READER = "aspose/words_foss/doc_reader/doc_file_reader.py"

_MARKDOWN_TESTS = "ApiExamples/loading_markdown.py"
_DOCUMENT_TESTS = "ApiExamples/loading_document.py"


def corroborate_python_words_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Add only source-and-test-proven Word document format records.

    Deliberately excludes several directions the real repository declares
    but does not genuinely, robustly support: DOC export (SaveFormat.DOC
    exists but Document.save() has no handler for it -- raises ValueError;
    confirmed absent, not merely unverified). RTF import (real, but only
    OLE2-container-wrapped RTF via delegation to the DOC reader -- not
    general plain-text RTF -- and only evidenced by a generic
    all-formats-in-a-loop test with a non-empty-text assertion, not a
    dedicated round trip). TXT import/export (only evidenced by the same
    generic loop test, no direct content assertion for the export side).
    """

    del formats
    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []

    docx_reader = _parse_relative(root, _DOCX_READER)
    docx_writer = _parse_relative(root, _DOCX_WRITER)
    pdf_writer = _parse_relative(root, _PDF_WRITER)
    md_reader = _parse_relative(root, _MD_READER)
    md_writer = _parse_relative(root, _MD_WRITER)
    doc_reader = _parse_relative(root, _DOC_READER)
    markdown_tests = _parse_relative(root, _MARKDOWN_TESTS)
    document_tests = _parse_relative(root, _DOCUMENT_TESTS)

    result: list[AsposeOrgFormatEvidenceV1] = []

    docx_pdf_test = (
        _unique_method(
            markdown_tests,
            "LoadingMarkdown",
            "test_save_markdown_with_base64_image_to_docx_and_pdf",
        )
        if markdown_tests is not None
        else None
    )
    if docx_pdf_test is not None:
        calls = _called_attributes(docx_pdf_test)
        attrs = _attribute_names(docx_pdf_test)
        docx_reader_load = (
            _unique_method(docx_reader, "DocumentReader", "load_file")
            if docx_reader is not None
            else None
        )
        docx_writer_write = (
            _unique_method(docx_writer, "LdmDocxWriter", "write")
            if docx_writer is not None
            else None
        )
        if (
            docx_reader_load is not None
            and docx_writer_write is not None
            and "Document" in calls
            and "save" in calls
            and "DOCX" in attrs
        ):
            result.append(
                AsposeOrgFormatEvidenceV1(
                    format="DOCX",
                    direction="import",
                    file=_DOCX_READER,
                    line=docx_reader_load.lineno,
                    functional=True,
                )
            )
            result.append(
                AsposeOrgFormatEvidenceV1(
                    format="DOCX",
                    direction="export",
                    file=_DOCX_WRITER,
                    line=docx_writer_write.lineno,
                    functional=True,
                )
            )

        pdf_writer_write = (
            _unique_method(pdf_writer, "LdmPdfWriter", "write") if pdf_writer is not None else None
        )
        if pdf_writer_write is not None and "save" in calls and "PDF" in attrs:
            result.append(
                AsposeOrgFormatEvidenceV1(
                    format="PDF",
                    direction="export",
                    file=_PDF_WRITER,
                    line=pdf_writer_write.lineno,
                    functional=True,
                )
            )

    md_roundtrip_test = (
        _unique_method(
            markdown_tests, "LoadingMarkdown", "test_markdown_round_trip_preserves_source"
        )
        if markdown_tests is not None
        else None
    )
    md_reader_load = (
        _unique_method(md_reader, "MarkdownReader", "load_file") if md_reader is not None else None
    )
    md_writer_write = (
        _unique_method(md_writer, "LdmMarkdownWriter", "write") if md_writer is not None else None
    )
    if (
        md_roundtrip_test is not None
        and md_reader_load is not None
        and md_writer_write is not None
        and "Document" in _called_attributes(md_roundtrip_test)
        and "save" in _called_attributes(md_roundtrip_test)
        and "MARKDOWN" in _attribute_names(md_roundtrip_test)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="MD",
                direction="import",
                file=_MD_READER,
                line=md_reader_load.lineno,
                functional=True,
            )
        )
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="MD",
                direction="export",
                file=_MD_WRITER,
                line=md_writer_write.lineno,
                functional=True,
            )
        )

    doc_import_test = (
        _unique_method(document_tests, "LoadingDocument", "test_open_document_from_file_doc_format")
        if document_tests is not None
        else None
    )
    doc_reader_load = (
        _unique_method(doc_reader, "DocFileReader", "to_light_document")
        if doc_reader is not None
        else None
    )
    if (
        doc_import_test is not None
        and doc_reader_load is not None
        and "Document" in _called_attributes(doc_import_test)
        and "get_text" in _called_attributes(doc_import_test)
    ):
        result.append(
            AsposeOrgFormatEvidenceV1(
                format="DOC",
                direction="import",
                file=_DOC_READER,
                line=doc_reader_load.lineno,
                functional=True,
            )
        )

    if not _revision_matches(root, source_revision):
        return []
    return result


def _revision_matches(root: Path, expected: str) -> bool:
    if _REVISION.fullmatch(expected) is None or not (root / ".git").is_dir():
        return False
    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return revision.stdout.strip().casefold() == expected.casefold() and not status.stdout.strip()


def _parse_relative(root: Path, relative_path: str) -> ast.Module | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
        return ast.parse(candidate.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError, ValueError):
        return None


def _unique_class(module: ast.Module, name: str) -> ast.ClassDef | None:
    matches = [node for node in module.body if isinstance(node, ast.ClassDef) and node.name == name]
    return matches[0] if len(matches) == 1 else None


def _unique_method(module: ast.Module, owner: str, name: str) -> ast.FunctionDef | None:
    class_node = _unique_class(module, owner)
    if class_node is None:
        return None
    matches = [
        node for node in class_node.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


def _attribute_names(node: ast.AST) -> set[str]:
    return {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}
