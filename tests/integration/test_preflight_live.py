"""Live preflight proof -- real network, real secrets. Excluded from default CI run."""

from pathlib import Path

import pytest

from readme_agent.preflight.runner import run_preflight

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.live
def test_preflight_passes_against_real_env(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    result = run_preflight()
    assert result.identity.ok, result.identity.error
    for repo in result.repos:
        assert repo.ok, f"{repo.org_repo}: {repo.error}"
    assert result.llm.ok, result.llm.error
    assert result.ok
