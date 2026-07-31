"""Resolve repository-relative license links from accepted license evidence."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote

from readme_agent.facts.schema_v2 import FactRecordV2


def repository_license_path(fact: FactRecordV2) -> str:
    """Return a safe repository-relative license path, or the conventional fallback."""

    prefix = "repository://"
    location = str(fact.source.location or "").strip().replace("\\", "/")
    candidate = location[len(prefix) :] if location.startswith(prefix) else ""
    path = PurePosixPath(candidate)
    if (
        not candidate
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(character in candidate for character in (":", "#", "?", "<", ">", "|"))
        or any(ord(character) < 32 for character in candidate)
    ):
        return "LICENSE"
    return quote(path.as_posix(), safe="/._-~")
