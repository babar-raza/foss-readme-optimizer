"""Corroborate bounded Python Email format directions from public source and tests."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Literal

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_Direction = Literal["import", "export", "both", "detect", "enum_only", "none"]

_REVISION = re.compile(r"[0-9a-f]{40}")
_CFB_READER = "aspose/email_foss/cfb/reader.py"
_CFB_WRITER = "aspose/email_foss/cfb/writer.py"
_MSG_READER = "aspose/email_foss/msg/reader.py"
_MSG_WRITER = "aspose/email_foss/msg/writer.py"
_MAPI_MESSAGE = "aspose/email_foss/msg/mapi_message.py"


def corroborate_python_email_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Add only source-and-test-proven CFB, MSG, and EML format records.

    The repository-format extraction path always calls this with an empty
    ``formats`` seed (see ``extract_repository_format_directions``), so a
    prior version of this function -- which only ever *upgraded* entries
    already present in ``formats`` -- could never emit any evidence
    regardless of proof outcome. Proven directions are now appended fresh.
    """

    root = repository_root.resolve()
    original = [item.model_copy(update={"functional": None}) for item in formats]
    if not _revision_matches(root, source_revision):
        return original

    cfb_proven = _cfb_round_trip_is_proven(root)
    msg_proven = _msg_round_trip_is_proven(root)
    eml_export_proven = _eml_export_is_proven(root)
    result = [
        item.model_copy(update={"functional": True})
        if _record_is_proven(
            root,
            item,
            cfb_proven=cfb_proven,
            msg_proven=msg_proven,
            eml_export_proven=eml_export_proven,
        )
        else item
        for item in original
    ]

    existing: set[tuple[str, _Direction, str]] = {
        (item.format.casefold(), item.direction, item.file) for item in result
    }
    if cfb_proven:
        result = _append_proven_format(
            result, existing, root, "CFB", "import", _CFB_READER, "CFBReader", "from_file"
        )
        result = _append_proven_format(
            result, existing, root, "CFB", "export", _CFB_WRITER, "CFBWriter", "to_bytes"
        )
    if msg_proven:
        result = _append_proven_format(
            result, existing, root, "MSG", "import", _MSG_READER, "MsgReader", "from_file"
        )
        result = _append_proven_format(
            result, existing, root, "MSG", "export", _MSG_WRITER, "MsgWriter", "to_bytes"
        )
    if eml_export_proven:
        result = _append_proven_format(
            result,
            existing,
            root,
            "EML",
            "export",
            _MAPI_MESSAGE,
            "MapiMessage",
            "to_email_message",
        )

    if not _revision_matches(root, source_revision):
        return original
    return result


def _append_proven_format(
    result: list[AsposeOrgFormatEvidenceV1],
    existing: set[tuple[str, _Direction, str]],
    root: Path,
    format_name: str,
    direction: _Direction,
    file_path: str,
    class_name: str,
    method_name: str,
) -> list[AsposeOrgFormatEvidenceV1]:
    identity = (format_name.casefold(), direction, file_path)
    if identity in existing:
        return result
    module = _parse_relative(root, file_path)
    owner = _unique_class(module, class_name) if module is not None else None
    method = _unique_method_in_class(owner, method_name) if owner is not None else None
    if method is None:
        return result
    existing.add(identity)
    return [
        *result,
        AsposeOrgFormatEvidenceV1(
            format=format_name,
            direction=direction,
            file=file_path,
            line=method.lineno,
            functional=True,
        ),
    ]


def _record_is_proven(
    root: Path,
    item: AsposeOrgFormatEvidenceV1,
    *,
    cfb_proven: bool,
    msg_proven: bool,
    eml_export_proven: bool,
) -> bool:
    if not _safe_file(root, item.file):
        return False
    identity = (item.format.casefold(), item.direction, item.file)
    return (
        (
            cfb_proven
            and identity
            in {
                ("cfb", "import", _CFB_READER),
                ("cfb", "export", _CFB_WRITER),
            }
        )
        or (
            msg_proven
            and identity
            in {
                ("msg", "import", _MSG_READER),
                ("msg", "export", _MSG_WRITER),
            }
        )
        or (eml_export_proven and identity == ("eml", "export", _MAPI_MESSAGE))
    )


def _cfb_round_trip_is_proven(root: Path) -> bool:
    reader = _parse_relative(root, _CFB_READER)
    writer = _parse_relative(root, _CFB_WRITER)
    tests = _parse_relative(root, "tests/test_cfb_formats.py")
    if reader is None or writer is None or tests is None:
        return False
    reader_owner = _unique_class(reader, "CFBReader")
    writer_owner = _unique_class(writer, "CFBWriter")
    test = _unique_method(
        tests,
        "TestCFBFormats",
        "test_v3_round_trip_routes_small_streams_through_mini_stream",
    )
    if reader_owner is None or writer_owner is None or test is None:
        return False
    return all(
        (
            _unique_method_in_class(reader_owner, "from_file") is not None,
            _unique_method_in_class(writer_owner, "to_bytes") is not None,
            _unique_method_in_class(writer_owner, "write_file") is not None,
            {"CFBReader", "CFBWriter", "CFBDocument"} <= _name_references(test),
            {"to_bytes", "get_stream_data"} <= _called_attributes(test),
        )
    )


def _msg_round_trip_is_proven(root: Path) -> bool:
    reader = _parse_relative(root, _MSG_READER)
    writer = _parse_relative(root, _MSG_WRITER)
    message = _parse_relative(root, _MAPI_MESSAGE)
    tests = _parse_relative(root, "tests/test_msg_formats.py")
    if reader is None or writer is None or message is None or tests is None:
        return False
    reader_owner = _unique_class(reader, "MsgReader")
    writer_owner = _unique_class(writer, "MsgWriter")
    message_owner = _unique_class(message, "MapiMessage")
    test = _unique_method(
        tests,
        "TestMsgFormats",
        "test_high_level_message_round_trip_preserves_core_msg_structure",
    )
    if None in (reader_owner, writer_owner, message_owner, test):
        return False
    assert reader_owner is not None and writer_owner is not None and message_owner is not None
    assert test is not None
    return all(
        (
            _unique_method_in_class(reader_owner, "from_file") is not None,
            _unique_method_in_class(writer_owner, "to_bytes") is not None,
            _unique_method_in_class(writer_owner, "write_file") is not None,
            _unique_method_in_class(message_owner, "from_file") is not None,
            _unique_method_in_class(message_owner, "save") is not None,
            _unique_method_in_class(message_owner, "to_bytes") is not None,
            {"MapiMessage", "MsgReader", "MsgDocument"} <= _name_references(test),
            {"to_bytes", "from_reader", "from_msg_document"} <= _called_attributes(test),
        )
    )


def _eml_export_is_proven(root: Path) -> bool:
    message = _parse_relative(root, _MAPI_MESSAGE)
    tests = _parse_relative(root, "tests/test_msg_formats.py")
    example = _parse_relative(root, "examples/create_msg_and_eml.py")
    if message is None or tests is None or example is None:
        return False
    message_owner = _unique_class(message, "MapiMessage")
    test = _unique_method(
        tests,
        "TestMsgFormats",
        "test_email_message_conversion_round_trip",
    )
    main = _unique_function(example, "main")
    if message_owner is None or test is None or main is None:
        return False
    return all(
        (
            _unique_method_in_class(message_owner, "from_email_message") is not None,
            _unique_method_in_class(message_owner, "to_email_message") is not None,
            _unique_method_in_class(message_owner, "to_email_bytes") is not None,
            {"from_email_message", "to_email_message"} <= _called_attributes(test),
            {"from_file", "to_email_message", "write_bytes", "as_bytes"}
            <= _called_attributes(main),
        )
    )


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


def _unique_function(module: ast.Module, name: str) -> ast.FunctionDef | None:
    matches = [
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _unique_method(module: ast.Module, owner: str, name: str) -> ast.FunctionDef | None:
    class_node = _unique_class(module, owner)
    return _unique_method_in_class(class_node, name) if class_node is not None else None


def _unique_method_in_class(owner: ast.ClassDef, name: str) -> ast.FunctionDef | None:
    matches = [
        node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _name_references(node: ast.AST) -> set[str]:
    return {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}


def _called_attributes(node: ast.AST) -> set[str]:
    return {
        call.func.attr
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
    }


def _safe_file(root: Path, relative_path: str) -> bool:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return candidate.is_file()
