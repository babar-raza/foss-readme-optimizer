"""Blocking prompt ownership, routing, documentation, and invalidation controls."""

from __future__ import annotations

import shutil
from pathlib import Path

from readme_agent import env
from readme_agent.llm.prompt_hygiene import audit_prompt_hygiene
from readme_agent.llm.prompt_source_audit import scan_prompt_source

REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_audit_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(REPO_ROOT / "prompts", root / "prompts")
    shutil.copytree(REPO_ROOT / "src" / "readme_agent", root / "src" / "readme_agent")
    return root


def test_real_prompt_inventory_is_clean():
    report = audit_prompt_hygiene(repo_root=REPO_ROOT)
    assert report.errors == []
    assert len(report.entries) == len(env.JOB_MODEL_ROUTING)


def test_orphan_route_is_blocking(tmp_path):
    root = _copy_audit_tree(tmp_path)
    report = audit_prompt_hygiene(
        repo_root=root,
        model_routes={**env.JOB_MODEL_ROUTING, "orphan_paid_job": "model"},
    )
    assert any("without prompts" in error and "orphan_paid_job" in error for error in report.errors)


def test_missing_prompt_file_is_blocking(tmp_path):
    root = _copy_audit_tree(tmp_path)
    (root / "prompts" / "generation" / "draft_product_truth.yaml").unlink()
    report = audit_prompt_hygiene(repo_root=root)
    assert any(
        "without prompts" in error and "draft_product_truth" in error for error in report.errors
    )


def test_unregistered_backup_file_is_blocking(tmp_path):
    root = _copy_audit_tree(tmp_path)
    (root / "prompts" / "generation" / "draft_product_truth.backup").write_text(
        "not an active manifest\n", encoding="utf-8"
    )
    report = audit_prompt_hygiene(repo_root=root)
    assert any("unregistered files" in error for error in report.errors)


def test_stale_documentation_is_blocking(tmp_path):
    root = _copy_audit_tree(tmp_path)
    readme = root / "prompts" / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "`DraftProductTruthV1`", "`StaleProductTruthContract`"
        ),
        encoding="utf-8",
    )
    report = audit_prompt_hygiene(repo_root=root)
    assert "prompts/README.md metadata is stale for 'draft_product_truth'" in report.errors


def test_inline_prompt_outside_declared_consumer_is_blocking(tmp_path):
    root = tmp_path / "repository"
    source = root / "src" / "readme_agent" / "unsafe.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'MESSAGES = [{"role": "system", "content": "You are an inline prompt."}]\n',
        encoding="utf-8",
    )
    *_references, errors = scan_prompt_source(root)
    assert errors == ["inline prompt message at src/readme_agent/unsafe.py:1"]


def test_each_prompt_invalidates_only_its_declared_scope(tmp_path):
    root = _copy_audit_tree(tmp_path)
    baseline = audit_prompt_hygiene(repo_root=root)
    assert baseline.clean
    for entry in baseline.entries:
        prompt_path = root / entry.path
        original = prompt_path.read_text(encoding="utf-8")
        prompt_path.write_text(original + "\n# mutation control\n", encoding="utf-8")
        mutated = audit_prompt_hygiene(repo_root=root)
        changed_scopes = {
            scope
            for scope, digest in baseline.dependency_hashes.items()
            if mutated.dependency_hashes.get(scope) != digest
        }
        assert changed_scopes == {entry.invalidation_scope}, entry.prompt_id
        assert mutated.prompt_hashes[entry.prompt_id] != baseline.prompt_hashes[entry.prompt_id]
        prompt_path.write_text(original, encoding="utf-8")
