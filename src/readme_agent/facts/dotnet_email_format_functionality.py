"""Corroborate Email .NET MSG and EML directions from immutable public source."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pygments import lex
from pygments.lexers.dotnet import CSharpLexer
from pygments.token import Comment, Literal

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1

_REVISION = re.compile(r"[0-9a-f]{40}")
_MAPI_MESSAGE = "src/Aspose.Email.Foss/Msg/MapiMessage.cs"
_MSG_READER = "src/Aspose.Email.Foss/Msg/MsgReader.cs"
_MSG_WRITER = "src/Aspose.Email.Foss/Msg/MsgWriter.cs"
_MIME_READER = "src/Aspose.Email.Foss/Msg/Mime/MimeReader.cs"
_MIME_WRITER = "src/Aspose.Email.Foss/Msg/Mime/MimeWriter.cs"
_SOURCE_FILES = (_MAPI_MESSAGE, _MSG_READER, _MSG_WRITER, _MIME_READER, _MIME_WRITER)


@dataclass(frozen=True)
class DotnetEmailFormatSourceV1:
    """Exact revision and source-byte identities used for corroboration."""

    source_revision: str
    source_files: dict[str, str]

    def canonical_sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.source_revision.encode("ascii"))
        digest.update(b"\0")
        for path, checksum in sorted(self.source_files.items()):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(checksum.encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()


def dotnet_email_format_source(
    repository_root: Path,
    *,
    source_revision: str,
) -> DotnetEmailFormatSourceV1 | None:
    """Return source hashes only for an exact clean repository revision."""

    root = repository_root.resolve()
    if not _revision_matches(root, source_revision):
        return None
    files: dict[str, str] = {}
    for relative in _SOURCE_FILES:
        try:
            files[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        except OSError:
            return None
    if not _revision_matches(root, source_revision):
        return None
    return DotnetEmailFormatSourceV1(source_revision=source_revision, source_files=files)


def corroborate_dotnet_email_format_directions(
    repository_root: Path,
    *,
    source_revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Promote only MSG/EML directions backed by complete public method pairs."""

    root = repository_root.resolve()
    original = [item.model_copy(update={"functional": None}) for item in formats]
    source_receipt = dotnet_email_format_source(root, source_revision=source_revision)
    if source_receipt is None:
        return original
    try:
        source = (root / _MAPI_MESSAGE).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return original
    structural = _structural_source(source)
    msg_proven = _msg_pair_is_public(structural)
    eml_proven = _eml_pair_is_public(structural)
    result = [
        item.model_copy(update={"functional": True})
        if _record_is_proven(root, item, msg_proven=msg_proven, eml_proven=eml_proven)
        else item
        for item in original
    ]
    if dotnet_email_format_source(root, source_revision=source_revision) != source_receipt:
        return original
    return result


def _structural_source(source: str) -> str:
    parts: list[str] = []
    for token_type, value in lex(source, CSharpLexer()):
        if token_type in Comment or token_type in Literal.String:
            parts.append("".join("\n" if character == "\n" else " " for character in value))
        else:
            parts.append(value)
    return "".join(parts)


def _method_body(source: str, signature: str) -> str | None:
    matches = list(re.finditer(rf"{signature}\s*\{{", source, flags=re.MULTILINE))
    if len(matches) != 1:
        return None
    opening = source.find("{", matches[0].start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    return None


def _body_has(source: str, signature: str, *tokens: str) -> bool:
    body = _method_body(source, signature)
    return body is not None and all(token in body for token in tokens)


def _msg_pair_is_public(source: str) -> bool:
    if "public sealed partial class MapiMessage" not in source:
        return False
    return all(
        (
            _body_has(
                source,
                r"public\s+static\s+MapiMessage\s+FromFile\s*\(\s*string\b[^)]*\)",
                "MsgReader.FromFile(",
                "FromMsgDocument(",
            ),
            _body_has(
                source,
                r"public\s+static\s+MapiMessage\s+FromStream\s*\(\s*Stream\b[^)]*\)",
                "MsgReader.FromStream(",
                "FromMsgDocument(",
            ),
            _body_has(
                source,
                r"public\s+byte\[\]\s+Save\s*\(\s*\)",
                "MsgWriter.ToBytes(",
                "ToMsgDocument(",
            ),
            _body_has(source, r"public\s+void\s+Save\s*\(\s*string\b[^)]*\)", "Save()"),
            _body_has(source, r"public\s+void\s+Save\s*\(\s*Stream\b[^)]*\)", "Save()"),
        )
    )


def _eml_pair_is_public(source: str) -> bool:
    return all(
        (
            _body_has(
                source,
                r"public\s+static\s+MapiMessage\s+LoadFromEml\s*\(\s*string\b[^)]*\)",
                "LoadFromEml(",
            ),
            _body_has(
                source,
                r"public\s+static\s+MapiMessage\s+LoadFromEml\s*\(\s*Stream\b[^)]*\)",
                "LoadFromEml(",
            ),
            _body_has(
                source,
                r"public\s+static\s+MapiMessage\s+LoadFromEml\s*\(\s*byte\[\]\s+\w+\s*\)",
                "MimeReader()",
                ".Read(",
                "EmlMessageMapper.ToMapiMessage(",
            ),
            _body_has(
                source,
                r"public\s+byte\[\]\s+SaveToEml\s*\(\s*\)",
                "EmlMessageMapper.ToMimeMessage(",
                "MimeWriter()",
                ".Write(",
            ),
            _body_has(
                source,
                r"public\s+void\s+SaveToEml\s*\(\s*string\b[^)]*\)",
                "SaveToEml()",
            ),
            _body_has(
                source,
                r"public\s+void\s+SaveToEml\s*\(\s*Stream\b[^)]*\)",
                "SaveToEml()",
            ),
        )
    )


def _record_is_proven(
    root: Path,
    item: AsposeOrgFormatEvidenceV1,
    *,
    msg_proven: bool,
    eml_proven: bool,
) -> bool:
    normalized = "".join(character for character in item.format.casefold() if character.isalnum())
    identity = (normalized, item.direction, item.file.replace("\\", "/"))
    expected = {
        ("msg", "import", _MSG_READER): msg_proven,
        ("msg", "export", _MSG_WRITER): msg_proven,
        ("eml", "import", _MIME_READER): eml_proven,
        ("eml", "export", _MIME_WRITER): eml_proven,
        ("mime", "import", _MIME_READER): eml_proven,
        ("mime", "export", _MIME_WRITER): eml_proven,
    }
    return expected.get(identity, False) and _safe_source_line(root, identity[2], item.line)


def _safe_source_line(root: Path, relative: str, line: int) -> bool:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
        lines = candidate.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError, ValueError):
        return False
    return 1 <= line <= len(lines)


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
