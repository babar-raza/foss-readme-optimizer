"""Fail-closed contracts and Docker-control wiring for isolated truth execution."""

from __future__ import annotations

import json
import subprocess

import pytest
from pydantic import ValidationError

from readme_agent.facts.isolated_execution import IsolatedExecutionError, execute_isolated
from readme_agent.facts.isolated_execution_inputs import build_isolated_input_bundle
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
)

IMAGE = "alpine@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce"


def _completed(
    argv: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class ScriptedDockerRunner:
    """Stateful fake that proves command construction and cleanup ordering."""

    def __init__(self, *, interrupt_wait: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.interrupt_wait = interrupt_wait
        self.removed_containers: set[str] = set()
        self.removed_volumes: set[str] = set()

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(argv)
        if argv[:2] == ["image", "inspect"]:
            return _completed(
                argv,
                stdout=json.dumps(
                    [
                        {
                            "RepoDigests": [IMAGE],
                            "Id": "sha256:" + "c" * 64,
                            "Os": "linux",
                            "Architecture": "amd64",
                        }
                    ]
                ),
            )
        if argv[:2] == ["version", "--format"]:
            return _completed(argv, stdout="28.4.0\n")
        if argv[:2] == ["volume", "create"]:
            return _completed(argv, stdout=argv[-1] + "\n")
        if argv[0] == "create":
            name = argv[argv.index("--name") + 1]
            return _completed(argv, stdout=f"{name}-id\n")
        if argv[0] == "cp":
            return _completed(argv)
        if argv[:2] == ["start", "--attach"]:
            return _completed(argv)
        if argv[0] == "start":
            return _completed(argv, stdout=argv[-1] + "\n")
        if argv[0] == "top":
            return _completed(argv, stdout="PID PPID USER COMMAND\n7 0 65534 /bin/echo ok\n")
        if argv[0] == "wait":
            if self.interrupt_wait:
                raise KeyboardInterrupt
            return _completed(argv, stdout="0\n")
        if argv[0] == "logs":
            return _completed(argv, stdout="ok\n")
        if argv[:2] == ["container", "inspect"]:
            if argv[-1] in self.removed_containers:
                return _completed(argv, returncode=1, stderr="not found")
            return _completed(
                argv,
                stdout=json.dumps(
                    [{"State": {"ExitCode": 0, "OOMKilled": False, "Running": False}}]
                ),
            )
        if argv[:2] == ["rm", "--force"]:
            self.removed_containers.add(argv[-1])
            return _completed(argv)
        if argv[:3] == ["volume", "rm", "--force"]:
            self.removed_volumes.add(argv[-1])
            return _completed(argv)
        if argv[:2] == ["volume", "inspect"]:
            return _completed(
                argv,
                returncode=1 if argv[-1] in self.removed_volumes else 0,
                stderr="not found" if argv[-1] in self.removed_volumes else "",
            )
        if argv[:2] == ["ps", "-aq"]:
            name = argv[-1].removeprefix("name=")
            return _completed(
                argv,
                stdout="" if name in self.removed_containers else f"{name}-id\n",
            )
        if argv[:3] == ["volume", "ls", "-q"]:
            name = argv[-1].removeprefix("name=")
            return _completed(
                argv,
                stdout="" if name in self.removed_volumes else f"{name}\n",
            )
        raise AssertionError(f"unexpected Docker command: {argv}")


class UncertainCleanupRunner(ScriptedDockerRunner):
    """Return Docker-control uncertainty after resources were asked to be removed."""

    def __init__(self, *, uncertain_inspections: int) -> None:
        super().__init__()
        self.uncertain_inspections = uncertain_inspections

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        removed = (
            argv[:2] == ["container", "inspect"] and argv[-1] in self.removed_containers
        ) or (argv[:2] == ["volume", "inspect"] and argv[-1] in self.removed_volumes)
        if removed and self.uncertain_inspections:
            self.commands.append(argv)
            self.uncertain_inspections -= 1
            return _completed(argv, returncode=124, stderr="Docker control command timed out")
        return super().run(
            argv,
            timeout_seconds=timeout_seconds,
            input_bytes=input_bytes,
        )


class DelayedListingCleanupRunner(ScriptedDockerRunner):
    """Keep removed resources visible in Docker listings for a bounded interval."""

    def __init__(self, *, lingering_listings: int) -> None:
        super().__init__()
        self.lingering_listings = lingering_listings

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        listing = argv[:2] == ["ps", "-aq"] or argv[:3] == ["volume", "ls", "-q"]
        if listing and self.lingering_listings:
            self.commands.append(argv)
            self.lingering_listings -= 1
            name = argv[-1].removeprefix("name=")
            return _completed(argv, stdout=f"{name}-visible\n")
        return super().run(
            argv,
            timeout_seconds=timeout_seconds,
            input_bytes=input_bytes,
        )


class InvalidWaitRunner(ScriptedDockerRunner):
    """Return one invalid Docker wait response while retaining cleanup behavior."""

    def __init__(self, *, returncode: int, stdout: str = "", stderr: str = "") -> None:
        super().__init__()
        self.wait_result = _completed(
            ["wait"],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if argv[0] == "wait":
            self.commands.append(argv)
            return self.wait_result
        return super().run(
            argv,
            timeout_seconds=timeout_seconds,
            input_bytes=input_bytes,
        )


def _request(tmp_path) -> IsolatedExecutionRequestV1:
    (tmp_path / "input.txt").write_text("immutable input\n", encoding="utf-8")
    return IsolatedExecutionRequestV1(
        org_repo="acme/widget",
        source_revision="abc1234",
        source_root=tmp_path,
        argv=["/bin/echo", "ok"],
        policy=IsolatedExecutionPolicyV1(immutable_image=IMAGE),
    )


def test_policy_rejects_mutable_image_root_and_credential_environment(tmp_path):
    with pytest.raises(ValidationError, match="pinned"):
        IsolatedExecutionPolicyV1(immutable_image="alpine:latest")
    with pytest.raises(ValidationError, match="non-root"):
        IsolatedExecutionPolicyV1(immutable_image=IMAGE, user="0:0")
    with pytest.raises(ValidationError, match="credential-like"):
        IsolatedExecutionRequestV1(
            org_repo="acme/widget",
            source_revision="abc1234",
            source_root=tmp_path,
            argv=["/bin/true"],
            environment={"GH_TOKEN": "synthetic"},
            policy=IsolatedExecutionPolicyV1(immutable_image=IMAGE),
        )
    with pytest.raises(ValidationError, match="non-allowlisted"):
        IsolatedExecutionRequestV1(
            org_repo="acme/widget",
            source_revision="abc1234",
            source_root=tmp_path,
            argv=["/bin/true"],
            environment={"AWS_REGION": "us-east-1"},
            policy=IsolatedExecutionPolicyV1(immutable_image=IMAGE),
        )


def test_input_and_policy_provenance_is_deterministic_and_content_addressed(tmp_path):
    request = _request(tmp_path)
    first = build_isolated_input_bundle(request)
    second = build_isolated_input_bundle(request)
    assert first.input_sha256 == second.input_sha256
    assert first.policy_sha256 == second.policy_sha256
    assert first.source_archive == second.source_archive

    (tmp_path / "input.txt").write_text("changed input\n", encoding="utf-8")
    changed = build_isolated_input_bundle(request)
    assert changed.input_sha256 != first.input_sha256
    assert changed.source_archive != first.source_archive


def test_executor_uses_named_volume_hardening_and_complete_cleanup(tmp_path):
    runner = ScriptedDockerRunner()
    request = _request(tmp_path)

    result = execute_isolated(request, runner=runner)

    assert result.truth_eligible is True
    assert result.return_code == 0
    assert result.cleanup.complete is True
    assert result.input_file_count == 1
    assert result.environment_names == []
    execution_create = [
        argv
        for argv in runner.commands
        if argv[0] == "create" and "readme-agent-exec-" in argv[argv.index("--name") + 1]
    ][0]
    for expected in (
        ["--network", "none"],
        ["--label", "readme-agent=true"],
        ["--read-only"],
        ["--cap-drop", "ALL"],
        ["--security-opt", "no-new-privileges:true"],
        ["--pids-limit", "64"],
        ["--memory", "512m"],
        ["--memory-swap", "512m"],
        ["--user", "65534:65534"],
    ):
        joined = "\0".join(execution_create)
        assert "\0".join(expected) in joined
    assert str(tmp_path) not in "\0".join(execution_create)
    assert any(argv[:2] == ["cp", "-"] for argv in runner.commands)


def test_cancellation_still_removes_containers_and_volume(tmp_path):
    runner = ScriptedDockerRunner(interrupt_wait=True)

    with pytest.raises(KeyboardInterrupt):
        execute_isolated(_request(tmp_path), runner=runner)

    assert len(runner.removed_containers) == 2
    assert len(runner.removed_volumes) == 1


def test_cleanup_retries_transient_docker_inspection_uncertainty(tmp_path):
    runner = UncertainCleanupRunner(uncertain_inspections=2)

    result = execute_isolated(_request(tmp_path), runner=runner)

    assert result.truth_eligible is True
    assert result.cleanup.complete is True
    execution_removals = [
        argv
        for argv in runner.commands
        if argv[:2] == ["rm", "--force"] and "readme-agent-exec-" in argv[-1]
    ]
    assert len(execution_removals) == 3


def test_cleanup_uncertainty_cannot_establish_truth(tmp_path):
    runner = UncertainCleanupRunner(uncertain_inspections=100)

    result = execute_isolated(_request(tmp_path), runner=runner)

    assert result.truth_eligible is False
    assert result.cleanup.complete is False


def test_cleanup_waits_for_docker_listing_to_converge(tmp_path):
    runner = DelayedListingCleanupRunner(lingering_listings=2)

    result = execute_isolated(_request(tmp_path), runner=runner)

    assert result.truth_eligible is True
    assert result.cleanup.complete is True


def test_persistently_listed_resource_cannot_establish_truth(tmp_path):
    runner = DelayedListingCleanupRunner(lingering_listings=100)

    result = execute_isolated(_request(tmp_path), runner=runner)

    assert result.truth_eligible is False
    assert result.cleanup.complete is False


@pytest.mark.parametrize(
    ("runner", "message"),
    [
        (InvalidWaitRunner(returncode=1, stderr="daemon unavailable"), "docker wait failed"),
        (InvalidWaitRunner(returncode=0, stdout=""), "one exact container exit code"),
    ],
)
def test_invalid_docker_wait_response_fails_closed_after_cleanup(tmp_path, runner, message):
    with pytest.raises(IsolatedExecutionError, match=message):
        execute_isolated(_request(tmp_path), runner=runner)

    assert len(runner.removed_containers) == 2
    assert len(runner.removed_volumes) == 1
