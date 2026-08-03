"""Primary Python format evidence is upgraded only after direct source corroboration."""

from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_format_functionality import (
    corroborate_python_primary_format_directions,
)


def _entry(
    *,
    format: str,
    direction: str,
    file: str,
    line: int,
    functional: bool | None,
) -> AsposeOrgFormatEvidenceV1:
    return AsposeOrgFormatEvidenceV1.model_validate(locals())


def _repository(tmp_path: Path, *, include_load: bool = True, include_write: bool = True) -> Path:
    package = tmp_path / "src" / "aspose_pdf"
    package.mkdir(parents=True)
    load = "self.load_from(source)" if include_load else "self.source = source"
    write = "destination.write(self._data)" if include_write else "return self"
    (package / "document.py").write_text(
        f"""from aspose_pdf._compat_surface import (
    require_pdf_save_format as _require_pdf_save_format,
)

class Document:
    def __init__(self, source=None):
        {load}

    def save(self, destination, save_format=None):
        _require_pdf_save_format(save_format)
        {write}
""",
        encoding="utf-8",
    )
    (package / "_compat_surface.py").write_text(
        """_PDF_MEMBERS = frozenset({("SaveFormat", "PDF")})

def require_pdf_save_format(value):
    if value is None:
        return
""",
        encoding="utf-8",
    )
    return tmp_path


def _formats() -> list[AsposeOrgFormatEvidenceV1]:
    return [
        _entry(
            format="PDF",
            direction="enum_only",
            file="src/aspose_pdf/save_format.py",
            line=10,
            functional=False,
        ),
        _entry(
            format="PPTX",
            direction="enum_only",
            file="src/aspose_pdf/save_format.py",
            line=10,
            functional=False,
        ),
        _entry(
            format="Pdf",
            direction="import",
            file="src/aspose_pdf/document.py",
            line=3,
            functional=None,
        ),
        _entry(
            format="Svg",
            direction="import",
            file="src/aspose_pdf/svg.py",
            line=20,
            functional=None,
        ),
    ]


def test_pdf_constructor_and_concrete_save_upgrade_only_pdf(tmp_path: Path) -> None:
    result = corroborate_python_primary_format_directions(
        _repository(tmp_path),
        family="pdf",
        formats=_formats(),
    )

    functional = {(item.format.casefold(), item.direction) for item in result if item.functional}
    assert functional == {("pdf", "import"), ("pdf", "export")}
    assert not any(item.format == "PPTX" and item.functional for item in result)
    assert not any(item.format == "Svg" and item.functional for item in result)


def test_signature_without_load_delegation_does_not_prove_import(tmp_path: Path) -> None:
    result = corroborate_python_primary_format_directions(
        _repository(tmp_path, include_load=False),
        family="pdf",
        formats=_formats(),
    )

    assert not any(item.direction == "import" and item.functional for item in result)


def test_helper_token_without_concrete_write_does_not_prove_export(tmp_path: Path) -> None:
    result = corroborate_python_primary_format_directions(
        _repository(tmp_path, include_write=False),
        family="pdf",
        formats=_formats(),
    )

    assert not any(item.direction == "export" and item.functional for item in result)
