"""Define the repository-name contract for execution-registry eligibility."""

from __future__ import annotations

import re

_MANAGED_REPOSITORY_PATTERN = re.compile(
    r"^Aspose[.-]([A-Za-z0-9]+)-FOSS-for-([A-Za-z0-9.]+)$",
    flags=re.IGNORECASE,
)

_PLATFORM_ALIASES = {
    ".net": "net",
    "net": "net",
    "cpp": "cpp",
    "go": "go",
    "java": "java",
    "javascript": "javascript",
    "nodejs": "nodejs",
    "python": "python",
    "rust": "rust",
    "typescript": "typescript",
}


def classify_managed_repository_name(repo_name: str) -> tuple[str, str] | None:
    """Return normalized coordinates only for the governed Aspose FOSS name shape."""

    match = _MANAGED_REPOSITORY_PATTERN.fullmatch(repo_name)
    if match is None:
        return None
    family = match.group(1).casefold()
    platform = match.group(2).casefold()
    return family, _PLATFORM_ALIASES.get(platform, platform)


def required_repository_name_syntax() -> str:
    """Return the human-readable execution eligibility contract."""

    return "Aspose.{Family}-FOSS-for-{Platform} or Aspose-{Family}-FOSS-for-{Platform}"


def validate_managed_repository_coordinates(
    repo_name: str,
    family: str,
    platform: str,
) -> None:
    """Reject names or coordinates that cannot enter the execution registry."""

    coordinates = classify_managed_repository_name(repo_name)
    if coordinates is None:
        raise ValueError(f"repo_name must match {required_repository_name_syntax()}")
    expected = (family.casefold(), platform.casefold())
    if coordinates != expected:
        raise ValueError(
            "repo_name family/platform coordinates do not match the registry entry: "
            f"{coordinates!r} != {expected!r}"
        )
