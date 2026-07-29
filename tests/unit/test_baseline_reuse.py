"""Tests for verified cross-process baseline reuse."""

from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.gitsafety.baseline_reuse import verified_baseline_at_revision
from readme_agent.gitsafety.clone import clone_baseline, reset_clone_memo
from readme_agent.registry.models import ProductEntry


def _entry(source: Path) -> ProductEntry:
    return ProductEntry(
        family="test",
        platform="python",
        repo_name="Example",
        repo_url="https://github.com/example/Example",
        clone_url=str(source),
        active=True,
        discovered_via="manual",
        mode="disabled",
        ecosystem="python",
    )


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    run_git(["init"], cwd=source)
    run_git(["config", "user.email", "test@example.com"], cwd=source)
    run_git(["config", "user.name", "Test"], cwd=source)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    run_git(["add", "."], cwd=source)
    run_git(["commit", "-m", "initial"], cwd=source)
    return source


def _head(path: Path) -> str:
    return run_git(["rev-parse", "HEAD"], cwd=path).stdout.strip()


def test_clean_matching_baseline_survives_a_fresh_process_boundary(tmp_path):
    source = _source(tmp_path)
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)
    marker = baseline / ".git" / "reuse-marker"
    marker.write_text("preserved", encoding="utf-8")

    reset_clone_memo()
    result = verified_baseline_at_revision(
        entry,
        baseline,
        expected_revision=_head(source),
    )

    assert result == baseline
    assert marker.is_file()


def test_dirty_baseline_is_replaced_instead_of_reused(tmp_path):
    source = _source(tmp_path)
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)
    (baseline / "untracked.txt").write_text("dirty", encoding="utf-8")

    reset_clone_memo()
    verified_baseline_at_revision(
        entry,
        baseline,
        expected_revision=_head(source),
    )

    assert not (baseline / "untracked.txt").exists()


def test_wrong_origin_or_revision_is_replaced(tmp_path):
    source = _source(tmp_path)
    entry = _entry(source)
    baseline = tmp_path / "baseline"
    clone_baseline(entry, baseline)
    run_git(["remote", "set-url", "origin", str(tmp_path / "wrong")], cwd=baseline)

    reset_clone_memo()
    verified_baseline_at_revision(
        entry,
        baseline,
        expected_revision=_head(source),
    )

    assert run_git(["remote", "get-url", "origin"], cwd=baseline).stdout.strip() == str(source)
