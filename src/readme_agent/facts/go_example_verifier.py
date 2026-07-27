"""Compile exact Go consumers against immutable repository source in Docker."""

from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from readme_agent.facts.compiled_consumer import (
    compiled_proof,
    copy_snapshot,
    dependency_pins,
    diagnostic,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

GO_124_IMAGE = "golang@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac"
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]


def _module_path(root: Path) -> str:
    text = (root / "go.mod").read_text(encoding="utf-8")
    match = re.search(r"(?m)^module\s+(\S+)", text)
    if match is None:
        raise ValueError("Go repository has no module path")
    return match.group(1)


def _selected_sources(
    snapshot: RepositorySnapshotV1,
    code: str,
) -> tuple[list[str], list[str]]:
    module = _module_path(snapshot.root_path)
    imports = re.findall(
        rf'(?m)^\s*(?:import\s+)?(\w+)?\s*"{re.escape(module)}"\s*$',
        code,
    )
    if not imports:
        raise ValueError("Go example does not import the immutable repository module")
    alias = next((item for item in imports if item), Path(module).name.replace("-", "_"))
    names = sorted(set(re.findall(rf"\b{re.escape(alias)}\.([A-Z]\w*)", code)))
    if not names:
        raise ValueError("Go example uses no exported repository symbol")
    paths = ["go.mod"]
    for path in sorted(snapshot.root_path.glob("*.go")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(
            re.search(
                rf"(?m)^(?:func\s+(?:\([^)]*\)\s*)?|type\s+|var\s+|const\s+)"
                rf"{re.escape(name)}\b",
                text,
            )
            for name in names
        ):
            paths.append(path.relative_to(snapshot.root_path).as_posix())
    if len(paths) == 1:
        raise ValueError("Go exported symbols do not resolve to repository source")
    return sorted(set(paths)), [f"{module}.{name}" for name in names]


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    *,
    executor: IsolatedExecutor = execute_isolated,
    immutable_image: str = GO_124_IMAGE,
) -> LocalProductVerificationV1:
    """Build the source module and exact external-style consumer with no network."""

    verify_repository_snapshot(snapshot)
    source_paths, symbols = _selected_sources(snapshot, example.code)
    with tempfile.TemporaryDirectory(prefix="readme-agent-go-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        copy_snapshot(snapshot, workspace)
        consumer_dir = workspace / ".readme-agent"
        consumer_dir.mkdir()
        (consumer_dir / "main.go").write_text(example.code, encoding="utf-8", newline="\n")
        execution = executor(
            IsolatedExecutionRequestV1(
                org_repo=snapshot.org_repo,
                source_revision=snapshot.source_revision,
                source_root=workspace,
                argv=[
                    "/bin/sh",
                    "-euc",
                    "go version; go build -p=1 ./...; "
                    "go build -p=1 -o /tmp/readme-example ./.readme-agent",
                ],
                environment={
                    "GOCACHE": "/tmp/go-build",
                    "GOMODCACHE": "/tmp/go-mod",
                    "GOPATH": "/tmp/go",
                    "HOME": "/tmp",
                    "TMPDIR": "/tmp",
                },
                policy=IsolatedExecutionPolicyV1(
                    immutable_image=immutable_image,
                    timeout_seconds=300,
                    memory_mebibytes=1536,
                    pids_limit=128,
                    tmpfs_mebibytes=1024,
                ),
            )
        )
    verify_repository_snapshot(snapshot)
    proof = compiled_proof(
        snapshot=snapshot,
        ecosystem="go",
        source_paths=source_paths,
        selected_symbols=symbols,
        example_code=example.code,
        execution=execution,
    )
    result = diagnostic(execution)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="go",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "exact Go consumer compiled against immutable repository source"
            if proof.accepted
            else "isolated Go source or exact consumer compilation failed"
        ),
        build=result,
        example_compile=result,
        isolated_execution=execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.selected_symbols if proof.accepted else [],
        public_api_sha256=proof.source_sha256,
        acquisition_dependency_pins=dependency_pins(proof, "go_module_dependencies=none"),
        compiled_consumer=proof,
    )
