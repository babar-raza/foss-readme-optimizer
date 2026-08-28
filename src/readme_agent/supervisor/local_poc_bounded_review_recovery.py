"""Recover validated bounded-review cache writes interrupted before bundle resealing."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from readme_agent.evidence.file_inventory import enumerate_files
from readme_agent.evidence.writer import refresh_sha256sums, sha256_file, verify_sha256sums
from readme_agent.specialists.bounded_review_cache import BoundedReviewPacketCacheV1

_CACHE_PATH = re.compile(r"^review/bounded-packet-cache/([0-9a-f]{64})\.json$")


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


def recover_interrupted_bounded_review_cache_write(
    bundle_dir: Path,
    *,
    org_repo: str,
    source_revision: str,
) -> bool:
    """Reseal only valid content-addressed review cache entries added after inventory.

    The existing inventory must remain exact for every artifact it already covers. Every extra
    artifact must be one structurally valid packet-cache receipt whose filename, repository, and
    immutable source revision match its typed content. Recovery preserves provider work without
    promoting a review verdict or accepting any candidate content.
    """

    expected = _inventory_entries(bundle_dir)
    if expected is None:
        return False
    try:
        actual = {
            relative.as_posix(): physical
            for relative, physical in enumerate_files(bundle_dir)
            if physical.name != "sha256sums.txt"
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
            path = actual[relative]
            if match is None or path.is_symlink():
                return False
            cached = BoundedReviewPacketCacheV1.model_validate_json(
                path.read_text(encoding="utf-8")
            )
            if (
                cached.cache_key != match.group(1)
                or cached.org_repo != org_repo
                or cached.source_revision != source_revision
            ):
                return False
    except (OSError, UnicodeError, ValidationError, ValueError):
        return False

    refresh_sha256sums(bundle_dir)
    return verify_sha256sums(bundle_dir)


__all__ = ["recover_interrupted_bounded_review_cache_write"]
