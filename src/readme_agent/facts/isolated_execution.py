"""Execute untrusted repository commands in disposable hardened Docker containers."""

from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from datetime import UTC, datetime

from readme_agent.evidence.redaction import redact
from readme_agent.facts.example_execution import secret_free_environment
from readme_agent.facts.isolated_cleanup import remove_docker_resource
from readme_agent.facts.isolated_docker_control import (
    DockerCommandRunner,
    IsolatedExecutionError,
    await_terminal_container_state,
    inspect_container_image,
    require_docker_success,
)
from readme_agent.facts.isolated_execution_inputs import build_isolated_input_bundle
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.gitsafety.process import run_bounded


class LocalDockerCommandRunner:
    """Bounded Docker CLI adapter used by the production executor."""

    cleanup_stability_seconds = 1.0

    def __init__(self, executable: str | None = None) -> None:
        self._executable = executable or shutil.which("docker") or ""

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if not self._executable:
            raise IsolatedExecutionError("Docker CLI is unavailable")
        return run_bounded(
            [self._executable, *argv],
            timeout=timeout_seconds,
            input_bytes=input_bytes,
            env=secret_free_environment(),
        )


def _resource_flags(request: IsolatedExecutionRequestV1) -> list[str]:
    policy = request.policy
    return [
        "--label",
        "readme-agent=true",
        "--network",
        policy.network_mode,
        "--read-only",
        "--cpus",
        str(policy.cpu_limit),
        "--memory",
        f"{policy.memory_mebibytes}m",
        "--memory-swap",
        f"{policy.memory_mebibytes}m",
        "--pids-limit",
        str(policy.pids_limit),
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        f"/tmp:rw,noexec,nosuid,nodev,size={policy.tmpfs_mebibytes}m",
    ]


def execute_isolated(
    request: IsolatedExecutionRequestV1,
    *,
    runner: DockerCommandRunner | None = None,
) -> IsolatedExecutionResultV1:
    """Copy inputs into a named volume and run argv with no host bind or network."""

    active_runner = runner or LocalDockerCommandRunner()
    inputs = build_isolated_input_bundle(request)
    image = inspect_container_image(active_runner, request.policy.immutable_image)
    suffix = uuid.uuid4().hex
    volume = f"readme-agent-workspace-{suffix}"
    seed_name = f"readme-agent-seed-{suffix}"
    execution_name = f"readme-agent-exec-{suffix}"
    container_id = ""
    process_inventory: list[str] = []
    return_code = 125
    stdout = ""
    stderr = ""
    timed_out = False
    oom_killed = False
    started_at = datetime.now(UTC).isoformat()
    execution_error: BaseException | None = None
    try:
        require_docker_success(
            active_runner, ["volume", "create", "--label", "readme-agent=true", volume]
        )
        uid, gid = request.policy.user.split(":")
        seed = require_docker_success(
            active_runner,
            [
                "create",
                "--name",
                seed_name,
                *_resource_flags(request),
                "--cap-add",
                "CHOWN",
                "--user",
                "0:0",
                "--volume",
                f"{volume}:{request.policy.workspace_path}",
                "--entrypoint",
                "/bin/sh",
                request.policy.immutable_image,
                "-c",
                f"chown -R {uid}:{gid} {request.policy.workspace_path}",
            ],
        )
        require_docker_success(
            active_runner,
            ["cp", "-", f"{seed_name}:{request.policy.workspace_path}"],
            timeout_seconds=60,
            input_bytes=inputs.source_archive,
        )
        seed_start = require_docker_success(
            active_runner,
            ["start", "--attach", seed.stdout.strip()],
            timeout_seconds=60,
        )
        if seed_start.returncode != 0:
            raise IsolatedExecutionError("workspace ownership initialization failed")
        require_docker_success(active_runner, ["rm", "--force", seed_name])

        create_argv = [
            "create",
            "--name",
            execution_name,
            *_resource_flags(request),
            "--user",
            request.policy.user,
            "--volume",
            f"{volume}:{request.policy.workspace_path}",
            "--workdir",
            request.policy.workspace_path,
        ]
        for name, value in sorted(request.environment.items()):
            create_argv.extend(["--env", f"{name}={value}"])
        create_argv.extend(
            ["--entrypoint", request.argv[0], request.policy.immutable_image, *request.argv[1:]]
        )
        create = require_docker_success(active_runner, create_argv)
        container_id = create.stdout.strip()
        require_docker_success(active_runner, ["start", container_id])
        top = active_runner.run(
            ["top", container_id, "-eo", "pid,ppid,user,args"], timeout_seconds=10
        )
        if top.returncode == 0:
            process_inventory = [line for line in top.stdout.splitlines() if line.strip()]
        wait_started = time.monotonic()
        wait = active_runner.run(
            ["wait", container_id],
            timeout_seconds=request.policy.timeout_seconds,
        )
        if wait.returncode == 124:
            timed_out = True
            active_runner.run(["kill", container_id], timeout_seconds=15)
            waited_exit_code: int | None = None
        elif wait.returncode != 0:
            detail = redact((wait.stderr or wait.stdout).strip())
            raise IsolatedExecutionError(f"docker wait failed: {detail}")
        else:
            try:
                waited_exit_code = int(wait.stdout.strip())
            except ValueError as exc:
                raise IsolatedExecutionError(
                    "docker wait did not return one exact container exit code"
                ) from exc
        state_timeout = (
            15.0
            if timed_out
            else max(0.1, request.policy.timeout_seconds - (time.monotonic() - wait_started))
        )
        state = await_terminal_container_state(
            active_runner,
            container_id,
            timeout_seconds=state_timeout,
        )
        logs = require_docker_success(active_runner, ["logs", container_id])
        stdout = redact(logs.stdout)
        stderr = redact(logs.stderr)
        inspected_exit_code = int(state["ExitCode"])
        if waited_exit_code is not None and waited_exit_code != inspected_exit_code:
            raise IsolatedExecutionError("docker wait and inspect returned different exit codes")
        return_code = 124 if timed_out else inspected_exit_code
        oom_killed = bool(state.get("OOMKilled", False))
    except BaseException as exc:
        execution_error = exc
    finally:
        cleanup = ContainerCleanupV1(
            execution_container_removed=remove_docker_resource(
                active_runner, "container", execution_name
            ),
            seed_container_removed=remove_docker_resource(active_runner, "container", seed_name),
            workspace_volume_removed=remove_docker_resource(active_runner, "volume", volume),
        )
    if execution_error is not None:
        if isinstance(execution_error, (KeyboardInterrupt, SystemExit)):
            raise execution_error
        if isinstance(execution_error, IsolatedExecutionError):
            raise execution_error
        raise IsolatedExecutionError(
            f"isolated execution failed: {execution_error}"
        ) from execution_error

    finished_at = datetime.now(UTC).isoformat()
    return IsolatedExecutionResultV1(
        truth_eligible=cleanup.complete,
        org_repo=request.org_repo,
        source_revision=request.source_revision,
        argv=request.argv,
        environment_names=sorted(request.environment),
        input_sha256=inputs.input_sha256,
        input_file_count=inputs.input_file_count,
        policy_sha256=inputs.policy_sha256,
        policy=request.policy,
        image=image,
        container_id=container_id,
        process_inventory=process_inventory,
        return_code=return_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        oom_killed=oom_killed,
        started_at=started_at,
        finished_at=finished_at,
        cleanup=cleanup,
    )
