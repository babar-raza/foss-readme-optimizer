"""Python barcode output evidence requires immutable public source and matching tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_barcode_format_functionality import (
    corroborate_python_barcode_format_directions,
)


def test_adds_only_mechanically_proven_png_and_svg_exports(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        AsposeOrgFormatEvidenceV1(
            format="PNG",
            direction="enum_only",
            file="src/aspose_barcode_foss/result.py",
            line=1,
            functional=True,
        ),
        AsposeOrgFormatEvidenceV1(
            format="PDF",
            direction="export",
            file="../outside.py",
            line=1,
            functional=True,
        ),
        _record("Barcode content", "import", "src/aspose_barcode_foss/api.py"),
    ]

    result = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=records
    )

    functional = {
        (item.format, item.direction, item.file) for item in result if item.functional is True
    }
    assert functional == {
        ("PNG", "export", "src/aspose_barcode_foss/result.py"),
        ("SVG", "export", "src/aspose_barcode_foss/result.py"),
    }
    assert result[0].model_copy(update={"functional": True}) == records[0]
    assert result[1].model_copy(update={"functional": True}) == records[1]
    assert result[2] == records[2]
    assert result[0].functional is None
    assert result[1].functional is None
    assert result[2].functional is None


def test_does_not_duplicate_existing_functional_export(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)
    records = [
        AsposeOrgFormatEvidenceV1(
            format="png",
            direction="export",
            file="src/aspose_barcode_foss/result.py",
            line=10,
            functional=True,
        )
    ]

    result = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=records
    )

    assert len([item for item in result if item.format.casefold() == "png"]) == 1
    assert any(item.format == "SVG" and item.functional is True for item in result)


def test_wrong_revision_and_dirty_tree_fail_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path)

    wrong_revision = corroborate_python_barcode_format_directions(
        tmp_path, source_revision="0" * 40, formats=[]
    )
    (tmp_path / "untracked.txt").write_text("changes the evidence tree", encoding="utf-8")
    dirty = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=[]
    )

    assert wrong_revision == []
    assert dirty == []


def test_missing_matching_test_proves_only_the_remaining_output(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, omitted="tests/rendering/test_barcode_svg.py")

    result = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=[]
    )

    assert [(item.format, item.direction) for item in result] == [("PNG", "export")]


def test_missing_renderer_source_proves_only_the_remaining_output(tmp_path: Path) -> None:
    revision = _seed_repository(
        tmp_path, omitted="src/aspose_barcode_foss/_internal/renderers/png.py"
    )

    result = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=[]
    )

    assert [(item.format, item.direction) for item in result] == [("SVG", "export")]


def test_ambiguous_public_result_contract_fails_closed(tmp_path: Path) -> None:
    revision = _seed_repository(tmp_path, duplicate_barcode=True)

    result = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=[]
    )

    assert result == []


def test_missing_input_pipeline_proof_fails_all_outputs_closed(tmp_path: Path) -> None:
    revision = _seed_repository(
        tmp_path,
        omitted="tests/api/test_barcode_service.py",
    )

    result = corroborate_python_barcode_format_directions(
        tmp_path, source_revision=revision, formats=[]
    )

    assert result == []


def _record(format_name: str, direction: str, file: str) -> AsposeOrgFormatEvidenceV1:
    return AsposeOrgFormatEvidenceV1(
        format=format_name,
        direction=direction,
        file=file,
        line=1,
    )


def _seed_repository(
    root: Path,
    *,
    omitted: str | None = None,
    duplicate_barcode: bool = False,
) -> str:
    files = {
        "src/aspose_barcode_foss/api.py": _API,
        "src/aspose_barcode_foss/_internal/service.py": _SERVICE,
        "src/aspose_barcode_foss/result.py": _RESULT
        + ("\nclass Barcode:\n    pass\n" if duplicate_barcode else ""),
        "src/aspose_barcode_foss/_internal/renderers/png.py": _renderer(
            "PngRenderer", "png", "image/png", "bytes"
        ),
        "src/aspose_barcode_foss/_internal/renderers/svg.py": _renderer(
            "SvgRenderer", "svg", "image/svg+xml", "str"
        ),
        "tests/api/test_api_entrypoints.py": _API_TEST,
        "tests/api/test_barcode_service.py": _SERVICE_TEST,
        "tests/rendering/test_barcode_png.py": _integration_test("png", "bytes"),
        "tests/rendering/test_barcode_svg.py": _integration_test("svg", "str"),
        "tests/rendering/test_png_renderer.py": _renderer_test(
            "png", "PngRenderer", "image/png", "bytes"
        ),
        "tests/rendering/test_svg_renderer.py": _renderer_test(
            "svg", "SvgRenderer", "image/svg+xml", "str"
        ),
    }
    for relative_path, content in files.items():
        if relative_path != omitted:
            _write(root / relative_path, content)
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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


_API = """
def generate(symbology: str, data: str | bytes):
    return _get_default_service().generate(symbology, data)
""".lstrip()

_SERVICE = """
class BarcodeService:
    def generate(self, symbology: str, data: str | bytes):
        definition = self.registry.get_definition(symbology)
        payload = definition.parser.parse(data)
        symbol = definition.encoder.encode(payload)
        return Barcode(symbol=symbol, profile=definition.profile)
""".lstrip()

_RESULT = """
class Barcode:
    def render(self, renderer):
        return renderer.render(self.symbol)

    def to_png(self) -> bytes:
        artifact = self.render(PngRenderer())
        if artifact.backend != "png" or artifact.media_type != "image/png":
            raise ValueError
        return artifact.data

    def to_svg(self) -> str:
        artifact = self.render(SvgRenderer())
        if artifact.backend != "svg" or artifact.media_type != "image/svg+xml":
            raise ValueError
        return artifact.data

    def to_pdf(self) -> bytes:
        raise NotImplementedError
""".lstrip()

_API_TEST = """
def test_generate_delegates_to_the_default_service():
    result = api.generate("CODE-128", b"ABC123")
    assert result
""".lstrip()

_SERVICE_TEST = """
def test_barcode_service_runs_parse_before_encode_and_forwards_encode_options():
    barcode = service.generate("CODE-128", "ABC123")
    assert events == ["parse", "encode"]
    assert barcode
""".lstrip()


def _renderer(class_name: str, backend: str, media_type: str, data_type: str) -> str:
    value = "b'data'" if data_type == "bytes" else "'<svg/>'"
    return f"""
class {class_name}:
    def render(self, symbol):
        pixels = symbol.matrix
        return RenderedArtifact(data={value}, media_type={media_type!r}, backend={backend!r})
""".lstrip()


def _integration_test(backend: str, return_type: str) -> str:
    return f"""
def test_barcode_to_{backend}_returns_{return_type}():
    barcode = make_barcode()
    result = barcode.to_{backend}()
    assert isinstance(result, {return_type})
""".lstrip()


def _renderer_test(backend: str, class_name: str, media_type: str, data_type: str) -> str:
    return f"""
def test_{backend}_renderer_returns_correct_artifact_fields():
    artifact = {class_name}().render(symbol)
    assert artifact.backend == {backend!r}
    assert artifact.media_type == {media_type!r}
    assert isinstance(artifact.data, {data_type})
""".lstrip()
