from pathlib import Path

import pytest

from readme_agent.supervisor.contract_freeze import (
    PipelineContractSnapshotV1,
    build_plan_freeze,
    canonical_sha256,
    materialize_pipeline_snapshot,
    raw_sha256,
    verify_pipeline_snapshot,
)


def test_pipeline_snapshot_materializes_exact_read_only_bytes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src/example.py").write_bytes(b"value = 1\r\n")
    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    (repo / "src/example.py").write_bytes(b"value = 2\r\n")

    manifest = materialize_pipeline_snapshot(
        repo,
        selections={"src/example.py": ("modified", "facts/python", "selected adapter")},
        output_root=tmp_path / "snapshots",
    )

    loaded = PipelineContractSnapshotV1.model_validate(manifest.model_dump(mode="json"))
    verify_pipeline_snapshot(loaded)
    target = Path(loaded.snapshot_root) / loaded.files[0].snapshot_path
    assert target.read_bytes() == b"value = 2\r\n"


def test_pipeline_snapshot_rejects_mutated_bytes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file.txt").write_text("one", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    (repo / "file.txt").write_text("two", encoding="utf-8")
    manifest = materialize_pipeline_snapshot(
        repo,
        selections={"file.txt": ("modified", "runtime", "contract")},
        output_root=tmp_path / "snapshots",
    )
    target = Path(manifest.snapshot_root) / manifest.files[0].snapshot_path
    target.chmod(0o666)
    target.write_text("corrupt", encoding="utf-8")

    with pytest.raises(ValueError, match="snapshot mismatch"):
        verify_pipeline_snapshot(manifest)


def test_plan_freeze_replay_uses_committed_bytes_after_later_worktree_change(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    member = repo / "level8-autonomous-mission-task-graph.yaml"
    member.write_text("frozen\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    frozen_bytes = subprocess.run(
        ["git", "show", f"{commit}:level8-autonomous-mission-task-graph.yaml"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    path = "level8-autonomous-mission-task-graph.yaml"
    members = [{"path": path, "sha256": raw_sha256(frozen_bytes), "size": len(frozen_bytes)}]
    acceptance_id = canonical_sha256(
        {"control_commit": commit, "members": members, "result": "ACCEPTED"}
    )
    member.write_text("later valid work\n", encoding="utf-8")

    with pytest.raises(ValueError, match="member is dirty"):
        build_plan_freeze(
            repo,
            control_commit=commit,
            members=[path],
            acceptance_receipt_id=acceptance_id,
        )

    replayed = build_plan_freeze(
        repo,
        control_commit=commit,
        members=[path],
        acceptance_receipt_id=acceptance_id,
        require_worktree_match=False,
    )
    assert replayed.members[0].sha256 == raw_sha256(frozen_bytes)
