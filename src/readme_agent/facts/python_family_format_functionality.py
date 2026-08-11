"""Dispatch repository-bound Python format corroborators by product family."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_3d_format_functionality import (
    corroborate_python_3d_format_directions,
)
from readme_agent.facts.python_barcode_format_functionality import (
    corroborate_python_barcode_format_directions,
)
from readme_agent.facts.python_cells_format_functionality import (
    corroborate_python_cells_format_directions,
)
from readme_agent.facts.python_email_format_functionality import (
    corroborate_python_email_format_directions,
)
from readme_agent.facts.python_font_format_functionality import (
    corroborate_python_font_format_directions,
)
from readme_agent.facts.python_html_format_functionality import (
    corroborate_python_html_format_directions,
)
from readme_agent.facts.python_slides_format_functionality import (
    corroborate_python_slides_format_directions,
)
from readme_agent.facts.python_tex_format_functionality import (
    corroborate_python_tex_format_directions,
)
from readme_agent.facts.python_words_format_functionality import (
    corroborate_python_words_format_directions,
)

_Corroborator = Callable[
    [Path, str, list[AsposeOrgFormatEvidenceV1]],
    list[AsposeOrgFormatEvidenceV1],
]


def _corroborate_3d(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_3d_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_barcode(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_barcode_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_email(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_email_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_html(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_html_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_cells(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_cells_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_font(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_font_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_slides(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_slides_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_tex(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_tex_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


def _corroborate_words(
    root: Path,
    revision: str,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    return corroborate_python_words_format_directions(
        root,
        source_revision=revision,
        formats=formats,
    )


_CORROBORATORS: dict[str, _Corroborator] = {
    "3d": _corroborate_3d,
    "barcode": _corroborate_barcode,
    "cells": _corroborate_cells,
    "email": _corroborate_email,
    "font": _corroborate_font,
    "html": _corroborate_html,
    "slides": _corroborate_slides,
    "tex": _corroborate_tex,
    "words": _corroborate_words,
}


def corroborate_python_family_format_directions(
    repository_root: Path,
    *,
    family: str,
    source_revision: str | None,
    formats: list[AsposeOrgFormatEvidenceV1],
) -> list[AsposeOrgFormatEvidenceV1]:
    """Apply one registered family corroborator when immutable identity is available."""

    if source_revision is None:
        return formats
    corroborator = _CORROBORATORS.get(family.casefold())
    if corroborator is None:
        return formats
    return corroborator(repository_root, source_revision, formats)
