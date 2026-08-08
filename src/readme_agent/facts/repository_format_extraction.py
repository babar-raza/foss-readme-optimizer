"""Extract directional format evidence from the immutable repository snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.aspose_org_format_contract import AsposeOrgFormatEvidenceV1
from readme_agent.facts.python_family_format_functionality import (
    corroborate_python_family_format_directions,
)

_PLATFORM_ALIASES = {".net": "net", "dotnet": "net", "nodejs": "typescript", "ts": "typescript"}


class RepositoryFormatExtractionV1(BaseModel):
    """Repository-owned format directions with no sibling-system dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["available", "unavailable"]
    formats: list[AsposeOrgFormatEvidenceV1] = Field(default_factory=list)
    detail: str


def extract_repository_format_directions(
    repository_root: Path,
    *,
    platform: str,
    family: str,
    source_revision: str,
) -> RepositoryFormatExtractionV1:
    """Return only directions corroborated by current-revision repository code and tests."""

    normalized_platform = _PLATFORM_ALIASES.get(platform.casefold(), platform.casefold())
    formats: list[AsposeOrgFormatEvidenceV1] = []
    if normalized_platform == "python":
        formats = corroborate_python_family_format_directions(
            repository_root,
            family=family,
            source_revision=source_revision,
            formats=[],
        )
    functional = [
        item
        for item in formats
        if item.functional is True and item.direction in {"import", "export", "both"}
    ]
    if not functional:
        return RepositoryFormatExtractionV1(
            status="unavailable",
            detail=(
                "no registered current-revision repository format corroborator produced "
                "functional directions"
            ),
        )
    return RepositoryFormatExtractionV1(
        status="available",
        formats=functional,
        detail=f"accepted {len(functional)} repository-native format records",
    )


__all__ = ["RepositoryFormatExtractionV1", "extract_repository_format_directions"]
