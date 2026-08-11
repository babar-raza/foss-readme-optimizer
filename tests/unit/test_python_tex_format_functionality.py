"""Python TeX format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.python_tex_format_functionality import (
    corroborate_python_tex_format_directions,
)


def test_replaces_extractor_noise_with_proven_tex_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_tex_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert {(item.format, item.direction) for item in result} == {
        ("TEX", "import"),
        ("DVI", "export"),
        ("PDF", "export"),
        ("SVG", "export"),
    }
    assert all(item.functional for item in result)


def test_missing_pdf_test_withholds_only_pdf(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="tests/test_presentation_pdf_integration.py")

    result = corroborate_python_tex_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert {(item.format, item.direction) for item in result} == {
        ("TEX", "import"),
        ("DVI", "export"),
        ("SVG", "export"),
    }


def test_unparseable_source_fails_closed_not_crash(tmp_path: Path) -> None:
    """A repository whose committed source is not valid Python (e.g. the real
    upstream aspose-tex-foss corruption discovered this session -- indentation
    collapsed to a uniform single space, destroying nested block structure,
    confirmed present in the actual upstream repository via an independent
    fresh clone and a direct HTTPS raw-content fetch, not a local artifact)
    must yield an empty result, never raise. Every proof in this module reads
    at least one of these two files, so corrupting both simulates the real,
    repository-wide scope of the actual defect.
    """
    _seed_repository(tmp_path)
    corrupted = (
        "class FileInputSource(InputSource):\n"
        ' """Docstring at the same indentation as its class -- a syntax error."""\n'
    )
    (tmp_path / "src/aspose_tex/_input/reader.py").write_text(corrupted, encoding="utf-8")
    (tmp_path / "src/aspose_tex/presentation/__init__.py").write_text(corrupted, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Readme Agent Test",
            "-c",
            "user.email=readme-agent@example.invalid",
            "commit",
            "-qm",
            "corrupt",
        ],
        check=True,
    )
    revision = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = corroborate_python_tex_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert result == []


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_tex_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_tex_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(root: Path, *, omitted: str | None = None) -> str:
    files = {
        "src/aspose_tex/_input/reader.py": """
class FileInputSource:
    def read_line(self):
        return None
""".lstrip(),
        "src/aspose_tex/presentation/__init__.py": """
class DviDevice:
    def get_bytes(self):
        return b'dvi'


class PdfDevice:
    def get_bytes(self):
        return b'%PDF-1.4'


class SvgDevice:
    def get_bytes(self):
        return b'<?xml'


class TeXJob:
    def run(self):
        return b''
""".lstrip(),
        "tests/test_e2e_dvi_baseline.py": """
def _run(fixture):
    source = FileInputSource(fixture)
    job = TeXJob(source, DviDevice(), options=TeXOptions(load_format="plain"))
    dvi = job.run()
    return dvi
""".lstrip(),
        "tests/test_presentation_pdf_integration.py": """
def test_texjob_pdf_hello_world():
    result = TeXJob(StringInputSource("Hello"), PdfDevice(), options=_NO_FORMAT).run()
    assert result.startswith(b"%PDF-1.4")
    assert result.endswith(b"%%EOF\\n")
""".lstrip(),
        "tests/test_presentation_svg_integration.py": """
def test_texjob_svg_hello_world():
    result = TeXJob(StringInputSource("Hello"), SvgDevice(), options=_NO_FORMAT).run()
    assert result.startswith(b"<?xml")
    root = ET.fromstring(result)
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
