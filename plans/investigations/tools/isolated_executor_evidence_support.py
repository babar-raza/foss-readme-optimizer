"""Run live isolated-executor controls and inspect disposable-resource cleanup."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from readme_agent.facts.example_execution import execute_example, secret_free_environment
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
)

IMAGE = "alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce"
CONTROL_SCRIPT = """set -eu
printf 'uid=%s\\n' "$(id -u)"
printf 'pids=%s\\n' "$(cat /sys/fs/cgroup/pids.max)"
printf 'memory=%s\\n' "$(cat /sys/fs/cgroup/memory.max)"
printf 'cpu=%s\\n' "$(cat /sys/fs/cgroup/cpu.max)"
printf 'interfaces=%s\\n' "$(ls /sys/class/net)"
test -z "${GH_TOKEN+x}"
test ! -e /operator-host-sentinel
grep -q '^overlay / overlay ro,' /proc/mounts
printf 'root_read_only=true\\n'
sleep 1
printf 'isolation_controls_passed=true\\n'
"""


def docker_inventory() -> dict[str, list[str]]:
    """List any container or volume that survived the production cleanup path."""

    environment = secret_free_environment()
    commands = {
        "containers": [
            "docker",
            "ps",
            "-a",
            "--filter",
            "label=readme-agent=true",
            "--format",
            "{{.ID}} {{.Names}}",
        ],
        "volumes": [
            "docker",
            "volume",
            "ls",
            "--filter",
            "label=readme-agent=true",
            "--format",
            "{{.Name}}",
        ],
    }
    inventory: dict[str, list[str]] = {}
    for name, command in commands.items():
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        inventory[name] = [line for line in result.stdout.splitlines() if line.strip()]
    return inventory


def run_live_controls() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Exercise success, timeout, and host-ineligibility controls through public seams."""

    with tempfile.TemporaryDirectory(prefix="readme-agent-isolation-proof-") as raw_root:
        root = Path(raw_root)
        (root / "control.sh").write_text(CONTROL_SCRIPT, encoding="utf-8", newline="\n")
        (root / "timeout.sh").write_text("sleep 30\n", encoding="utf-8", newline="\n")
        policy = IsolatedExecutionPolicyV1(
            immutable_image=IMAGE,
            cpu_limit=0.5,
            memory_mebibytes=128,
            pids_limit=32,
            timeout_seconds=10,
        )
        prior_token = os.environ.get("GH_TOKEN")
        os.environ["GH_TOKEN"] = "ghp_syntheticSecretValue123456"
        try:
            success = execute_isolated(
                IsolatedExecutionRequestV1(
                    org_repo="control/isolation-proof",
                    source_revision="live-control",
                    source_root=root,
                    argv=["/bin/sh", "./control.sh"],
                    policy=policy,
                )
            )
        finally:
            if prior_token is None:
                os.environ.pop("GH_TOKEN", None)
            else:
                os.environ["GH_TOKEN"] = prior_token
        timeout = execute_isolated(
            IsolatedExecutionRequestV1(
                org_repo="control/isolation-timeout-proof",
                source_revision="live-timeout-control",
                source_root=root,
                argv=["/bin/sh", "./timeout.sh"],
                policy=policy.model_copy(update={"timeout_seconds": 0.2}),
            )
        )
        host = execute_example(
            [sys.executable, "-c", "print('host-diagnostic-only')"],
            workspace=root,
            timeout_seconds=10,
            base_environment={"GH_TOKEN": "ghp_syntheticSecretValue123456"},
        )
    return (
        success.model_dump(mode="json"),
        timeout.model_dump(mode="json"),
        host.model_dump(mode="json"),
    )
