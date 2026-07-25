"""Committed investigation evidence must be inventoried from Git blobs."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[2]
        / "plans"
        / "investigations"
        / "tools"
        / "evidence_manifest.py"
    )
    spec = importlib.util.spec_from_file_location("investigation_evidence_manifest", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_committed_manifest_includes_blob_missing_from_working_tree(tmp_path, monkeypatch):
    module = _load_module()
    repository = tmp_path / "repository"
    evidence = repository / "plans" / "investigations" / "evidence" / "proof"
    evidence.mkdir(parents=True)
    retained = evidence / "retained.json"
    absent = evidence / "working-tree-absent.json"
    retained.write_text('{"retained": true}\n', encoding="utf-8")
    absent.write_text('{"committed": true}\n', encoding="utf-8")

    _git(repository, "init")
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "Evidence Test")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "fixture")
    absent.unlink()

    monkeypatch.setattr(module, "REPO_ROOT", repository)
    monkeypatch.setattr(module, "OUT", repository / "plans/investigations/control/manifest.json")
    manifest = module._build_committed_manifest(source_head_commit="a" * 40)

    entries = manifest["sha256_crlf_normalized"]
    assert isinstance(entries, dict)
    assert "plans/investigations/evidence/proof/retained.json" in entries
    assert "plans/investigations/evidence/proof/working-tree-absent.json" in entries
    assert manifest["file_count"] == 2
