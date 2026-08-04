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
from readme_agent.facts.dotnet_dependency_acquisition import (
    DotnetDependencyBundle,
    acquire_dotnet_dependencies,
    materialize_dotnet_dependencies,
)
from readme_agent.facts.dotnet_legacy_reference_fallback import (
    apply_repository_assembly_reference_fallback,
)
from readme_agent.facts.dotnet_project_closure import dotnet_project_export_paths
from readme_agent.facts.dotnet_source_generator_fallback import (
    apply_checked_in_generator_fallback,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.root_role_schema import (
    filesystem_repository_path,
    portable_repository_path,
)
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

DOTNET_8_IMAGE = (
    "mcr.microsoft.com/dotnet/sdk@sha256:"
    "3c0edbfe1549dd93fb789dc96299a40df865ad7bffefcaf38e8c05940686d641"
)
DOTNET_9_IMAGE = (
    "mcr.microsoft.com/dotnet/sdk@sha256:"
    "cb9d975bf57fd1b0915858d1db1184bea20f7f746f0536323fcab49673144e8c"
)
IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]
DependencyAcquirer = Callable[..., DotnetDependencyBundle | None]
_SUPPORTED_TARGETS = {
    "net8.0": (DOTNET_8_IMAGE, "8.0.423"),
    "net9.0": (DOTNET_9_IMAGE, "9.0.316"),
}


def _project(
    snapshot: RepositorySnapshotV1,
    selected_product_manifest_path: str | None = None,
) -> Path:
    package_projects = {
        portable_repository_path(root.manifest_path): (
            snapshot.root_path / filesystem_repository_path(root.manifest_path)
        )
        for root in snapshot.package_roots
        if root.ecosystem in {"dotnet", "net"}
    }
    if selected_product_manifest_path is not None:
        selected = portable_repository_path(selected_product_manifest_path)
        project = package_projects.get(selected)
        if project is None:
            raise ValueError(
                "selected .NET product project is not bound to the repository snapshot"
            )
        if not project.is_file() or project.suffix.casefold() != ".csproj":
            raise ValueError("selected .NET product project is unavailable or not a .csproj")
        return project
    candidates = [
        path
        for path in package_projects.values()
        if path.is_file()
        and not {"test", "tests", "sample", "samples"} & {part.casefold() for part in path.parts}
    ]
    if not candidates:
        candidates = [
            *snapshot.root_path.glob("*.csproj"),
            *snapshot.root_path.glob("src/**/*.csproj"),
        ]
    if not candidates:
        raise ValueError(".NET repository has no production project bound to the snapshot")
    return min(
        candidates,
        key=lambda path: (
            "main" not in {part.lower() for part in path.parts},
            "converter" in {part.lower() for part in path.parts},
            len(path.parts),
            path.as_posix(),
        ),
    )


def _target_framework(project: Path, requested: str | None = None) -> str:
    text = project.read_text(encoding="utf-8-sig", errors="replace")
    declared = [
        value.strip().casefold()
        for group in re.findall(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>", text)
        for value in group.split(";")
        if value.strip()
    ]
    if requested is not None:
        target = requested.strip().casefold()
        if target not in _SUPPORTED_TARGETS:
            raise ValueError(".NET consumer target must be pinned to net8.0 or net9.0")
        if target == "net8.0" and declared and all(value.startswith("net9") for value in declared):
            raise ValueError("net8.0 consumer cannot reference a net9-only product project")
        return target
    if "net8.0" in declared:
        return "net8.0"
    if "net9.0" in declared:
        return "net9.0"
    if not declared or all(
        value.startswith("netstandard")
        or re.fullmatch(r"net(?:coreapp)?[1-8](?:\.\d+)?", value) is not None
        for value in declared
    ):
        return "net8.0"
    raise ValueError(".NET project has no supported net8.0/net9.0 consumer target")


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
    immutable_image: str | None = None,
    selected_product_manifest_path: str | None = None,
    target_framework: str | None = None,
    dependency_acquirer: DependencyAcquirer | None = None,
) -> LocalProductVerificationV1:
    """Restore from no package sources and compile an exact pinned .NET consumer."""

    verify_repository_snapshot(snapshot)
    project = _project(snapshot, selected_product_manifest_path)
    selected_target = _target_framework(project, target_framework)
    selected_image, sdk_version = _SUPPORTED_TARGETS[selected_target]
    image = immutable_image or selected_image
    source_paths, symbols = _selected_sources(snapshot, project, example.code)
    project_relative = project.relative_to(snapshot.root_path).as_posix()
    bundle = (dependency_acquirer or acquire_dotnet_dependencies)(
        snapshot,
        project_relative,
        immutable_image=image,
        target_framework=selected_target,
    )
    if bundle is not None:
        receipt = bundle.acquisition
        if (
            receipt.org_repo != snapshot.org_repo
            or receipt.source_revision != snapshot.source_revision
            or receipt.snapshot_inventory_sha256 != snapshot.inventory_sha256
            or receipt.selected_manifest_path != project_relative
            or receipt.target_framework != selected_target
            or receipt.image.requested_reference != image
        ):
            raise ValueError("NuGet dependency acquisition does not match the immutable source")
    with tempfile.TemporaryDirectory(prefix="readme-agent-dotnet-consumer-") as temp:
        workspace = Path(temp) / "workspace"
        copy_snapshot(
            snapshot,
            workspace,
            included_paths=dotnet_project_export_paths(snapshot.root_path, project),
        )
        consumer_dir = workspace / ".readme-agent"
        consumer_dir.mkdir()
        if bundle is not None:
            materialize_dotnet_dependencies(
                bundle,
                consumer_dir / "nuget-packages",
                repository_destination=workspace,
            )
        transformations = (
            *apply_checked_in_generator_fallback(workspace),
            *apply_repository_assembly_reference_fallback(workspace),
        )
        if (
            bundle is not None
            and tuple(bundle.acquisition.project_transformations) != transformations
        ):
            raise ValueError("NuGet acquisition and offline project transformations differ")
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
            f"    <TargetFramework>{selected_target}</TargetFramework>\n"
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
            f"dotnet build {project_argument} --nologo --configuration Debug "
            f"-p:TargetFramework={selected_target} "
            f"-p:TargetFrameworks={selected_target} "
            "-p:GenerateDocumentationFile=false "
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
                    "NUGET_PACKAGES": "/workspace/.readme-agent/nuget-packages",
                    "TMPDIR": "/tmp",
                },
                policy=IsolatedExecutionPolicyV1(
                    immutable_image=image,
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
            f"dotnet_sdk={sdk_version}",
            f"dotnet_target_framework={selected_target}",
            *(
                [
                    f"nuget_inventory_sha256={bundle.acquisition.inventory_sha256}",
                    *(
                        "dotnet_project_transformation=" + item
                        for item in bundle.acquisition.project_transformations
                    ),
                ]
                if bundle is not None
                else []
            ),
        ),
        compiled_consumer=proof,
    )
