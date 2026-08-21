"""Tests for self-contained, revision-bound repository knowledge generation."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from readme_agent.facts.repository_knowledge_generator import generate_repository_knowledge
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, timeout=15
    )
    return result.stdout.strip()


def _repository(root: Path) -> RepositorySnapshotV1:
    (root / "src/aspose_note").mkdir(parents=True)
    (root / "README.md").write_text("# Aspose.Note FOSS for Python\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "aspose-note-foss"\nversion = "0.1.0"\nlicense = "MIT"\n',
        encoding="utf-8",
    )
    (root / "src/aspose_note/__init__.py").write_text(
        'class Notebook:\n    """Represent a OneNote notebook."""\n\n'
        '    def save_pdf(self, path: str) -> None:\n        """Save as PDF."""\n',
        encoding="utf-8",
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Knowledge Test")
    _git(root, "config", "user.email", "knowledge@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    revision = _git(root, "rev-parse", "HEAD")
    inventory = _git(root, "ls-tree", "-r", "--full-tree", "HEAD") + "\n"
    readme = root / "README.md"
    return RepositorySnapshotV1(
        org_repo="aspose-note-foss/Aspose.Note-FOSS-for-Python",
        source_revision=revision,
        snapshot_root=str(root.resolve()),
        readme_path="README.md",
        readme_sha256=hashlib.sha256(readme.read_bytes()).hexdigest(),
        inventory_sha256=hashlib.sha256(inventory.encode()).hexdigest(),
        captured_at="2026-08-20T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/note.git",
            git_tree_sha256=hashlib.sha256(inventory.encode()).hexdigest(),
        ),
    )


def test_generation_is_self_contained_and_identical_retry_reuses_bytes(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    snapshot = _repository(repository)
    destination = tmp_path / "knowledge" / snapshot.source_revision

    first = generate_repository_knowledge(
        snapshot,
        family="note",
        platform="python",
        output_root=destination,
    )
    second = generate_repository_knowledge(
        snapshot,
        family="note",
        platform="python",
        output_root=destination,
    )

    assert first.status == "generated"
    assert second.status == "reused"
    assert first.artifacts == second.artifacts
    assert first.generator_sha256 == second.generator_sha256
    assert "model.yaml" in first.artifacts
    assert "api_surface.json" in first.artifacts
    assert "formats.json" in first.artifacts
    assert not list(destination.rglob("__pycache__"))
