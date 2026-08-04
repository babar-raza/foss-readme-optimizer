"""Email .NET format claims require immutable public MapiMessage method pairs."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.dotnet_email_format_functionality import (
    corroborate_dotnet_email_format_directions,
    dotnet_email_format_source,
)


def test_corroborates_only_msg_and_eml_public_method_pairs(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    result = corroborate_dotnet_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=_records(),
    )

    assert {
        (item.format.casefold(), item.direction) for item in result if item.functional is True
    } == {
        ("msg", "import"),
        ("msg", "export"),
        ("mime", "import"),
        ("mime", "export"),
        ("eml", "import"),
        ("eml", "export"),
    }
    assert not any(item.format in {"Cfb", "Pdf"} and item.functional for item in result)
    receipt = dotnet_email_format_source(tmp_path, source_revision=revision)
    assert receipt is not None
    assert set(receipt.source_files) == {
        "src/Aspose.Email.Foss/Msg/MapiMessage.cs",
        "src/Aspose.Email.Foss/Msg/MsgReader.cs",
        "src/Aspose.Email.Foss/Msg/MsgWriter.cs",
        "src/Aspose.Email.Foss/Msg/Mime/MimeReader.cs",
        "src/Aspose.Email.Foss/Msg/Mime/MimeWriter.cs",
    }
    assert len(receipt.canonical_sha256()) == 64


def test_wrong_revision_and_dirty_source_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong = corroborate_dotnet_email_format_directions(
        tmp_path,
        source_revision="0" * 40,
        formats=_records(),
    )
    (tmp_path / "src/Aspose.Email.Foss/Msg/MapiMessage.cs").write_text(
        "// dirty source\n", encoding="utf-8"
    )
    dirty = corroborate_dotnet_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=_records(),
    )

    assert not any(item.functional is True for item in wrong)
    assert not any(item.functional is True for item in dirty)
    assert dotnet_email_format_source(tmp_path, source_revision=revision) is None


def test_missing_eml_save_pair_withholds_both_eml_directions(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, include_eml_export=False)

    result = corroborate_dotnet_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=_records(),
    )

    assert not any(
        item.format.casefold() in {"eml", "mime"} and item.functional is True for item in result
    )
    assert {
        item.direction for item in result if item.format == "Msg" and item.functional is True
    } == {"import", "export"}


def test_mismatched_path_or_source_line_is_not_promoted(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        _record("Msg", "import", "src/Aspose.Email.Foss/Msg/Mime/MimeReader.cs"),
        _record("Msg", "export", "src/Aspose.Email.Foss/Msg/MsgWriter.cs", line=999),
        _record("Cfb", "import", "src/Aspose.Email.Foss/Cfb/CfbReader.cs", functional=True),
    ]

    result = corroborate_dotnet_email_format_directions(
        tmp_path,
        source_revision=revision,
        formats=records,
    )

    assert all(item.functional is None for item in result)


def _records() -> list[AsposeOrgFormatEvidenceV1]:
    return [
        _record("Cfb", "import", "src/Aspose.Email.Foss/Cfb/CfbReader.cs", functional=True),
        _record("Msg", "import", "src/Aspose.Email.Foss/Msg/MsgReader.cs"),
        _record("Msg", "export", "src/Aspose.Email.Foss/Msg/MsgWriter.cs"),
        _record("Mime", "import", "src/Aspose.Email.Foss/Msg/Mime/MimeReader.cs"),
        _record("Mime", "export", "src/Aspose.Email.Foss/Msg/Mime/MimeWriter.cs"),
        _record("Eml", "import", "src/Aspose.Email.Foss/Msg/Mime/MimeReader.cs"),
        _record("Eml", "export", "src/Aspose.Email.Foss/Msg/Mime/MimeWriter.cs"),
        _record("Pdf", "export", "src/Aspose.Email.Foss/Msg/MsgWriter.cs", functional=True),
    ]


def _record(
    name: str,
    direction: str,
    file: str,
    *,
    line: int = 1,
    functional: bool | None = None,
) -> AsposeOrgFormatEvidenceV1:
    return AsposeOrgFormatEvidenceV1(
        format=name,
        direction=direction,
        file=file,
        line=line,
        functional=functional,
    )


def _seed_repository(root: Path, *, include_eml_export: bool = True) -> str:
    eml_export = (
        """
    public byte[] SaveToEml()
    {
        var model = EmlMessageMapper.ToMimeMessage(this);
        return new MimeWriter().Write(model);
    }
    public void SaveToEml(string path) { File.WriteAllBytes(path, SaveToEml()); }
    public void SaveToEml(Stream stream) { stream.Write(SaveToEml()); }
"""
        if include_eml_export
        else ""
    )
    files = {
        "src/Aspose.Email.Foss/Msg/MapiMessage.cs": f"""
public sealed partial class MapiMessage
{{
    public static MapiMessage FromFile(string path, bool strict = false)
    {{
        using var reader = MsgReader.FromFile(path, strict);
        return FromMsgDocument(MsgDocument.FromReader(reader));
    }}
    public static MapiMessage FromStream(Stream stream, bool strict = false)
    {{
        using var reader = MsgReader.FromStream(stream, strict);
        return FromMsgDocument(MsgDocument.FromReader(reader));
    }}
    public byte[] Save() {{ return MsgWriter.ToBytes(ToMsgDocument()); }}
    public void Save(string path) {{ File.WriteAllBytes(path, Save()); }}
    public void Save(Stream stream) {{ stream.Write(Save()); }}
    public static MapiMessage LoadFromEml(string path)
    {{
        return LoadFromEml(File.ReadAllBytes(path));
    }}
    public static MapiMessage LoadFromEml(Stream stream) {{ return LoadFromEml(ReadAll(stream)); }}
    public static MapiMessage LoadFromEml(byte[] data)
    {{
        var model = new MimeReader().Read(data);
        return EmlMessageMapper.ToMapiMessage(model);
    }}
{eml_export}
}}
""".lstrip(),
        "src/Aspose.Email.Foss/Msg/MsgReader.cs": "public sealed class MsgReader {{}}\n",
        "src/Aspose.Email.Foss/Msg/MsgWriter.cs": "public static class MsgWriter {{}}\n",
        "src/Aspose.Email.Foss/Msg/Mime/MimeReader.cs": "internal sealed class MimeReader {{}}\n",
        "src/Aspose.Email.Foss/Msg/Mime/MimeWriter.cs": "internal sealed class MimeWriter {{}}\n",
        "src/Aspose.Email.Foss/Cfb/CfbReader.cs": "public sealed class CfbReader {{}}\n",
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
