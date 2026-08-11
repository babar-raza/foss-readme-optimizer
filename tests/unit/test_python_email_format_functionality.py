"""Python Email format evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_email_format_functionality import (
    corroborate_python_email_format_directions,
)


def test_corroborates_only_source_and_test_proven_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = _records()

    result = corroborate_python_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=records,
    )

    functional = {
        (item.format.casefold(), item.direction, item.file)
        for item in result
        if item.functional is True
    }
    assert functional == {
        ("cfb", "import", "aspose/email_foss/cfb/reader.py"),
        ("cfb", "export", "aspose/email_foss/cfb/writer.py"),
        ("msg", "import", "aspose/email_foss/msg/reader.py"),
        ("msg", "export", "aspose/email_foss/msg/writer.py"),
        ("eml", "export", "aspose/email_foss/msg/mapi_message.py"),
    }
    eml_input = next(item for item in result if item.direction == "import" and item.format == "eml")
    assert eml_input.functional is None


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_python_email_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=_records(),
    )
    (tmp_path / "untracked.txt").write_text("dirty", encoding="utf-8")
    dirty = corroborate_python_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=_records(),
    )

    assert not any(item.functional is True for item in wrong)
    assert not any(item.functional is True for item in dirty)


def test_missing_cfb_test_withholds_only_cfb_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="tests/test_cfb_formats.py")

    result = corroborate_python_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=_records(),
    )

    assert not any(item.format == "CFB" and item.functional is True for item in result)
    assert any(item.format == "Msg" and item.functional is True for item in result)
    assert any(
        item.format == "eml" and item.direction == "export" and item.functional is True
        for item in result
    )


def test_missing_eml_example_withholds_only_eml_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="examples/create_msg_and_eml.py")

    result = corroborate_python_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=_records(),
    )

    assert not any(item.format == "eml" and item.functional is True for item in result)
    assert any(item.format == "Msg" and item.functional is True for item in result)


def test_unsafe_and_unrecognized_preapproved_records_are_sanitized(tmp_path: Path) -> None:
    """Unsafe/unproven pre-seeded records never get upgraded to functional=True.

    The seeded repository fully proves CFB, MSG, and EML export (same fixture as
    test_corroborates_only_source_and_test_proven_directions), so the corroborator
    independently appends those 5 proven directions regardless of what was
    pre-seeded -- only the two specific pre-seeded records under test here (an
    unsafe path-traversal file, and a real file claiming an unproven direction)
    must stay unproven.
    """
    revision = _seed_repository(tmp_path)
    records = [
        AsposeOrgFormatEvidenceV1(
            format="PDF",
            direction="export",
            file="../outside.py",
            line=1,
            functional=True,
        ),
        AsposeOrgFormatEvidenceV1(
            format="eml",
            direction="import",
            file="aspose/email_foss/msg/mapi_message.py",
            line=1,
            functional=True,
        ),
    ]

    result = corroborate_python_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=records,
    )

    unsafe_pdf = next(item for item in result if item.format == "PDF")
    unproven_eml_import = next(
        item for item in result if item.format == "eml" and item.direction == "import"
    )
    assert unsafe_pdf.functional is None
    assert unproven_eml_import.functional is None


def _records() -> list[AsposeOrgFormatEvidenceV1]:
    return [
        _record("CFB", "import", "aspose/email_foss/cfb/reader.py"),
        _record("CFB", "export", "aspose/email_foss/cfb/writer.py"),
        _record("Msg", "import", "aspose/email_foss/msg/reader.py"),
        _record("Msg", "export", "aspose/email_foss/msg/writer.py"),
        _record("eml", "import", "aspose/email_foss/msg/mapi_message.py"),
        _record("eml", "export", "aspose/email_foss/msg/mapi_message.py"),
    ]


def _record(name: str, direction: str, file: str) -> AsposeOrgFormatEvidenceV1:
    return AsposeOrgFormatEvidenceV1(format=name, direction=direction, file=file, line=1)


def _seed_repository(root: Path, *, omitted: str | None = None) -> str:
    files = {
        "aspose/email_foss/cfb/reader.py": """
class CFBReader:
    @classmethod
    def from_file(cls, path):
        return cls(path.read_bytes())
""".lstrip(),
        "aspose/email_foss/cfb/writer.py": """
class CFBWriter:
    @classmethod
    def to_bytes(cls, document):
        return b'data'

    @classmethod
    def write_file(cls, document, path):
        path.write_bytes(cls.to_bytes(document))
""".lstrip(),
        "aspose/email_foss/msg/reader.py": """
class MsgReader:
    @classmethod
    def from_file(cls, path):
        return cls(CFBReader.from_file(path))
""".lstrip(),
        "aspose/email_foss/msg/writer.py": """
class MsgWriter:
    @classmethod
    def to_bytes(cls, document):
        return b'data'

    @classmethod
    def write_file(cls, document, path):
        path.write_bytes(cls.to_bytes(document))
""".lstrip(),
        "aspose/email_foss/msg/mapi_message.py": """
class MapiMessage:
    @classmethod
    def from_file(cls, path):
        return cls()

    @classmethod
    def from_email_message(cls, message):
        return cls()

    def save(self, path):
        MsgWriter.write_file(self, path)

    def to_bytes(self):
        return MsgWriter.to_bytes(self)

    def to_email_message(self):
        return EmailMessage()

    def to_email_bytes(self):
        return self.to_email_message().as_bytes()
""".lstrip(),
        "tests/test_cfb_formats.py": """
class TestCFBFormats:
    def test_v3_round_trip_routes_small_streams_through_mini_stream(self):
        reader = CFBReader(CFBWriter.to_bytes(CFBDocument()))
        assert reader.get_stream_data(1)
""".lstrip(),
        "tests/test_msg_formats.py": """
class TestMsgFormats:
    def test_high_level_message_round_trip_preserves_core_msg_structure(self):
        message = MapiMessage()
        reader = MsgReader(message.to_bytes())
        document = MsgDocument.from_reader(reader)
        assert MapiMessage.from_msg_document(document)

    def test_email_message_conversion_round_trip(self):
        message = MapiMessage.from_email_message(EmailMessage())
        assert message.to_email_message()
""".lstrip(),
        "examples/create_msg_and_eml.py": """
def main():
    with MapiMessage.from_file(args.msg_path) as loaded:
        message = loaded.to_email_message()
        args.eml_path.write_bytes(message.as_bytes())
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
