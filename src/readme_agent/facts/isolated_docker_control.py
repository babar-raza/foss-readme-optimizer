"""Validate Docker image identity and converged container state."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Protocol

from readme_agent.errors import ReadmeAgentError
from readme_agent.evidence.redaction import redact
from readme_agent.facts.isolated_execution_schema import ContainerImageIdentityV1


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


def require_docker_success(
    runner: DockerCommandRunner,
    argv: list[str],
    *,
    timeout_seconds: float = 30,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one Docker command or raise a redacted typed failure."""

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

    image_result = require_docker_success(runner, ["image", "inspect", immutable_image])
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
    engine = require_docker_success(runner, ["version", "--format", "{{.Server.Version}}"])
    return ContainerImageIdentityV1(
        requested_reference=immutable_image,
        repo_digest=immutable_image,
        image_id=str(image_record["Id"]),
        operating_system=str(image_record["Os"]),
        architecture=str(image_record["Architecture"]),
        engine_version=engine.stdout.strip(),
    )


def _container_is_listed(runner: DockerCommandRunner, identity: str) -> bool:
    listing = runner.run(
        ["ps", "-aq", "--filter", f"id={identity}"],
        timeout_seconds=10,
    )
    return listing.returncode == 0 and bool(listing.stdout.strip())


def await_terminal_container_state(
    runner: DockerCommandRunner,
    identity: str,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Wait for Docker's inspect and listing views to converge on terminal state."""

    deadline = time.monotonic() + max(0.1, timeout_seconds)
    absent_observations = 0
    last_detail = "container state was not observed"
    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())
        observed = runner.run(
            ["container", "inspect", identity],
            timeout_seconds=min(10, remaining),
        )
        if observed.returncode == 0:
            absent_observations = 0
            try:
                state = json.loads(observed.stdout)[0]["State"]
            except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise IsolatedExecutionError(
                    "Docker returned invalid container state JSON"
                ) from exc
            if not bool(state.get("Running", False)):
                return state
            last_detail = "container remained running after docker wait"
        elif _container_is_listed(runner, identity):
            absent_observations = 0
            last_detail = redact((observed.stderr or observed.stdout).strip())
        else:
            absent_observations += 1
            last_detail = redact((observed.stderr or observed.stdout).strip())
            if absent_observations >= 3:
                raise IsolatedExecutionError(
                    "container disappeared before terminal state could be verified"
                )
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
    raise IsolatedExecutionError(f"container state did not converge: {last_detail}")
