"""Compile exact .NET consumers against immutable repository source in Docker."""

from __future__ import annotations

import re
import shlex
import tempfile
from collections.abc import Callable
from pathlib import Path
from xml.sax.saxutils import escape

from readme_agent.ecosystems.dotnet_public_types import public_dotnet_type_index
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

DOTNET_8_IMAGE = (
    "mcr.microsoft.com/dotnet/sdk@sha256:"
    "3c0edbfe1549dd93fb789dc96299a40df865ad7bffefcaf38e8c05940686d641"
)
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]


def _project(snapshot: RepositorySnapshotV1) -> Path:
    candidates = [
        path
        for path in snapshot.root_path.glob("src/**/*.csproj")
        if not {"test", "tests", "sample", "samples"} & {part.lower() for part in path.parts}
    ]
    if not candidates:
        raise ValueError(".NET repository has no production project under src/")
    return min(
        candidates,
        key=lambda path: (
            "main" not in {part.lower() for part in path.parts},
            "converter" in {part.lower() for part in path.parts},
            len(path.parts),
            path.as_posix(),
        ),
    )


def _selected_sources(
    snapshot: RepositorySnapshotV1,
    project: Path,
    code: str,
) -> tuple[list[str], list[str]]:
    namespaces = sorted(set(re.findall(r"(?m)^\s*using\s+(Aspose(?:\.[A-Za-z_]\w*)+)\s*;", code)))
    type_index = public_dotnet_type_index(project.parent)
    used_types = sorted(name for name in type_index if re.search(rf"\b{re.escape(name)}\b", code))
    if not namespaces or not used_types:
        raise ValueError(".NET example must use a repository namespace and public source type")
    paths = [project.relative_to(snapshot.root_path).as_posix()]
    paths.extend(
        type_index[name].source_path.relative_to(snapshot.root_path).as_posix()
        for name in used_types
    )
    symbols = [type_index[name].qualified_name for name in used_types]
    return sorted(set(paths)), sorted(set(symbols))


def verify(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    *,
    executor: IsolatedExecutor = execute_isolated,
    immutable_image: str = DOTNET_8_IMAGE,
) -> LocalProductVerificationV1:
    """Restore from no package sources and compile an exact .NET 8 consumer."""

    verify_repository_snapshot(snapshot)
    project = _project(snapshot)
    source_paths, symbols = _selected_sources(snapshot, project, example.code)
    project_relative = project.relative_to(snapshot.root_path).as_posix()
    with tempfile.TemporaryDirectory(prefix="readme-agent-dotnet-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        copy_snapshot(snapshot, workspace)
        consumer_dir = workspace / ".readme-agent"
        consumer_dir.mkdir()
        (consumer_dir / "Program.cs").write_text(example.code, encoding="utf-8", newline="\n")
        (consumer_dir / "NuGet.Config").write_text(
            "<configuration><packageSources><clear /></packageSources></configuration>\n",
            encoding="utf-8",
            newline="\n",
        )
        (consumer_dir / "ReadmeAgentExample.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            "  <PropertyGroup>\n"
            "    <OutputType>Exe</OutputType>\n"
            "    <TargetFramework>net8.0</TargetFramework>\n"
            "    <ImplicitUsings>enable</ImplicitUsings>\n"
            "    <Nullable>enable</Nullable>\n"
            "  </PropertyGroup>\n"
            f'  <ItemGroup><ProjectReference Include="../{escape(project_relative)}" />'
            "</ItemGroup>\n"
            "</Project>\n",
            encoding="utf-8",
            newline="\n",
        )
        project_argument = shlex.quote(".readme-agent/ReadmeAgentExample.csproj")
        command = (
            "dotnet --version; "
            f"dotnet build {project_argument} --nologo --configuration Release "
            "-p:TargetFramework=net8.0 "
            "-p:TargetFrameworks=net8.0 "
            "-p:RestoreConfigFile=/workspace/.readme-agent/NuGet.Config"
        )
        execution = executor(
            IsolatedExecutionRequestV1(
                org_repo=snapshot.org_repo,
                source_revision=snapshot.source_revision,
                source_root=workspace,
                argv=["/bin/sh", "-euc", command],
                environment={
                    "DOTNET_CLI_HOME": "/tmp/dotnet",
                    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                    "DOTNET_NOLOGO": "1",
                    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
                    "HOME": "/tmp",
                    "NUGET_PACKAGES": "/tmp/nuget",
                    "TMPDIR": "/tmp",
                },
                policy=IsolatedExecutionPolicyV1(
                    immutable_image=immutable_image,
                    timeout_seconds=300,
                    memory_mebibytes=1536,
                    pids_limit=128,
                ),
            )
        )
    verify_repository_snapshot(snapshot)
    proof = compiled_proof(
        snapshot=snapshot,
        ecosystem="dotnet",
        source_paths=source_paths,
        selected_symbols=symbols,
        example_code=example.code,
        execution=execution,
    )
    result = diagnostic(execution)
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="dotnet",
        outcome="SOURCE_BUILD_VERIFIED" if proof.accepted else "BUILD_FAILED",
        detail=(
            "exact .NET consumer compiled against immutable repository source"
            if proof.accepted
            else "isolated .NET source or exact consumer compilation failed"
        ),
        build=result,
        example_compile=result,
        isolated_execution=execution,
        truth_eligible=proof.accepted,
        verified_public_symbols=proof.selected_symbols if proof.accepted else [],
        public_api_sha256=proof.source_sha256,
        acquisition_dependency_pins=dependency_pins(
            proof,
            "dotnet_sdk=8.0.423",
            "dotnet_target_framework=net8.0",
        ),
        compiled_consumer=proof,
    )
