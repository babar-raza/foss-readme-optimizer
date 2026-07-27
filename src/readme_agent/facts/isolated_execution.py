"""Execute untrusted repository commands in disposable hardened Docker containers."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Protocol

from readme_agent.errors import ReadmeAgentError
from readme_agent.evidence.redaction import redact
from readme_agent.facts.example_execution import secret_free_environment
from readme_agent.facts.isolated_execution_inputs import build_isolated_input_bundle
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.gitsafety.process import run_bounded


class IsolatedExecutionError(ReadmeAgentError):
    """The fail-closed container boundary could not be established."""

    exit_code = 3


class DockerCommandRunner(Protocol):
    """Narrow injectable seam around the trusted Docker CLI."""

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one Docker control-plane command without ambient credentials."""


class LocalDockerCommandRunner:
    """Bounded Docker CLI adapter used by the production executor."""

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


def _require_success(
    runner: DockerCommandRunner,
    argv: list[str],
    *,
    timeout_seconds: float = 30,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[str]:
    result = runner.run(argv, timeout_seconds=timeout_seconds, input_bytes=input_bytes)
    if result.returncode != 0:
        detail = redact((result.stderr or result.stdout).strip())
        raise IsolatedExecutionError(f"docker {' '.join(argv[:2])} failed: {detail}")
    return result


def inspect_container_image(
    runner: DockerCommandRunner,
    immutable_image: str,
) -> ContainerImageIdentityV1:
    """Verify one locally available immutable Linux container image."""

    image_result = _require_success(
        runner,
        ["image", "inspect", immutable_image],
    )
    try:
        image_record = json.loads(image_result.stdout)[0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise IsolatedExecutionError("Docker returned invalid image identity JSON") from exc
    repo_digests = image_record.get("RepoDigests") or []
    if immutable_image not in repo_digests:
        raise IsolatedExecutionError(
            "locally resolved image does not advertise the requested immutable digest"
        )
    if image_record.get("Os") != "linux":
        raise IsolatedExecutionError("isolated executor requires a Linux container image")
    engine = _require_success(runner, ["version", "--format", "{{.Server.Version}}"])
    return ContainerImageIdentityV1(
        requested_reference=immutable_image,
        repo_digest=immutable_image,
        image_id=str(image_record["Id"]),
        operating_system=str(image_record["Os"]),
        architecture=str(image_record["Architecture"]),
        engine_version=engine.stdout.strip(),
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


def _removed(runner: DockerCommandRunner, kind: str, identity: str) -> bool:
    inspect = runner.run([kind, "inspect", identity], timeout_seconds=10)
    return inspect.returncode != 0


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
    seed_created = False
    execution_created = False
    volume_created = False
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
        _require_success(
            active_runner, ["volume", "create", "--label", "readme-agent=true", volume]
        )
        volume_created = True
        uid, gid = request.policy.user.split(":")
        seed = _require_success(
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
        seed_created = True
        _require_success(
            active_runner,
            ["cp", "-", f"{seed_name}:{request.policy.workspace_path}"],
            timeout_seconds=60,
            input_bytes=inputs.source_archive,
        )
        seed_start = _require_success(
            active_runner,
            ["start", "--attach", seed.stdout.strip()],
            timeout_seconds=60,
        )
        if seed_start.returncode != 0:
            raise IsolatedExecutionError("workspace ownership initialization failed")
        _require_success(active_runner, ["rm", "--force", seed_name])
        seed_created = False

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
        create = _require_success(active_runner, create_argv)
        execution_created = True
        container_id = create.stdout.strip()
        _require_success(active_runner, ["start", container_id])
        top = active_runner.run(
            ["top", container_id, "-eo", "pid,ppid,user,args"], timeout_seconds=10
        )
        if top.returncode == 0:
            process_inventory = [line for line in top.stdout.splitlines() if line.strip()]
        wait = active_runner.run(
            ["wait", container_id],
            timeout_seconds=request.policy.timeout_seconds,
        )
        if wait.returncode == 124:
            timed_out = True
            active_runner.run(["kill", container_id], timeout_seconds=15)
        logs = active_runner.run(["logs", container_id], timeout_seconds=30)
        stdout = redact(logs.stdout)
        stderr = redact(logs.stderr)
        inspect = _require_success(active_runner, ["container", "inspect", container_id])
        state = json.loads(inspect.stdout)[0]["State"]
        return_code = 124 if timed_out else int(state["ExitCode"])
        oom_killed = bool(state.get("OOMKilled", False))
    except BaseException as exc:
        execution_error = exc
    finally:
        if execution_created:
            active_runner.run(["rm", "--force", execution_name], timeout_seconds=15)
        if seed_created:
            active_runner.run(["rm", "--force", seed_name], timeout_seconds=15)
        if volume_created:
            active_runner.run(["volume", "rm", "--force", volume], timeout_seconds=15)
        cleanup = ContainerCleanupV1(
            execution_container_removed=_removed(active_runner, "container", execution_name),
            seed_container_removed=_removed(active_runner, "container", seed_name),
            workspace_volume_removed=_removed(active_runner, "volume", volume),
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
