"""Preserve invalidated local README bundles as immutable superseded evidence."""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from readme_agent.evidence.file_inventory import filesystem_path
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    sha256_file,
    verify_sha256sums,
    win_long_path,
    write_redacted_json,
)
from readme_agent.gitsafety.clone import force_rmtree
from readme_agent.supervisor.local_poc_review_cache_preservation import (
    PACKET_CACHE_DIRECTORY,
    preserve_bounded_review_cache,
)

_EVIDENCE_DIRECTORIES = ("facts", "assessment", "planning", "candidate", "review", "receipts")
_DOWNSTREAM_DIRECTORIES = ("assessment", "planning", "candidate", "review")
_DOWNSTREAM_RECEIPT_STAGES = frozenset(
    {
        "README_ASSESSED",
        "PLAN_READY",
        "CANDIDATE_GENERATED",
        "DETERMINISTIC_VALIDATION_FAILED",
        "DETERMINISTIC_VALIDATED",
        "AGENT_REVIEWING",
        "AGENT_REVIEW_REJECTED",
        "REPAIRING",
        "AGENT_APPROVED",
        "NO_OP_PROVEN",
        "HUMAN_REVIEW_READY",
        "HUMAN_ACCEPTED",
        "PR_ELIGIBLE",
        "PR_PROOF_COMPLETE",
    }
)
_DIRECTORY_HASH_LENGTH = 16
_PACKET_CACHE_ARCHIVE = "bounded-packet-cache.zip"
_RECOVERABLE_PREPROMOTION_MUTATIONS = frozenset({"assurance/section_authoring/document.json"})


def _write_deterministic_packet_cache_archive(source: Path, destination: Path) -> None:
    """Compact hash-named packet receipts without lengthening Windows paths."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source_path in sorted(path for path in source.rglob("*") if path.is_file()):
            relative = source_path.relative_to(source).as_posix()
            entry = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, source_path.read_bytes(), compresslevel=9)


def _long_path(path: Path) -> str | Path:
    """`path`, prefixed for Win32 MAX_PATH safety when running on Windows.

    A superseded-evidence destination is `<bundle>/superseded/<16-hex>/...` --
    always longer than its `source` sibling, which lacks that extra path
    segment -- nested under whatever the bundle's own already-long
    `<repo>/<40-char revision>/` path is, so it is the side that crosses 260
    characters. `shutil.copytree`/`shutil.rmtree` open every entry through the
    raw Win32 API and have no long-path handling of their own, unlike
    `os.replace` elsewhere in this codebase (see `evidence/writer.py::
    win_long_path`, which this reuses).

    Only ever applied to a destination, never a source: `_copy_evidence_directory`'s
    `ignore` callback below compares `Path(current) == source` against the
    unprefixed `source` it closed over, so prefixing `source` for `copytree`
    would silently break that comparison on every call.
    """

    return win_long_path(path) if os.name == "nt" else path


def _copy_evidence_directory(source: Path, destination: Path, *, name: str) -> None:
    """Resume one evidence copy while compacting the long packet-cache subtree."""

    if name != "review":
        shutil.copytree(source, _long_path(destination), dirs_exist_ok=True)
        return

    packet_cache = source / PACKET_CACHE_DIRECTORY

    def ignore(current: str, names: list[str]) -> set[str]:
        return (
            {PACKET_CACHE_DIRECTORY}
            if Path(current) == source and PACKET_CACHE_DIRECTORY in names
            else set()
        )

    shutil.copytree(source, _long_path(destination), dirs_exist_ok=True, ignore=ignore)
    if not packet_cache.is_dir():
        return
    _write_deterministic_packet_cache_archive(
        packet_cache,
        destination / _PACKET_CACHE_ARCHIVE,
    )
    partial_cache_copy = destination / PACKET_CACHE_DIRECTORY
    if partial_cache_copy.is_dir():
        shutil.rmtree(_long_path(partial_cache_copy))


def has_active_downstream_artifacts(bundle_dir: Path, manifest: dict) -> bool:
    """Return whether a fact-boundary bundle still exposes later-stage evidence."""

    if any((bundle_dir / name).is_dir() for name in _DOWNSTREAM_DIRECTORIES):
        return True
    receipts_dir = bundle_dir / "receipts"
    if receipts_dir.is_dir() and any(
        (receipts_dir / f"{stage}.json").is_file() for stage in _DOWNSTREAM_RECEIPT_STAGES
    ):
        return True
    stage_receipts = manifest.get("stage_receipts")
    return isinstance(stage_receipts, dict) and any(
        stage in _DOWNSTREAM_RECEIPT_STAGES for stage in stage_receipts
    )


def preserve_superseded_candidate(
    bundle_dir: Path,
    prior_manifest: dict,
    *,
    reason: str,
) -> str | None:
    """Snapshot one displaced candidate and its evidence without inventing acceptance."""

    candidate_path = bundle_dir / "candidate" / "README.md"
    if not candidate_path.is_file():
        return None
    candidate_hash = sha256_file(candidate_path)[0]
    destination = bundle_dir / "superseded" / candidate_hash[:_DIRECTORY_HASH_LENGTH]
    preserved_candidate = destination / "candidate" / "README.md"
    if preserved_candidate.is_file() and (destination / "superseded.json").is_file():
        if sha256_file(preserved_candidate)[0] != candidate_hash:
            raise RuntimeError(f"superseded candidate hash collision in {destination}")
        record_path = destination / "superseded.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("candidate_hash") != candidate_hash:
            raise RuntimeError(f"superseded candidate identity collision in {destination}")
        return candidate_hash

    if preserved_candidate.is_file() and sha256_file(preserved_candidate)[0] != candidate_hash:
        raise RuntimeError(f"superseded candidate hash collision in {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    for name in _EVIDENCE_DIRECTORIES:
        source = bundle_dir / name
        if source.is_dir():
            _copy_evidence_directory(source, destination / name, name=name)
    for name in ("manifest.json", "sha256sums.txt"):
        source = bundle_dir / name
        if source.is_file():
            shutil.copy2(source, destination / name)
    manifest_candidate_hash = prior_manifest.get("candidate_hash")
    write_redacted_json(
        destination / "superseded.json",
        {
            "schema_version": 1,
            "candidate_hash": candidate_hash,
            "source_revision": prior_manifest.get("source_revision"),
            "prior_lifecycle_status": prior_manifest.get("lifecycle_status"),
            "prior_manifest_candidate_hash": manifest_candidate_hash,
            "candidate_binding": (
                "manifest_bound"
                if manifest_candidate_hash == candidate_hash
                else "retained_artifact_without_current_manifest_binding"
            ),
            "packet_cache_archive": (
                f"review/{_PACKET_CACHE_ARCHIVE}"
                if (destination / "review" / _PACKET_CACHE_ARCHIVE).is_file()
                else None
            ),
            "reason": reason,
        },
    )
    refresh_sha256sums(destination)
    return candidate_hash


def _load_checksum_inventory(bundle_dir: Path) -> dict[str, str] | None:
    inventory_path = bundle_dir / "sha256sums.txt"
    if not inventory_path.is_file():
        return None
    try:
        inventory: dict[str, str] = {}
        for line in inventory_path.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", maxsplit=1)
            relative_path = Path(relative)
            if (
                len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or not relative
                or relative in inventory
                or relative_path.is_absolute()
                or ".." in relative_path.parts
                or relative_path.as_posix() != relative
            ):
                return None
            inventory[relative] = digest
        return inventory
    except (OSError, UnicodeError, ValueError):
        return None


def _files_outside_interrupted_destination(
    bundle_dir: Path,
    destination: Path,
) -> dict[str, Path]:
    """Enumerate the sealed tree without descending into one known partial copy."""

    physical_root = filesystem_path(bundle_dir)
    excluded = destination.relative_to(bundle_dir)
    files: dict[str, Path] = {}

    def raise_walk_error(error: OSError) -> None:
        raise error

    for current_root, directories, filenames in os.walk(
        physical_root,
        topdown=True,
        onerror=raise_walk_error,
    ):
        current = Path(current_root)
        current_relative = current.relative_to(physical_root)
        directories.sort()
        if current_relative == excluded.parent and excluded.name in directories:
            directories.remove(excluded.name)
        for filename in sorted(filenames):
            physical = current / filename
            if not stat.S_ISREG(physical.stat().st_mode):
                raise OSError(f"unsupported non-regular evidence artifact: {physical}")
            relative = physical.relative_to(physical_root).as_posix()
            # The canonical evidence inventory omits checksum inventories at
            # every nesting depth, not only the bundle root.
            if physical.name != "sha256sums.txt":
                files[relative] = physical
    return files


def recover_interrupted_candidate_supersession(bundle_dir: Path) -> bool:
    """Finish one narrowly recognized candidate supersession, otherwise fail closed."""

    try:
        manifest_path = bundle_dir / "manifest.json"
        candidate_path = bundle_dir / "candidate" / "README.md"
        if not manifest_path.is_file() or not candidate_path.is_file():
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False
        candidate_hash = sha256_file(candidate_path)[0]
        if manifest.get("candidate_hash") != candidate_hash:
            return False

        destination = bundle_dir / "superseded" / candidate_hash[:_DIRECTORY_HASH_LENGTH]
        if not destination.is_dir():
            return False
        preserved_candidate = destination / "candidate" / "README.md"
        if preserved_candidate.is_file() and sha256_file(preserved_candidate)[0] != candidate_hash:
            return False

        inventory = _load_checksum_inventory(bundle_dir)
        if inventory is None:
            return False
        destination_prefix = destination.relative_to(bundle_dir).as_posix() + "/"
        if any(relative.startswith(destination_prefix) for relative in inventory):
            return False

        actual = _files_outside_interrupted_destination(bundle_dir, destination)
        if set(actual) != set(inventory):
            return False
        mismatches = {
            relative
            for relative, digest in inventory.items()
            if sha256_file(actual[relative])[0] != digest
        }
        if not mismatches <= _RECOVERABLE_PREPROMOTION_MUTATIONS:
            return False

        record_path = destination / "superseded.json"
        if record_path.is_file() and not verify_sha256sums(destination):
            return False
        preserve_superseded_candidate(
            bundle_dir,
            manifest,
            reason="resume interrupted candidate supersession",
        )
        refresh_sha256sums(bundle_dir)
        return verify_sha256sums(bundle_dir)
    except (OSError, UnicodeError, ValueError, RuntimeError, json.JSONDecodeError):
        return False


def archive_and_prune_downstream_artifacts(
    bundle_dir: Path,
    prior_manifest: dict,
    *,
    reason: str,
) -> dict:
    """Archive a physical candidate, then remove artifacts invalid below product truth."""

    preserve_superseded_candidate(bundle_dir, prior_manifest, reason=reason)
    with preserve_bounded_review_cache(bundle_dir):
        for name in _DOWNSTREAM_DIRECTORIES:
            path = bundle_dir / name
            if path.is_dir():
                # `review/bounded-packet-cache` was very likely just read in
                # full twice in a row -- once by `preserve_superseded_candidate`
                # above (zip-archiving it), once by `preserve_bounded_review_cache`'s
                # own entry snapshot just above this loop -- a back-to-back
                # read pattern SCL-010 (gitsafety/clone.py) already found
                # reproducibly triggers a transient Windows `WinError 145`
                # ("directory not empty") on an otherwise-already-cleared
                # child, from an AV/indexer handle invisible to directory
                # enumeration. Plain `shutil.rmtree` has no recovery for that;
                # reuse the same proven sweep-and-retry remedy rather than a
                # second copy of it.
                force_rmtree(path)

    receipts_dir = bundle_dir / "receipts"
    if receipts_dir.is_dir():
        for stage in _DOWNSTREAM_RECEIPT_STAGES:
            (receipts_dir / f"{stage}.json").unlink(missing_ok=True)
        if not any(receipts_dir.iterdir()):
            receipts_dir.rmdir()

    retained = dict(prior_manifest)
    stage_receipts = retained.get("stage_receipts")
    if isinstance(stage_receipts, dict):
        retained_receipts = {
            stage: receipt
            for stage, receipt in stage_receipts.items()
            if stage not in _DOWNSTREAM_RECEIPT_STAGES
        }
        if retained_receipts:
            retained["stage_receipts"] = retained_receipts
        else:
            retained.pop("stage_receipts", None)
            retained.pop("acceptance_authority", None)
    return retained


def superseded_candidate_hashes(bundle_dir: Path) -> list[str]:
    """Return the deterministic set of preserved candidate identities."""

    root = bundle_dir / "superseded"
    if not root.is_dir():
        return []
    hashes: list[str] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        record_path = path / "superseded.json"
        if not record_path.is_file():
            raise RuntimeError(f"superseded candidate record is missing in {path}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        candidate_hash = record.get("candidate_hash")
        if not isinstance(candidate_hash, str) or len(candidate_hash) != 64:
            raise RuntimeError(f"superseded candidate identity is invalid in {path}")
        hashes.append(candidate_hash)
    return sorted(hashes)
