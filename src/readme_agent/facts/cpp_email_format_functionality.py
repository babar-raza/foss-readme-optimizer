"""Prove C++ Email format directions from immutable public source and tests."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal as TypingLiteral

from pygments import lex
from pygments.lexers.c_cpp import CppLexer
from pygments.token import Comment, Literal

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_MAPI_HEADER = "include/aspose/email/foss/msg/mapi_message.hpp"
_MAPI_SOURCE = "src/msg/mapi_message.cpp"
_CFB_READER_HEADER = "include/aspose/email/foss/cfb/cfb_reader.hpp"
_CFB_READER_SOURCE = "src/cfb/cfb_reader.cpp"
_CFB_WRITER_HEADER = "include/aspose/email/foss/cfb/cfb_writer.hpp"
_CFB_WRITER_SOURCE = "src/cfb/cfb_writer.cpp"
_CFB_TEST = "tests/test_cfb.cpp"
_MSG_TEST = "tests/test_msg.cpp"
_SOURCE_FILES = (
    _MAPI_HEADER,
    _MAPI_SOURCE,
    _CFB_READER_HEADER,
    _CFB_READER_SOURCE,
    _CFB_WRITER_HEADER,
    _CFB_WRITER_SOURCE,
    _CFB_TEST,
    _MSG_TEST,
)


@dataclass(frozen=True)
class _DirectionSpec:
    format: str
    direction: TypingLiteral["import", "export"]
    evidence_path: str
    declaration_tokens: tuple[str, ...]
    implementation_tokens: tuple[str, ...]
    test_tokens: tuple[str, ...]


_SPECS = (
    _DirectionSpec(
        "CFB",
        "import",
        _CFB_READER_HEADER,
        ("class cfb_reader", "from_file(", "from_stream(", "from_bytes("),
        ("cfb_reader::from_file(", "cfb_reader::from_stream(", "cfb_reader::from_bytes("),
        ("cfb_reader::from_bytes(", "cfb_reader::from_stream(", "cfb_reader::from_file("),
    ),
    _DirectionSpec(
        "CFB",
        "export",
        _CFB_WRITER_HEADER,
        ("class cfb_writer", "to_bytes(", "write_file(", "write_stream("),
        ("cfb_writer::to_bytes(", "cfb_writer::write_file(", "cfb_writer::write_stream("),
        ("cfb_writer::to_bytes(", "cfb_writer::write_file(", "cfb_writer::write_stream("),
    ),
    _DirectionSpec(
        "MSG",
        "import",
        _MAPI_HEADER,
        ("class mapi_message", "from_file(", "from_stream("),
        ("mapi_message::from_file(", "mapi_message::from_stream(", "msg_reader::from_file("),
        ("mapi_message::from_stream(",),
    ),
    _DirectionSpec(
        "MSG",
        "export",
        _MAPI_HEADER,
        ("class mapi_message", "save() const", "save(std::ostream& stream) const"),
        (
            "mapi_message::save() const",
            "msg_writer::to_bytes(",
            "mapi_message::save(std::ostream& stream) const",
        ),
        ("message.save(",),
    ),
    _DirectionSpec(
        "EML",
        "import",
        _MAPI_HEADER,
        ("load_from_eml(const std::filesystem::path& path)", "load_from_eml(std::istream& stream)"),
        (
            "mapi_message::load_from_eml(const std::filesystem::path& path)",
            "mapi_message::load_from_eml(std::istream& stream)",
        ),
        ("mapi_message::load_from_eml(",),
    ),
    _DirectionSpec(
        "EML",
        "export",
        _MAPI_HEADER,
        ("save_to_eml() const", "save_to_eml(std::ostream& stream) const"),
        (
            "mapi_message::save_to_eml() const",
            "mapi_message::save_to_eml(std::ostream& stream) const",
        ),
        ("save_to_eml(",),
    ),
)


def corroborate_cpp_email_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
) -> list[AsposeOrgFormatEvidenceV1]:
    """Return only directions proven by public declarations, implementations, and tests."""

    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return []
    sources = _load_structural_sources(root)
    if sources is None:
        return []
    result: list[AsposeOrgFormatEvidenceV1] = []
    for spec in _SPECS:
        declaration = sources[spec.evidence_path]
        implementation_path = _implementation_path(spec)
        test_path = _CFB_TEST if spec.format == "CFB" else _MSG_TEST
        if not all(token in declaration for token in spec.declaration_tokens):
            continue
        if not all(token in sources[implementation_path] for token in spec.implementation_tokens):
            continue
        if not all(token in sources[test_path] for token in spec.test_tokens):
            continue
        result.append(
            AsposeOrgFormatEvidenceV1(
                format=spec.format,
                direction=spec.direction,
                file=spec.evidence_path,
                line=_line_of(root / spec.evidence_path, spec.declaration_tokens[-1]),
                functional=True,
            )
        )
    if not _revision_matches(root, source_revision):
        return []
    return result


def _implementation_path(spec: _DirectionSpec) -> str:
    if spec.format == "CFB":
        return _CFB_READER_SOURCE if spec.direction == "import" else _CFB_WRITER_SOURCE
    return _MAPI_SOURCE


def _load_structural_sources(root: Path) -> dict[str, str] | None:
    result: dict[str, str] = {}
    try:
        for relative in _SOURCE_FILES:
            source = (root / relative).read_text(encoding="utf-8-sig")
            result[relative] = _structural_source(source)
    except (OSError, UnicodeError):
        return None
    return result


def _structural_source(source: str) -> str:
    parts: list[str] = []
    for token_type, value in lex(source, CppLexer()):
        if token_type in Comment or token_type in Literal.String:
            parts.append("".join("\n" if character == "\n" else " " for character in value))
        else:
            parts.append(value)
    return "".join(parts)


def _line_of(path: Path, token: str) -> int:
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if token in line:
            return number
    return 1


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


__all__ = ["corroborate_cpp_email_format_directions"]
