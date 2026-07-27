"""Live Docker proof for isolation, resource, timeout, and cleanup controls."""

from __future__ import annotations

import pytest

from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
)

IMAGE = "alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce"


@pytest.mark.live
def test_real_container_enforces_truth_isolation_controls(tmp_path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ghp_syntheticSecretValue123456")
    (tmp_path / "control.sh").write_text(
        """set -eu
test "$(id -u)" = "65534"
test "$(cat /sys/fs/cgroup/pids.max)" = "32"
test "$(cat /sys/fs/cgroup/memory.max)" = "134217728"
test "$(cat /sys/fs/cgroup/cpu.max)" = "50000 100000"
test "$(ls /sys/class/net)" = "lo"
test -z "${GH_TOKEN+x}"
test ! -e /operator-host-sentinel
grep -q '^overlay / overlay ro,' /proc/mounts
sleep 1
printf 'isolation-controls-passed\\n'
""",
        encoding="utf-8",
        newline="\n",
    )
    policy = IsolatedExecutionPolicyV1(
        immutable_image=IMAGE,
        cpu_limit=0.5,
        memory_mebibytes=128,
        pids_limit=32,
        timeout_seconds=10,
    )

    result = execute_isolated(
        IsolatedExecutionRequestV1(
            org_repo="control/isolation-proof",
            source_revision="live-control",
            source_root=tmp_path,
            argv=["/bin/sh", "./control.sh"],
            policy=policy,
        )
    )

    assert result.return_code == 0, result
    assert result.truth_eligible is True
    assert result.cleanup.complete is True
    assert "isolation-controls-passed" in result.stdout
    assert result.process_inventory
    assert "GH_TOKEN" not in result.environment_names
    assert "ghp_syntheticSecretValue123456" not in result.stdout + result.stderr


@pytest.mark.live
def test_real_container_timeout_kills_work_and_cleans_resources(tmp_path):
    (tmp_path / "timeout.sh").write_text("sleep 30\n", encoding="utf-8", newline="\n")
    policy = IsolatedExecutionPolicyV1(
        immutable_image=IMAGE,
        timeout_seconds=0.2,
        memory_mebibytes=64,
        pids_limit=16,
    )

    result = execute_isolated(
        IsolatedExecutionRequestV1(
            org_repo="control/isolation-timeout-proof",
            source_revision="live-timeout-control",
            source_root=tmp_path,
            argv=["/bin/sh", "./timeout.sh"],
            policy=policy,
        )
    )

    assert result.return_code == 124
    assert result.timed_out is True
    assert result.cleanup.complete is True
