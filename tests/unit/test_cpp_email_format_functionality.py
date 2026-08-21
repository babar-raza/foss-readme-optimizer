"""C++ Email format directions require public APIs, implementations, and tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.cpp_email_format_functionality import (
    corroborate_cpp_email_format_directions,
)


def test_proves_cfb_msg_and_eml_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_cpp_email_format_directions(tmp_path, source_revision=revision)

    assert {(item.format, item.direction) for item in result} == {
        ("CFB", "import"),
        ("CFB", "export"),
        ("MSG", "import"),
        ("MSG", "export"),
        ("EML", "import"),
        ("EML", "export"),
    }
    assert all(item.functional is True for item in result)


def test_missing_test_proof_withholds_only_affected_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_eml_test=False)

    result = corroborate_cpp_email_format_directions(tmp_path, source_revision=revision)

    assert not any(item.format == "EML" for item in result)
    assert {(item.format, item.direction) for item in result} == {
        ("CFB", "import"),
        ("CFB", "export"),
        ("MSG", "import"),
        ("MSG", "export"),
    }


def test_reader_only_evidence_never_implies_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_cfb_writer=False)

    result = corroborate_cpp_email_format_directions(tmp_path, source_revision=revision)

    assert ("CFB", "import") in {(item.format, item.direction) for item in result}
    assert ("CFB", "export") not in {(item.format, item.direction) for item in result}


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    assert not corroborate_cpp_email_format_directions(tmp_path, source_revision="0" * 40)
    (tmp_path / "tests/test_msg.cpp").write_text("// dirty\n", encoding="utf-8")
    assert not corroborate_cpp_email_format_directions(tmp_path, source_revision=revision)


def _seed_repository(
    root: Path,
    *,
    include_eml_test: bool = True,
    include_cfb_writer: bool = True,
) -> str:
    cfb_writer_header = (
        "class cfb_writer { to_bytes(); write_file(); write_stream(); };\n"
        if include_cfb_writer
        else "class cfb_writer {};\n"
    )
    cfb_writer_source = (
        "cfb_writer::to_bytes(); cfb_writer::write_file(); cfb_writer::write_stream();\n"
        if include_cfb_writer
        else "\n"
    )
    eml_test = (
        "mapi_message::load_from_eml(stream); message.save_to_eml(stream);"
        if include_eml_test
        else ""
    )
    files = {
        "include/aspose/email/foss/cfb/cfb_reader.hpp": (
            "class cfb_reader { from_file(); from_stream(); from_bytes(); };\n"
        ),
        "src/cfb/cfb_reader.cpp": (
            "cfb_reader::from_file(); cfb_reader::from_stream(); cfb_reader::from_bytes();\n"
        ),
        "include/aspose/email/foss/cfb/cfb_writer.hpp": cfb_writer_header,
        "src/cfb/cfb_writer.cpp": cfb_writer_source,
        "tests/test_cfb.cpp": (
            "cfb_reader::from_bytes(); cfb_reader::from_stream(); cfb_reader::from_file(); "
            "cfb_writer::to_bytes(); cfb_writer::write_file(); cfb_writer::write_stream();\n"
        ),
        "include/aspose/email/foss/msg/mapi_message.hpp": (
            "class mapi_message { from_file(); from_stream(); save() const; "
            "save(std::ostream& stream) const; "
            "load_from_eml(const std::filesystem::path& path); "
            "load_from_eml(std::istream& stream); save_to_eml() const; "
            "save_to_eml(std::ostream& stream) const; };\n"
        ),
        "src/msg/mapi_message.cpp": (
            "mapi_message::from_file(); mapi_message::from_stream(); msg_reader::from_file(); "
            "mapi_message::save() const; msg_writer::to_bytes(); "
            "mapi_message::save(std::ostream& stream) const; "
            "mapi_message::load_from_eml(const std::filesystem::path& path); "
            "mapi_message::load_from_eml(std::istream& stream); "
            "mapi_message::save_to_eml() const; "
            "mapi_message::save_to_eml(std::ostream& stream) const;\n"
        ),
        "tests/test_msg.cpp": (
            "message.save(stream); mapi_message::from_stream(stream); " + eml_test + "\n"
        ),
    }
    for relative, content in files.items():
        path = root / relative
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
