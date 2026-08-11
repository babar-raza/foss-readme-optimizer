"""Python Font format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.python_font_format_functionality import (
    corroborate_python_font_format_directions,
)


def test_replaces_extractor_noise_with_proven_font_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_python_font_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert {(item.format, item.direction) for item in result} == {
        ("TTF", "import"),
        ("TTF", "export"),
        ("OTF", "import"),
        ("CFF", "import"),
        ("CFF", "export"),
        ("TYPE1", "import"),
        ("TYPE1", "export"),
        ("TYPE1_PFA", "import"),
        ("WOFF", "import"),
        ("WOFF", "export"),
        ("WOFF2", "import"),
        ("WOFF2", "export"),
        ("EOT", "import"),
        ("EOT", "export"),
    }
    assert all(item.functional for item in result)


def test_missing_serializer_tests_withholds_ttf_cff_type1_eot_only(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="tests/test_serializer.py")

    result = corroborate_python_font_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    remaining = {(item.format, item.direction) for item in result}
    assert remaining == {
        ("OTF", "import"),
        ("TYPE1_PFA", "import"),
        ("WOFF", "import"),
        ("WOFF", "export"),
        ("WOFF2", "import"),
        ("WOFF2", "export"),
    }


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_font_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=[],
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_font_format_directions(
        tmp_path,
        source_revision=revision,
        formats=[],
    )

    assert wrong == []
    assert dirty == []


def _seed_repository(root: Path, *, omitted: str | None = None) -> str:
    files = {
        "src/aspose_font/ttf/font.py": """
class TtfFont:
    @classmethod
    def _from_reader(cls, reader, font_type=None):
        return cls()

    def to_bytes(self, font_type=None):
        return b'ttf'
""".lstrip(),
        "src/aspose_font/cff/font.py": """
class CffFont:
    @classmethod
    def _from_bytes(cls, data):
        return cls()

    def to_bytes(self, font_type=None):
        return b'cff'
""".lstrip(),
        "src/aspose_font/type1/font.py": """
class Type1Font:
    @classmethod
    def _from_source(cls, data):
        return cls()

    def to_bytes(self, font_type=None):
        return b'type1'
""".lstrip(),
        "src/aspose_font/woff/woff1.py": """
class WoffFont:
    @classmethod
    def _from_reader(cls, reader):
        return cls()

    def to_bytes(self, font_type=None):
        return b'woff'
""".lstrip(),
        "src/aspose_font/woff/woff2.py": """
class Woff2Font:
    @classmethod
    def _from_reader(cls, reader):
        return cls()

    def to_bytes(self, font_type=None):
        return b'woff2'
""".lstrip(),
        "src/aspose_font/eot/font.py": """
class EotFont:
    @classmethod
    def _from_reader(cls, reader):
        return cls()

    def to_bytes(self, font_type=None):
        return b'eot'
""".lstrip(),
        "tests/test_serializer.py": """
from aspose_font import CffFont, EotFont, FontLoader, FontType, Type1Font

def test_ttf_save_roundtrip(tmp_path, roboto_path):
    font = FontLoader.open(str(roboto_path))
    out_path = tmp_path / "out.ttf"
    font.save(str(out_path))
    loaded = FontLoader.open(str(out_path))
    assert loaded.num_glyphs == font.num_glyphs


def test_cff_save_roundtrip(opensans_cff):
    data = opensans_cff.to_bytes(FontType.CFF)
    reloaded = FontLoader.open(data, font_type=FontType.CFF)
    assert isinstance(reloaded, CffFont)


def test_type1_pfb_roundtrip(opensans_pfb_path):
    font = FontLoader.open(str(opensans_pfb_path))
    assert isinstance(font, Type1Font)
    data = font.to_bytes(FontType.TYPE1)
    reloaded = FontLoader.open(data)
    assert isinstance(reloaded, Type1Font)


def test_eot_save_roundtrip(saira_eot):
    data = saira_eot.to_bytes()
    reloaded = FontLoader.open(data, font_type=FontType.EOT)
    assert isinstance(reloaded, EotFont)
""".lstrip(),
        "tests/test_loader.py": """
from aspose_font import FontLoader, FontType, TtfFont, Type1Font

class TestLoaderMagicDetection:
    def test_otf_magic_detected(self):
        font = FontLoader.open(b"OTTO")
        assert isinstance(font, TtfFont)
        assert font.font_type == FontType.OTF

    def test_pfa_magic_detected(self):
        font = FontLoader.open(b"%!PS-AdobeFont-1.0")
        assert isinstance(font, Type1Font)
""".lstrip(),
        "tests/test_woff.py": """
from aspose_font import FontConverter, FontLoader, FontType, WoffFont, Woff2Font

def test_woff_roundtrip(saira_woff):
    blob = saira_woff.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, WoffFont)


def test_woff2_project_generated_roundtrip():
    source = FontLoader.open("testdata/Fonts/Roboto-Regular.ttf")
    converted = FontConverter.convert(source, FontType.WOFF2)
    blob = converted.to_bytes()
    rt = FontLoader.open(blob)
    assert isinstance(rt, Woff2Font)
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
