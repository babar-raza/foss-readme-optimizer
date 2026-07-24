"""RepositorySnapshotV1 capture, binding, and drift controls."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.errors import RepositorySnapshotError
from readme_agent.gitsafety import clone as clone_module
from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.clone import clone_baseline
from readme_agent.profile import cached
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import (
    capture_repository_snapshot,
    current_repository_snapshot,
    repository_snapshot_scope,
    verify_repository_snapshot,
)

ORG_REPO = "example-org/Example"


def _git(repo: Path, *args: str) -> None:
    result = run_git(list(args), cwd=repo)
    assert result.returncode == 0, result.stderr


def _source_repo(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Snapshot Test")
    _git(path, "config", "user.email", "snapshot@example.invalid")
    (path / "README.md").write_text("# Example\n\nA Java library.\n", encoding="utf-8")
    (path / "pom.xml").write_text(
        "<project><modelVersion>4.0.0</modelVersion>"
        "<groupId>example</groupId><artifactId>demo</artifactId>"
        "<version>1.0</version></project>",
        encoding="utf-8",
    )
    _git(path, "add", ".")
    _git(path, "commit", "-m", "seed")
    return path


def _entry(source: Path) -> ProductEntry:
    return ProductEntry(
        family="example",
        platform="java",
        repo_name="Example",
        repo_url="https://github.com/example-org/Example",
        clone_url=str(source),
        active=True,
        discovered_via="test",
        mode="dry_run",
        ecosystem="java",
        policy_profile=None,
    )


def test_capture_records_revision_readme_inventory_and_package_roots(tmp_path):
    source = _source_repo(tmp_path / "source")
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)

    snapshot = capture_repository_snapshot(entry, baseline)

    assert snapshot.org_repo == ORG_REPO
    assert snapshot.root_path == baseline.resolve()
    assert snapshot.readme_path == "README.md"
    assert len(snapshot.readme_sha256 or "") == 64
    assert len(snapshot.inventory_sha256) == 64
    assert snapshot.provenance.git_tree_sha256 == snapshot.inventory_sha256
    assert [(root.ecosystem, root.manifest_path) for root in snapshot.package_roots] == [
        ("java", "pom.xml")
    ]
    verify_repository_snapshot(snapshot)


def test_bound_snapshot_suppresses_remote_reobservation_for_clone_and_profile(
    tmp_path, monkeypatch
):
    source = _source_repo(tmp_path / "source")
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)
    snapshot = capture_repository_snapshot(entry, baseline)

    def _network_forbidden(*args, **kwargs):
        raise AssertionError("a bound snapshot must suppress remote revision probes")

    monkeypatch.setattr(clone_module, "remote_head_sha", _network_forbidden)
    monkeypatch.setattr(cached, "remote_head_sha", _network_forbidden)
    with repository_snapshot_scope(snapshot):
        assert current_repository_snapshot(ORG_REPO) == snapshot
        assert clone_baseline(entry, baseline) == baseline.resolve()
        profile = cached.get_or_build_profile(entry)

    assert profile.source_revision == snapshot.source_revision
    assert profile.package_roots == list(snapshot.package_roots)
    assert current_repository_snapshot() is None


def test_snapshot_scope_fails_closed_when_readme_changes(tmp_path):
    source = _source_repo(tmp_path / "source")
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)
    snapshot = capture_repository_snapshot(entry, baseline)

    with pytest.raises(RepositorySnapshotError, match="README changed"):
        with repository_snapshot_scope(snapshot):
            (baseline / "README.md").write_text("# Mutated\n", encoding="utf-8")


def test_snapshot_cannot_be_reused_for_another_repository(tmp_path):
    source = _source_repo(tmp_path / "source")
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)
    snapshot = capture_repository_snapshot(entry, baseline)

    with repository_snapshot_scope(snapshot):
        with pytest.raises(RepositorySnapshotError, match="not requested repository"):
            current_repository_snapshot("another/repository")
