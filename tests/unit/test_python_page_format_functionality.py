"""Python Page format evidence requires immutable public source and real, calling tests.

PWD-011: `aspose-page-foss/Aspose.Page-FOSS-for-Python` had no registered family
corroborator at all, so its genuinely real PS/EPS-import, PS-to-PNG-export, XPS-import,
and XPS-to-PDF-export capabilities never became verified `product.formats` facts -- the
deterministic `format_direction_contradiction` gate then correctly rejected the composer's
(accurate) mentions of those directions as unauthorized. This adds the missing
corroborator; these tests prove it accepts the real capabilities and still withholds each
one independently when its proving test doesn't actually call the claimed method.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_page_format_functionality import (
    corroborate_python_page_format_directions,
)


def test_replaces_extractor_noise_with_proven_page_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_page_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[
            AsposeOrgFormatEvidenceV1(
                format="blob",
                direction="export",
                file="src/aspose/page/noise.py",
                line=1,
            )
        ],
    )

    assert [(item.format, item.direction, item.file, item.functional) for item in result] == [
        ("PS/EPS", "import", "src/aspose/page/ps/document.py", True),
        ("PNG", "export", "src/aspose/page/ps/document.py", True),
        ("XPS", "import", "src/aspose/page/xps/document.py", True),
        ("PDF", "export", "src/aspose/page/xps/document.py", True),
    ]


def test_ps_test_not_calling_to_image_withholds_only_png_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, ps_test_calls_to_image=False)

    result = corroborate_python_page_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert ("PNG", "export") not in [(item.format, item.direction) for item in result]
    assert ("PS/EPS", "import") in [(item.format, item.direction) for item in result]


def test_ps_test_not_calling_from_file_withholds_only_ps_import(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, ps_test_calls_from_file=False)

    result = corroborate_python_page_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert ("PS/EPS", "import") not in [(item.format, item.direction) for item in result]
    assert ("PNG", "export") in [(item.format, item.direction) for item in result]


def test_xps_test_not_calling_to_pdf_withholds_only_pdf_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, xps_test_calls_to_pdf=False)

    result = corroborate_python_page_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert ("PDF", "export") not in [(item.format, item.direction) for item in result]
    assert ("XPS", "import") in [(item.format, item.direction) for item in result]


def test_missing_ps_test_file_withholds_only_ps_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_ps_test=False)

    result = corroborate_python_page_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert [(item.format, item.direction) for item in result] == [
        ("XPS", "import"),
        ("PDF", "export"),
    ]


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_page_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_page_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(
    root: Path,
    *,
    include_ps_test: bool = True,
    ps_test_calls_from_file: bool = True,
    ps_test_calls_to_image: bool = True,
    xps_test_calls_to_pdf: bool = True,
) -> str:
    ps_document = """
class PsDocument:
    @classmethod
    def from_file(cls, path):
        return cls()

    def to_image(self, options=None):
        return b"\\x89PNG\\r\\n\\x1a\\nfixture"
""".lstrip()

    xps_document = """
class XpsDocument:
    @classmethod
    def from_file(cls, path):
        return cls()

    def to_pdf(self, options=None):
        return b"%PDF-1.4 fixture output"
""".lstrip()

    ps_from_file_call = (
        "doc = PsDocument.from_file(path)" if ps_test_calls_from_file else "doc = PsDocument()"
    )
    ps_to_image_call = "doc.to_image()" if ps_test_calls_to_image else "b'noop'"
    ps_test = f"""
import unittest

from aspose.page.ps.document import PsDocument


class TestPsRasterIntegration(unittest.TestCase):
    def test_ps_to_png_header(self) -> None:
        path = "testdata/ps/integration/minimal.ps"
        {ps_from_file_call}
        data = {ps_to_image_call}
        self.assertTrue(data.startswith(b"\\x89PNG"))
"""

    xps_to_pdf_call = "doc.to_pdf()" if xps_test_calls_to_pdf else "b'noop'"
    xps_test = f"""
import unittest

from aspose.page.xps.document import XpsDocument


class TestXpsIntegration(unittest.TestCase):
    def test_simple_xps_to_pdf(self) -> None:
        path = "testdata/xps/integration/Simple.xps"
        doc = XpsDocument.from_file(path)
        pdf = {xps_to_pdf_call}
        self.assertTrue(pdf.startswith(b"%PDF"))
"""

    files = {
        "src/aspose/page/ps/document.py": ps_document,
        "src/aspose/page/xps/document.py": xps_document,
        "tests/xps/test_xps_integration.py": xps_test,
    }
    if include_ps_test:
        files["tests/ps/test_ps_raster_integration.py"] = ps_test

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
