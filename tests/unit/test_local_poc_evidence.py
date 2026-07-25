"""Revision-addressed snapshot evidence for the canonical local POC."""

from pathlib import Path

from readme_agent import paths
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1
from readme_agent.supervisor.local_poc_evidence import (
    mark_local_poc_profiled,
    write_local_poc_snapshot,
)


def _snapshot(tmp_path: Path, *, readme: bool = True) -> RepositorySnapshotV1:
    if readme:
        (tmp_path / "README.md").write_text("# Product\n", encoding="utf-8")
    return RepositorySnapshotV1(
        org_repo="acme/product",
        source_revision="a" * 40,
        snapshot_root=str(tmp_path),
        readme_path="README.md" if readme else None,
        readme_sha256="b" * 64 if readme else None,
        inventory_sha256="c" * 64,
        captured_at="2026-07-25T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/product.git", git_tree_sha256="c" * 64
        ),
    )


def test_snapshot_bundle_is_revision_addressed_idempotent_and_checksum_complete(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)

    bundle = write_local_poc_snapshot(snapshot)
    second = write_local_poc_snapshot(snapshot)

    assert bundle == second
    assert (bundle / "source" / "README.md").read_text(encoding="utf-8") == "# Product\n"
    assert (bundle / "source" / "revision.json").is_file()
    assert (bundle / "manifest.json").is_file()
    assert (bundle / "sha256sums.txt").is_file()
    assert '"complete": false' in (bundle / "manifest.json").read_text(encoding="utf-8")


def test_missing_readme_is_explicit_evidence_not_a_fake_empty_readme(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")

    bundle = write_local_poc_snapshot(_snapshot(tmp_path, readme=False))

    assert (bundle / "source" / "readme-absence.json").is_file()
    assert not (bundle / "source" / "README.md").exists()


def test_profile_boundary_updates_manifest_without_claiming_completion(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    snapshot = _snapshot(tmp_path)
    bundle = write_local_poc_snapshot(snapshot)

    mark_local_poc_profiled(snapshot, bundle)

    manifest = (bundle / "manifest.json").read_text(encoding="utf-8")
    assert '"lifecycle_status": "PROFILED"' in manifest
    assert '"complete": false' in manifest
    assert '"SNAPSHOTTED"' in manifest
    assert '"PROFILED"' in manifest
