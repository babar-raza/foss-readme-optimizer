"""Live proof against the real pilot repo -- real network clone. Excluded from default CI run."""

from pathlib import Path

import pytest

from readme_agent.gitsafety.clone import _force_rmtree, clone_baseline, create_work_clone
from readme_agent.gitsafety.hooks import install_pre_push_hook
from readme_agent.gitsafety.neuter import neuter_push
from readme_agent.gitsafety.verify import verify_push_blocked
from readme_agent.registry.loader import find_entry

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.live
def test_full_pipeline_against_real_pilot_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    entry = find_entry("aspose-3d-foss/Aspose.3D-FOSS-for-Java")
    assert entry is not None

    baseline_path = tmp_path / "baseline"
    work_path = tmp_path / "work"
    try:
        clone_baseline(entry, baseline_path)
        assert (baseline_path / "README.md").exists()

        create_work_clone(entry, baseline_path, work_path)
        neuter_push(work_path)
        install_pre_push_hook(work_path)

        proof = verify_push_blocked(work_path)
        assert proof.ok, proof.detail
    finally:
        if baseline_path.exists():
            _force_rmtree(baseline_path)
        if work_path.exists():
            _force_rmtree(work_path)
