"""Seal immutable snapshot evidence and maintain local-POC manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from readme_agent import env, paths
from readme_agent.errors import RepositorySnapshotError
from readme_agent.evidence.redaction import redact
from readme_agent.evidence.writer import (
    refresh_sha256sums,
    verify_sha256sums,
    write_redacted_json,
    write_redacted_text,
)
from readme_agent.llm import prompt_registry
from readme_agent.llm.bundle_accounting import local_bundle_llm_accounting_fields
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.assurance import ContentAssuranceV1


def load_existing_local_poc_manifest(bundle_dir: Path, source_revision: str) -> dict:
    """Load the manifest only when it belongs to the requested revision."""

    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return {}
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("source_revision") != source_revision:
        return {}
    return loaded


def write_local_poc_manifest(
    bundle_dir: Path,
    manifest: dict,
    *,
    content_assurance: ContentAssuranceV1 | None = None,
    include_runtime_accounting: bool = True,
) -> None:
    """Write one bundle manifest with cumulative, fail-closed LLM accounting."""

    path = bundle_dir / "manifest.json"
    prior: dict = {}
    if path.is_file():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            prior = loaded
    accounting = (
        local_bundle_llm_accounting_fields(bundle_dir, prior) if include_runtime_accounting else {}
    )
    write_redacted_json(
        path,
        {
            **manifest,
            "content_assurance": (
                content_assurance
                or manifest.get("content_assurance")
                or prior.get("content_assurance")
                or "repository_verified"
            ),
            "prompt_registry_content_hash": prompt_registry.content_hash(),
            "prompt_hashes_by_id": prompt_registry.prompt_hashes(),
            "prompt_dependency_hashes": prompt_registry.dependency_hashes(),
            **accounting,
        },
    )


def _fail(message: str) -> RepositorySnapshotError:
    return RepositorySnapshotError(f"sealed local-POC snapshot evidence is invalid: {message}")


def _load_json_object(path: Path, label: str) -> dict:
    if not path.is_file():
        raise _fail(f"missing {label}: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise _fail(f"malformed {label}: {path}") from exc
    if not isinstance(loaded, dict):
        raise _fail(f"{label} must be a JSON object: {path}")
    return loaded


def _stable_snapshot_identity(snapshot: RepositorySnapshotV1) -> dict:
    identity = snapshot.model_dump(mode="json")
    # These describe this particular local capture, not the immutable Git object.
    identity.pop("captured_at")
    identity.pop("snapshot_root")
    return identity


def _profile_identity(snapshot: RepositorySnapshotV1) -> dict:
    return {
        "org_repo": snapshot.org_repo,
        "inventory_sha256": snapshot.inventory_sha256,
        "package_roots": [root.model_dump(mode="json") for root in snapshot.package_roots],
    }


def _read_current_readme(snapshot: RepositorySnapshotV1) -> str | None:
    if snapshot.readme_path is None:
        return None
    readme = snapshot.root_path / snapshot.readme_path
    if not readme.is_file():
        raise _fail(f"current snapshot README is missing: {snapshot.readme_path}")
    try:
        raw = readme.read_bytes()
        text = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise _fail(f"current snapshot README cannot be read: {snapshot.readme_path}") from exc
    if hashlib.sha256(raw).hexdigest() != snapshot.readme_sha256:
        raise _fail("current snapshot README does not match its declared checksum")
    return redact(text, env.secret_values())


def _is_checksum_valid_intake_only_bundle(bundle_dir: Path) -> bool:
    """Allow snapshot sealing after durable intake created the revision directory first."""

    files = [path for path in bundle_dir.rglob("*") if path.is_file()]
    if not files or not verify_sha256sums(bundle_dir):
        return False
    relative_paths = {path.relative_to(bundle_dir).as_posix() for path in files}
    return "sha256sums.txt" in relative_paths and all(
        path == "sha256sums.txt" or path.startswith("intake/") for path in relative_paths
    )


def _validate_sealed_snapshot(
    bundle_dir: Path,
    snapshot: RepositorySnapshotV1,
    expected_readme: str | None,
) -> None:
    if not verify_sha256sums(bundle_dir):
        raise _fail(f"checksum inventory is missing, incomplete, or corrupt: {bundle_dir}")

    source_dir = bundle_dir / "source"
    revision_path = source_dir / "revision.json"
    try:
        persisted = RepositorySnapshotV1.model_validate_json(
            revision_path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValidationError) as exc:
        raise _fail(f"missing or malformed RepositorySnapshotV1: {revision_path}") from exc
    if _stable_snapshot_identity(persisted) != _stable_snapshot_identity(snapshot):
        raise _fail("repository, revision, README, inventory, package roots, or provenance changed")

    manifest = _load_json_object(bundle_dir / "manifest.json", "bundle manifest")
    if (
        manifest.get("org_repo") != snapshot.org_repo
        or manifest.get("source_revision") != snapshot.source_revision
    ):
        raise _fail("bundle manifest does not identify the sealed repository revision")
    if _load_json_object(source_dir / "repository-profile.json", "repository profile") != (
        _profile_identity(snapshot)
    ):
        raise _fail("repository profile differs from the sealed snapshot")

    expected_names = {"revision.json", "repository-profile.json"}
    if snapshot.readme_path is None:
        expected_names.add("readme-absence.json")
        absence = _load_json_object(source_dir / "readme-absence.json", "README absence")
        if absence != {"reason": "README absent at immutable source revision"}:
            raise _fail("README absence evidence differs from the sealed snapshot")
    else:
        expected_names.add("README.md")
        readme_path = source_dir / "README.md"
        try:
            persisted_readme = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise _fail(f"sealed README is missing or unreadable: {readme_path}") from exc
        if persisted_readme != expected_readme:
            raise _fail("sealed README differs from the current immutable source")

    actual_names = {path.name for path in source_dir.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise _fail("source evidence contains missing, stale, or unexpected artifacts")


def write_local_poc_snapshot(snapshot: RepositorySnapshotV1) -> Path:
    """Seal the source boundary once and reuse it only for the same immutable source."""

    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    expected_readme = _read_current_readme(snapshot)
    if bundle_dir.exists():
        revision_path = bundle_dir / "source" / "revision.json"
        if (
            revision_path.is_file()
            or (bundle_dir / "source").exists()
            or (bundle_dir / "manifest.json").exists()
        ):
            _validate_sealed_snapshot(bundle_dir, snapshot, expected_readme)
            return bundle_dir
        if not _is_checksum_valid_intake_only_bundle(bundle_dir):
            raise _fail(
                "existing revision directory is neither a sealed snapshot nor a "
                "checksum-valid intake-only bundle"
            )

    source_dir = bundle_dir / "source"
    write_redacted_json(source_dir / "revision.json", snapshot)
    write_redacted_json(source_dir / "repository-profile.json", _profile_identity(snapshot))
    if snapshot.readme_path is None:
        write_redacted_json(
            source_dir / "readme-absence.json",
            {"reason": "README absent at immutable source revision"},
        )
    else:
        write_redacted_text(source_dir / "README.md", expected_readme or "")
    write_local_poc_manifest(
        bundle_dir,
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": "SNAPSHOTTED",
            "complete": False,
            "completed_stages": ["SNAPSHOTTED"],
        },
    )
    refresh_sha256sums(bundle_dir)
    return bundle_dir


def mark_local_poc_profiled(snapshot: RepositorySnapshotV1, bundle_dir: Path) -> None:
    """Advance the bundle manifest after the durable profile transition."""

    existing = load_existing_local_poc_manifest(bundle_dir, snapshot.source_revision)
    if "PROFILED" in existing.get("completed_stages", []):
        return
    write_local_poc_manifest(
        bundle_dir,
        {
            "schema_version": 1,
            "org_repo": snapshot.org_repo,
            "source_revision": snapshot.source_revision,
            "lifecycle_status": "PROFILED",
            "complete": False,
            "completed_stages": ["SNAPSHOTTED", "PROFILED"],
        },
    )
    refresh_sha256sums(bundle_dir)
