"""Recover a validated section-authoring cache write interrupted before bundle resealing."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from readme_agent.evidence.file_inventory import enumerate_files
from readme_agent.evidence.writer import refresh_sha256sums, sha256_file, verify_sha256sums
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.specialists.section_authoring_cache import SectionAuthoringCacheV1

_CACHE_PATH = re.compile(r"^assurance/section_authoring/cache/([0-9a-f]{12})\.json$")


def _inventory_entries(bundle_dir: Path) -> dict[str, str] | None:
    inventory = bundle_dir / "sha256sums.txt"
    if not inventory.is_file():
        return None
    try:
        entries: dict[str, str] = {}
        for line in inventory.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", maxsplit=1)
            if (
                len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or not relative
                or relative in entries
            ):
                return None
            entries[relative] = digest
        return entries
    except (OSError, UnicodeError, ValueError):
        return None


def recover_interrupted_section_authoring_cache_write(
    bundle_dir: Path,
    snapshot: RepositorySnapshotV1,
) -> bool:
    """Reseal only valid cache files added after an otherwise exact checksum inventory.

    Cache entries are content-addressed and the normal loader will reuse one only when the
    freshly recomputed key matches. Recovery therefore preserves a valid provider result without
    promoting it, changing lifecycle state, or trusting it as current candidate content.
    """

    expected = _inventory_entries(bundle_dir)
    if expected is None:
        return False
    try:
        actual = {
            relative.as_posix(): physical
            for relative, physical in enumerate_files(bundle_dir)
            if relative.as_posix() != "sha256sums.txt"
        }
        if not set(expected).issubset(actual) or any(
            sha256_file(actual[relative])[0] != digest for relative, digest in expected.items()
        ):
            return False
        extras = sorted(set(actual) - set(expected))
        if not extras:
            return False
        for relative in extras:
            match = _CACHE_PATH.fullmatch(relative)
            path = bundle_dir / Path(relative)
            if match is None or path.is_symlink():
                return False
            cached = SectionAuthoringCacheV1.model_validate_json(path.read_text(encoding="utf-8"))
            if (
                cached.org_repo != snapshot.org_repo
                or cached.source_revision != snapshot.source_revision
                or cached.cache_key[:12] != match.group(1)
            ):
                return False
    except (OSError, UnicodeError, ValidationError, ValueError):
        return False

    refresh_sha256sums(bundle_dir)
    return verify_sha256sums(bundle_dir)


__all__ = ["recover_interrupted_section_authoring_cache_write"]
