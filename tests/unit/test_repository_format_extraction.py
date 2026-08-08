"""Prove repository-native format extraction is independent of development siblings."""

from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.repository_format_extraction import extract_repository_format_directions


def test_python_family_dispatch_returns_only_functional_directions(
    monkeypatch, tmp_path: Path
) -> None:
    observed: dict[str, object] = {}

    def corroborate(root, *, family, source_revision, formats):
        observed.update(
            root=root,
            family=family,
            source_revision=source_revision,
            formats=formats,
        )
        return [
            AsposeOrgFormatEvidenceV1(
                format="Gltf",
                direction="import",
                file="aspose/threed/formats/gltf/GltfImporter.py",
                line=21,
                functional=True,
            ),
            AsposeOrgFormatEvidenceV1(
                format="Obj",
                direction="enum_only",
                file="aspose/threed/FileFormat.py",
                line=10,
            ),
        ]

    monkeypatch.setattr(
        "readme_agent.facts.repository_format_extraction."
        "corroborate_python_family_format_directions",
        corroborate,
    )

    result = extract_repository_format_directions(
        tmp_path,
        platform="python",
        family="3d",
        source_revision="a" * 40,
    )

    assert result.status == "available"
    assert [item.format for item in result.formats] == ["Gltf"]
    assert observed == {
        "root": tmp_path,
        "family": "3d",
        "source_revision": "a" * 40,
        "formats": [],
    }


def test_unregistered_platform_fails_closed(tmp_path: Path) -> None:
    result = extract_repository_format_directions(
        tmp_path,
        platform="go",
        family="pdf",
        source_revision="b" * 40,
    )

    assert result.status == "unavailable"
    assert result.formats == []
