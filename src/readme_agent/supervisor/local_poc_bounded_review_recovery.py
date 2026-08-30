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


def recover_migrated_bounded_review_cache_entries(
    bundle_dir: Path,
    *,
    org_repo: str,
    source_revision: str,
) -> bool:
    """Reseal bounded-review cache entries whose content legitimately changed post-seal.

    Filenames under `review/bounded-packet-cache/` are *identity keys* (dominated by
    `packet.packet_sha256`, see `bounded_review_cache.py::packet_cache_key()`), never a hash of the
    file's own bytes. `sha256sums.txt`, sealed once at snapshot time, therefore can't tell a
    legitimate later rewrite at that same identity-keyed path from real corruption. This is exactly
    why `recover_interrupted_bounded_review_cache_write()` above can't repair it -- that function
    only tolerates *added* files and bails at its very first check the moment any *already-
    inventoried* file's digest disagrees. Found live: a sealed `aspose-font-foss` snapshot had 41
    bounded-review-cache files with mismatched digests, all already inventoried, zero added -- the
    "no extras" bail-out fired immediately and the snapshot was discarded as corrupt across multiple
    retries instead of resealed.

    The *exact* trigger for the content change is not confirmed (a later re-read of
    `BoundedReviewPacketCache.load()`'s legacy-cache-key migration path found it always writes to a
    *new* filename derived from the *current* cache key, never the file it read from -- so it cannot
    itself explain a same-filename rewrite, contrary to this function's first write-up). The current
    best-supported theory: two runs racing a cache miss for the same packet identity both compute a
    fresh, independently non-deterministic result (`write_bounded_review_packet_cache()` always
    writes to `{cache_key}.json`; two calls with identical identity naturally collide on that path)
    and both persist, the second silently overwriting the first. This function does not depend on
    which explanation is correct.

    It recovers that specific, narrower case: it never tolerates an added or removed path (unlike
    the function above); every *disagreeing* file must already be inventoried, must live under
    `review/bounded-packet-cache/`, and must parse as a structurally valid packet-cache receipt
    whose filename, org_repo, and source_revision all agree with its own typed content -- the same
    identity check the function above already trusts for *added* files, applied here to *changed*
    ones instead. Every other inventoried file must still match its recorded digest exactly; this
    recovers nothing outside the one path a legitimate rewrite can touch.
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
        if set(expected) != set(actual):
            return False
        disagreements = [
            relative
            for relative, digest in expected.items()
            if sha256_file(actual[relative])[0] != digest
        ]
        if not disagreements:
            return False
        for relative in disagreements:
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


__all__ = [
    "recover_interrupted_bounded_review_cache_write",
    "recover_migrated_bounded_review_cache_entries",
]
