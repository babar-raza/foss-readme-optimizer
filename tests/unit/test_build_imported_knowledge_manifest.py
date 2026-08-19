"""Determinism and sensitivity proofs for the imported-knowledge corpus
manifest generator (Gate R1.1)."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_DIR = _REPO_ROOT / "scripts" / "data-refresh"


@pytest.fixture
def manifest_module():
    sys.path.insert(0, str(_SCRIPT_DIR))
    try:
        module = import_module("build_imported_knowledge_manifest")
        yield module
    finally:
        sys.path.remove(str(_SCRIPT_DIR))


def _make_corpus(root: Path) -> Path:
    knowledge_root = root / "data" / "imported" / "knowledge"
    bundle = knowledge_root / "cells" / "python" / "merged"
    bundle.mkdir(parents=True)
    (bundle / "claims.json").write_text(
        '[{"claim_id": "CLM-1", "kind": "feature"}]', encoding="utf-8"
    )
    (bundle / "model.yaml").write_text(
        "family: cells\nplatform: python\nrepo_sha: abc123\n", encoding="utf-8"
    )
    return knowledge_root


def test_two_consecutive_runs_produce_byte_identical_manifest(
    manifest_module, tmp_path, monkeypatch
):
    knowledge_root = _make_corpus(tmp_path)
    output_path = tmp_path / "data" / "imported" / "knowledge_manifest.json"
    monkeypatch.setattr(manifest_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "KNOWLEDGE_ROOT", knowledge_root)
    monkeypatch.setattr(manifest_module, "OUTPUT_PATH", output_path)

    manifest_module.main()
    first_bytes = output_path.read_bytes()
    manifest_module.main()
    second_bytes = output_path.read_bytes()

    assert first_bytes == second_bytes


def test_manifest_has_no_generated_at_field(manifest_module, tmp_path, monkeypatch):
    """The specific defect: a wall-clock field embedded in a hashed
    contract. This regression test fails against the pre-repair generator
    (which wrote `generated_at`) and passes after the repair."""

    knowledge_root = _make_corpus(tmp_path)
    monkeypatch.setattr(manifest_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "KNOWLEDGE_ROOT", knowledge_root)

    manifest = manifest_module.build_manifest()

    assert "generated_at" not in manifest


def test_one_byte_corpus_mutation_changes_bundle_and_aggregate_hash(
    manifest_module, tmp_path, monkeypatch
):
    knowledge_root = _make_corpus(tmp_path)
    monkeypatch.setattr(manifest_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "KNOWLEDGE_ROOT", knowledge_root)

    before = manifest_module.build_manifest()
    claims_path = knowledge_root / "cells" / "python" / "merged" / "claims.json"
    claims_path.write_text(
        claims_path.read_text(encoding="utf-8") + " ", encoding="utf-8"
    )  # one-byte mutation
    after = manifest_module.build_manifest()

    assert before["aggregate_sha256"] != after["aggregate_sha256"]
    before_bundle = next(b for b in before["bundles"] if b["family"] == "cells")
    after_bundle = next(b for b in after["bundles"] if b["family"] == "cells")
    assert before_bundle["bundle_sha256"] != after_bundle["bundle_sha256"]


def test_unrelated_file_outside_knowledge_tree_does_not_change_hashes(
    manifest_module, tmp_path, monkeypatch
):
    knowledge_root = _make_corpus(tmp_path)
    monkeypatch.setattr(manifest_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "KNOWLEDGE_ROOT", knowledge_root)

    before = manifest_module.build_manifest()
    unrelated = tmp_path / "data" / "imported" / "keywords" / "cells.json"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text('["unrelated"]', encoding="utf-8")
    after = manifest_module.build_manifest()

    assert before["aggregate_sha256"] == after["aggregate_sha256"]
    assert before["bundles"] == after["bundles"]


def test_a_different_bundle_family_mutation_does_not_change_an_unrelated_bundle_hash(
    manifest_module, tmp_path, monkeypatch
):
    knowledge_root = _make_corpus(tmp_path)
    other_bundle = knowledge_root / "pdf" / "python" / "merged"
    other_bundle.mkdir(parents=True)
    (other_bundle / "claims.json").write_text(
        '[{"claim_id": "CLM-2", "kind": "license"}]', encoding="utf-8"
    )
    (other_bundle / "model.yaml").write_text(
        "family: pdf\nplatform: python\nrepo_sha: def456\n", encoding="utf-8"
    )
    monkeypatch.setattr(manifest_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "KNOWLEDGE_ROOT", knowledge_root)

    before = manifest_module.build_manifest()
    cells_claims = knowledge_root / "cells" / "python" / "merged" / "claims.json"
    cells_claims.write_text(cells_claims.read_text(encoding="utf-8") + " ", encoding="utf-8")
    after = manifest_module.build_manifest()

    before_pdf = next(b for b in before["bundles"] if b["family"] == "pdf")
    after_pdf = next(b for b in after["bundles"] if b["family"] == "pdf")
    assert before_pdf["bundle_sha256"] == after_pdf["bundle_sha256"]
    before_cells = next(b for b in before["bundles"] if b["family"] == "cells")
    after_cells = next(b for b in after["bundles"] if b["family"] == "cells")
    assert before_cells["bundle_sha256"] != after_cells["bundle_sha256"]
