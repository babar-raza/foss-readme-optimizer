"""Offline contracts for Java, .NET, C++, and Go isolated consumers."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from readme_agent.facts import (
    cpp_example_verifier,
    dotnet_example_verifier,
    go_example_verifier,
    java_example_verifier,
)
from readme_agent.facts.compiled_consumer import copy_snapshot
from readme_agent.facts.dotnet_legacy_reference_fallback import (
    apply_repository_assembly_reference_fallback,
)
from readme_agent.facts.dotnet_project_closure import dotnet_project_export_paths
from readme_agent.facts.dotnet_source_generator_fallback import (
    apply_checked_in_generator_fallback,
)
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.profile.schema import PackageRoot
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(root: Path) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="abc1234",
        snapshot_root=str(root.resolve()),
        inventory_sha256="a" * 64,
        captured_at="2026-07-27T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/acme/widget.git",
            git_tree_sha256="a" * 64,
        ),
    )


def _example(language: str, code: str, class_name: str = "ReadmeExample"):
    return MinimalExamplePolicy(
        language=language,
        class_name=class_name,
        code=code,
        evidence_paths=["README.md"],
        required_symbols=["repository-authored example"],
    )


def _successful_executor(calls: list[IsolatedExecutionRequestV1]):
    def execute(request: IsolatedExecutionRequestV1) -> IsolatedExecutionResultV1:
        calls.append(request)
        now = datetime.now(UTC).isoformat()
        return IsolatedExecutionResultV1(
            truth_eligible=True,
            org_repo=request.org_repo,
            source_revision=request.source_revision,
            argv=request.argv,
            environment_names=sorted(request.environment),
            input_sha256="b" * 64,
            input_file_count=8,
            policy_sha256="c" * 64,
            policy=request.policy,
            image=ContainerImageIdentityV1(
                requested_reference=request.policy.immutable_image,
                repo_digest=request.policy.immutable_image,
                image_id="sha256:" + "d" * 64,
                operating_system="linux",
                architecture="amd64",
                engine_version="test",
            ),
            container_id="fixture",
            process_inventory=["compiler"],
            return_code=0,
            stdout="",
            stderr="",
            timed_out=False,
            oom_killed=False,
            started_at=now,
            finished_at=now,
            cleanup=ContainerCleanupV1(
                execution_container_removed=True,
                seed_container_removed=True,
                workspace_volume_removed=True,
            ),
        )

    return execute


def _failed_executor(calls: list[IsolatedExecutionRequestV1]):
    success = _successful_executor(calls)

    def execute(request: IsolatedExecutionRequestV1) -> IsolatedExecutionResultV1:
        return success(request).model_copy(
            update={"return_code": 1, "stderr": "compiler rejected consumer"}
        )

    return execute


def test_java_consumer_binds_imported_source_and_network_denied(tmp_path, monkeypatch):
    (tmp_path / "src/main/java/org/acme").mkdir(parents=True)
    (tmp_path / "pom.xml").write_text(
        "<project><properties><maven.compiler.release>17</maven.compiler.release>"
        "</properties></project>",
        encoding="utf-8",
    )
    (tmp_path / "src/main/java/org/acme/Widget.java").write_text(
        "package org.acme; public class Widget { public Widget() {} }\n",
        encoding="utf-8",
    )
    calls: list[IsolatedExecutionRequestV1] = []
    monkeypatch.setattr(java_example_verifier, "verify_repository_snapshot", lambda _: None)

    result = java_example_verifier.verify(
        _snapshot(tmp_path),
        _example(
            "java",
            "import org.acme.Widget;\npublic class ReadmeExample {"
            " public static void main(String[] a) { new Widget(); } }\n",
        ),
        executor=_successful_executor(calls),
    )

    assert result.truth_eligible
    assert result.verified_public_symbols == ["org.acme.Widget"]
    assert result.compiled_consumer is not None
    assert result.compiled_consumer.source_paths == [
        "pom.xml",
        "src/main/java/org/acme/Widget.java",
    ]
    assert calls[0].policy.network_mode == "none"
    assert calls[0].policy.read_only_rootfs is True
    assert f"container_image={java_example_verifier.JAVA_21_IMAGE}" in (
        result.acquisition_dependency_pins
    )
    assert "javac -version" in calls[0].argv[-1]


def test_dotnet_consumer_binds_public_types_and_clears_package_sources(tmp_path, monkeypatch):
    project = tmp_path / "src/Widget/Widget.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net8.0</TargetFramework>"
        "</PropertyGroup></Project>",
        encoding="utf-8",
    )
    (project.parent / "Workbook.cs").write_text(
        "namespace Aspose.Cells_FOSS; public class Workbook { public Workbook() {} }\n",
        encoding="utf-8",
    )
    (project.parent / "CellsHelper.cs").write_text(
        "namespace Aspose.Cells_FOSS.Utility; public class CellsHelper {}\n",
        encoding="utf-8",
    )
    calls: list[IsolatedExecutionRequestV1] = []
    snapshot = _snapshot(tmp_path)
    acquisition = SimpleNamespace(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        snapshot_inventory_sha256=snapshot.inventory_sha256,
        selected_manifest_path="src/Widget/Widget.csproj",
        target_framework="net8.0",
        image=SimpleNamespace(requested_reference=dotnet_example_verifier.DOTNET_8_IMAGE),
        inventory_sha256="f" * 64,
        project_transformations=[],
    )
    bundle = SimpleNamespace(acquisition=acquisition)
    materialized: list[Path] = []
    monkeypatch.setattr(dotnet_example_verifier, "verify_repository_snapshot", lambda _: None)
    monkeypatch.setattr(
        dotnet_example_verifier,
        "materialize_dotnet_dependencies",
        lambda _bundle, destination, **_kwargs: materialized.append(destination),
    )

    result = dotnet_example_verifier.verify(
        snapshot,
        _example(
            "dotnet",
            "using Aspose.Cells_FOSS;\n"
            "using Aspose.Cells_FOSS.Utility;\n"
            "var book = new Workbook();\n"
            "var helper = new CellsHelper();\n",
        ),
        executor=_successful_executor(calls),
        dependency_acquirer=lambda *_args, **_kwargs: bundle,
    )

    assert result.truth_eligible
    assert result.verified_public_symbols == [
        "Aspose.Cells_FOSS.Utility.CellsHelper",
        "Aspose.Cells_FOSS.Workbook",
    ]
    assert "-p:RestoreConfigFile=/workspace/.readme-agent/NuGet.Config" in calls[0].argv[-1]
    assert "-p:GenerateDocumentationFile=false" in calls[0].argv[-1]
    assert "dotnet --version" in calls[0].argv[-1]
    assert set(calls[0].environment) == {
        "DOTNET_CLI_HOME",
        "DOTNET_CLI_TELEMETRY_OPTOUT",
        "DOTNET_NOLOGO",
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE",
        "HOME",
        "NUGET_PACKAGES",
        "TMPDIR",
    }
    assert calls[0].policy.network_mode == "none"
    assert materialized and materialized[0].name == "nuget-packages"
    assert "nuget_inventory_sha256=" + "f" * 64 in result.acquisition_dependency_pins
    assert calls[0].environment["NUGET_PACKAGES"] == ("/workspace/.readme-agent/nuget-packages")


def test_snapshot_copy_can_exclude_dotnet_build_generated_trees(tmp_path):
    source = tmp_path / "source"
    generated = source / "Generated" / "Generator"
    generated.mkdir(parents=True)
    (generated / "Transient.cs").write_text("generated", encoding="utf-8")
    (source / "Product.cs").write_text("source", encoding="utf-8")
    destination = tmp_path / "destination"

    copy_snapshot(
        _snapshot(source),
        destination,
        ignored_names=("Generated", "generated"),
    )

    assert (destination / "Product.cs").read_text(encoding="utf-8") == "source"
    assert not (destination / "Generated").exists()


def test_snapshot_copy_exports_committed_git_bytes_and_ignores_untracked_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(
        ["git", "-C", str(source), "config", "user.email", "fixture@example.test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(source), "config", "user.name", "Fixture"],
        check=True,
    )
    (source / "Product.cs").write_text("source", encoding="utf-8")
    subprocess.run(["git", "-C", str(source), "add", "Product.cs"], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "-qm", "fixture"], check=True)
    revision = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (source / "untracked.txt").write_text("not immutable", encoding="utf-8")
    snapshot = _snapshot(source).model_copy(update={"source_revision": revision})
    destination = tmp_path / "destination"

    copy_snapshot(snapshot, destination)

    assert (destination / "Product.cs").read_text(encoding="utf-8") == "source"
    assert not (destination / "untracked.txt").exists()


def test_targeted_snapshot_export_preserves_product_source_named_artifacts(tmp_path):
    source = tmp_path / "source"
    artifact_source = source / "src" / "Artifacts" / "ArtifactCollection.cs"
    artifact_source.parent.mkdir(parents=True)
    artifact_source.write_text("public class ArtifactCollection {}", encoding="utf-8")
    destination = tmp_path / "destination"

    copy_snapshot(_snapshot(source), destination, included_paths=("src",))

    assert (destination / "src" / "Artifacts" / "ArtifactCollection.cs").is_file()


def test_dotnet_project_export_closure_includes_references_and_root_build_files(tmp_path):
    product = tmp_path / "Product" / "Product.csproj"
    foundation = tmp_path / "Foundation" / "Foundation.csproj"
    legacy_assembly = tmp_path / "packages" / "Legacy" / "lib" / "Legacy.dll"
    product.parent.mkdir()
    foundation.parent.mkdir()
    legacy_assembly.parent.mkdir(parents=True)
    legacy_assembly.write_bytes(b"fixture assembly")
    product.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
        '<ProjectReference Include="..\\Foundation\\Foundation.csproj" />'
        '<Reference Include="..\\packages\\Legacy\\lib\\Legacy.dll" />'
        "</ItemGroup></Project>",
        encoding="utf-8",
    )
    foundation.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    (tmp_path / "Directory.Build.props").write_text("<Project />", encoding="utf-8")

    assert dotnet_project_export_paths(tmp_path, product) == (
        "Directory.Build.props",
        "Foundation",
        "packages/Legacy/lib/Legacy.dll",
        "Product",
    )


def test_dotnet_project_export_closure_rejects_dynamic_references(tmp_path):
    product = tmp_path / "Product.csproj"
    product.write_text(
        '<Project><ItemGroup><ProjectReference Include="$(Shared)/Shared.csproj" />'
        "</ItemGroup></Project>",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="literal repository path"):
        dotnet_project_export_paths(tmp_path, product)


def test_dotnet_legacy_repository_assembly_reference_is_normalized(tmp_path):
    project = tmp_path / "Product" / "Product.csproj"
    assembly = tmp_path / "packages" / "Legacy" / "lib" / "Legacy.dll"
    project.parent.mkdir()
    assembly.parent.mkdir(parents=True)
    assembly.write_bytes(b"fixture assembly")
    project.write_text(
        '<Project><ItemGroup><Reference Include="..\\packages\\Legacy\\lib\\Legacy.dll" />'
        "</ItemGroup></Project>",
        encoding="utf-8",
    )

    transformations = apply_repository_assembly_reference_fallback(tmp_path)

    assert transformations == ("Product/Product.csproj:repository-assembly-reference-hint-paths=1",)
    root = ElementTree.parse(project).getroot()
    reference = next(item for item in root.iter() if item.tag == "Reference")
    assert reference.attrib["Include"] == "Legacy"
    assert next(item for item in reference if item.tag == "HintPath").text == (
        "..\\packages\\Legacy\\lib\\Legacy.dll"
    )


def test_dotnet_generator_fallback_requires_private_reference_and_checked_in_output(tmp_path):
    project = tmp_path / "Product" / "Product.csproj"
    generated = project.parent / "Generated"
    generated.mkdir(parents=True)
    (generated / "EnumExtensions.cs").write_text(
        "namespace Aspose.Widget; public static class EnumExtensions {}",
        encoding="utf-8",
    )
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><ItemGroup>'
        '<PackageReference Include="Aspose.EnumExtensionsGenerator" Version="1.0.2" '
        'PrivateAssets="all" ExcludeAssets="runtime" />'
        "</ItemGroup></Project>",
        encoding="utf-8",
    )

    transformations = apply_checked_in_generator_fallback(tmp_path)
    normalized = project.read_text(encoding="utf-8")

    assert transformations == (
        "Product/Product.csproj:Aspose.EnumExtensionsGenerator->checked-in-generated-source",
    )
    assert "Aspose.EnumExtensionsGenerator" not in normalized
    assert "<IncludeGenerated>true</IncludeGenerated>" in normalized


def test_cpp_consumer_binds_public_headers_and_namespace(tmp_path, monkeypatch):
    package = tmp_path / "Widget"
    (package / "include/acme").mkdir(parents=True)
    (package / "src").mkdir()
    (package / "CMakeLists.txt").write_text("project(widget)\n", encoding="utf-8")
    (package / "include/acme/Widget.h").write_text(
        "namespace acme { class Widget {}; }\n",
        encoding="utf-8",
    )
    (package / "src/Widget.cpp").write_text('#include "acme/Widget.h"\n', encoding="utf-8")
    calls: list[IsolatedExecutionRequestV1] = []
    monkeypatch.setattr(cpp_example_verifier, "verify_repository_snapshot", lambda _: None)

    result = cpp_example_verifier.verify(
        _snapshot(tmp_path),
        _example(
            "cpp",
            '#include "acme/Widget.h"\nusing namespace acme;\n'
            "int main() { Widget widget; return 0; }\n",
        ),
        executor=_successful_executor(calls),
    )

    assert result.truth_eligible
    assert result.verified_public_symbols == ["acme", "acme/Widget.h"]
    assert calls[0].policy.cap_drop_all is True
    assert calls[0].policy.network_mode == "none"
    assert "g++ --version" in calls[0].argv[-1]


def test_go_consumer_binds_exported_module_symbols(tmp_path, monkeypatch):
    (tmp_path / "go.mod").write_text(
        "module example.test/acme/widget\n\ngo 1.24\n",
        encoding="utf-8",
    )
    (tmp_path / "widget.go").write_text(
        "package widget\n\ntype Document struct{}\n"
        "func Open(name string) (*Document, error) { return &Document{}, nil }\n"
        "func (d *Document) Save(name string) error { return nil }\n",
        encoding="utf-8",
    )
    calls: list[IsolatedExecutionRequestV1] = []
    monkeypatch.setattr(go_example_verifier, "verify_repository_snapshot", lambda _: None)

    result = go_example_verifier.verify(
        _snapshot(tmp_path),
        _example(
            "go",
            'package main\nimport pdf "example.test/acme/widget"\n'
            'func main() { doc, _ := pdf.Open("input.pdf"); _ = doc.Save("output.pdf") }\n',
        ),
        executor=_successful_executor(calls),
    )

    assert result.truth_eligible
    assert result.verified_public_symbols == ["example.test/acme/widget.Open"]
    assert calls[0].environment == {
        "GOCACHE": "/tmp/go-build",
        "GOMODCACHE": "/tmp/go-mod",
        "GOPATH": "/tmp/go",
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
    }
    assert calls[0].policy.network_mode == "none"
    assert "go version" in calls[0].argv[-1]


@pytest.mark.parametrize(
    ("verifier", "language", "code", "message"),
    [
        (
            java_example_verifier,
            "java",
            "public class ReadmeExample {}",
            "imports no concrete",
        ),
        (
            dotnet_example_verifier,
            "dotnet",
            "var value = 1;",
            "namespace and public source type",
        ),
        (
            cpp_example_verifier,
            "cpp",
            "int main() { return 0; }",
            "public header",
        ),
        (
            go_example_verifier,
            "go",
            "package main\nfunc main() {}",
            "does not import",
        ),
    ],
)
def test_unbound_text_cannot_become_public_example(
    tmp_path, monkeypatch, verifier, language, code, message
):
    monkeypatch.setattr(verifier, "verify_repository_snapshot", lambda _: None)
    if language == "dotnet":
        project = tmp_path / "src/Widget/Widget.csproj"
        project.parent.mkdir(parents=True)
        project.write_text("<Project />", encoding="utf-8")
        (project.parent / "Workbook.cs").write_text("public class Workbook {}\n", encoding="utf-8")
    elif language == "cpp":
        package = tmp_path / "Widget"
        (package / "include").mkdir(parents=True)
        (package / "src").mkdir()
        (package / "CMakeLists.txt").write_text("project(widget)\n", encoding="utf-8")
    elif language == "go":
        (tmp_path / "go.mod").write_text("module example.test/widget\n", encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        verifier.verify(
            _snapshot(tmp_path),
            _example(language, code),
            executor=_successful_executor([]),
        )


def test_compiler_rejection_cannot_become_verified_example(tmp_path, monkeypatch):
    (tmp_path / "src/main/java/org/acme").mkdir(parents=True)
    (tmp_path / "pom.xml").write_text("<project />\n", encoding="utf-8")
    (tmp_path / "src/main/java/org/acme/Widget.java").write_text(
        "package org.acme; public class Widget {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(java_example_verifier, "verify_repository_snapshot", lambda _: None)

    result = java_example_verifier.verify(
        _snapshot(tmp_path),
        _example(
            "java",
            "import org.acme.Widget;\npublic class ReadmeExample {"
            " public static void main(String[] a) { new Missing(); } }\n",
        ),
        executor=_failed_executor([]),
    )

    assert result.outcome == "BUILD_FAILED"
    assert result.truth_eligible is False
    assert result.verified_public_symbols == []
    assert result.compiled_consumer is not None
    assert result.compiled_consumer.accepted is False


def test_dotnet_project_selection_prefers_main_library(tmp_path):
    converter = tmp_path / "src/converter/Converter.csproj"
    library = tmp_path / "src/main/Widget/Widget.csproj"
    converter.parent.mkdir(parents=True)
    library.parent.mkdir(parents=True)
    converter.write_text("<Project />\n", encoding="utf-8")
    library.write_text("<Project />\n", encoding="utf-8")

    assert dotnet_example_verifier._project(_snapshot(tmp_path)) == library


def test_dotnet_project_selection_accepts_root_role_manifest_with_windows_separators(tmp_path):
    foundation = tmp_path / "Aspose.Foundation/Aspose.Foundation/Aspose.Foundation.csproj"
    words = tmp_path / "Aspose.Words/Aspose.Words.csproj"
    foundation.parent.mkdir(parents=True)
    words.parent.mkdir(parents=True)
    foundation.write_text("<Project />\n", encoding="utf-8")
    words.write_text("<Project />\n", encoding="utf-8")
    snapshot = _snapshot(tmp_path).model_copy(
        update={
            "package_roots": (
                PackageRoot(
                    path=r"Aspose.Foundation\Aspose.Foundation",
                    ecosystem="net",
                    manifest_path=(r"Aspose.Foundation\Aspose.Foundation\Aspose.Foundation.csproj"),
                    confidence=1.0,
                    evidence="fixture",
                ),
                PackageRoot(
                    path="Aspose.Words",
                    ecosystem="net",
                    manifest_path=r"Aspose.Words\Aspose.Words.csproj",
                    confidence=1.0,
                    evidence="fixture",
                ),
            )
        }
    )

    assert (
        dotnet_example_verifier._project(
            snapshot,
            "Aspose.Words/Aspose.Words.csproj",
        )
        == words
    )


def test_dotnet_consumer_selects_pinned_net9_image_and_target(tmp_path, monkeypatch):
    project = tmp_path / "Aspose.Words/Aspose.Words.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFramework>net9.0</TargetFramework>"
        "</PropertyGroup></Project>",
        encoding="utf-8",
    )
    (project.parent / "Document.cs").write_text(
        "namespace Aspose.Words; public class Document { public Document() {} }\n",
        encoding="utf-8",
    )
    snapshot = _snapshot(tmp_path).model_copy(
        update={
            "package_roots": (
                PackageRoot(
                    path="Aspose.Words",
                    ecosystem="net",
                    manifest_path="Aspose.Words/Aspose.Words.csproj",
                    confidence=1.0,
                    evidence="fixture",
                ),
            )
        }
    )
    calls: list[IsolatedExecutionRequestV1] = []
    monkeypatch.setattr(dotnet_example_verifier, "verify_repository_snapshot", lambda _: None)

    result = dotnet_example_verifier.verify(
        snapshot,
        _example(
            "dotnet",
            "using Aspose.Words;\nvar document = new Document();\n",
        ),
        executor=_successful_executor(calls),
        selected_product_manifest_path="Aspose.Words/Aspose.Words.csproj",
        dependency_acquirer=lambda *_args, **_kwargs: None,
    )

    assert result.truth_eligible
    assert calls[0].policy.immutable_image == dotnet_example_verifier.DOTNET_9_IMAGE
    assert "-p:TargetFramework=net9.0" in calls[0].argv[-1]
    assert "-p:TargetFrameworks=net9.0" in calls[0].argv[-1]
    assert "dotnet_sdk=9.0.316" in result.acquisition_dependency_pins
    assert "dotnet_target_framework=net9.0" in result.acquisition_dependency_pins


def test_dotnet_consumer_selects_pinned_net10_image_and_target(tmp_path, monkeypatch):
    project = tmp_path / "src/Product.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        "<TargetFrameworks>net10.0;net8.0</TargetFrameworks>"
        "</PropertyGroup><PropertyGroup Condition=\"'$(Configuration)' == 'Debug'\">"
        "<TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    (project.parent / "Scene.cs").write_text(
        "namespace Aspose.ThreeD; public class Scene { public void Save(string path) {} }",
        encoding="utf-8",
    )
    snapshot = _snapshot(tmp_path).model_copy(
        update={
            "package_roots": (
                PackageRoot(
                    path="src",
                    ecosystem="net",
                    manifest_path="src/Product.csproj",
                    confidence=1.0,
                    evidence="fixture",
                ),
            )
        }
    )
    calls: list[IsolatedExecutionRequestV1] = []
    monkeypatch.setattr(dotnet_example_verifier, "verify_repository_snapshot", lambda _: None)
    result = dotnet_example_verifier.verify(
        snapshot,
        _example(
            "dotnet",
            'using Aspose.ThreeD; var scene = new Scene(); scene.Save("out");',
        ),
        executor=_successful_executor(calls),
        selected_product_manifest_path="src/Product.csproj",
        dependency_acquirer=lambda *_args, **_kwargs: None,
    )

    assert result.truth_eligible
    assert calls[0].policy.immutable_image == dotnet_example_verifier.DOTNET_10_IMAGE
    assert "-p:TargetFramework=net10.0" in calls[0].argv[-1]
    assert "dotnet_sdk=10.0.302" in result.acquisition_dependency_pins
    assert "dotnet_target_framework=net10.0" in result.acquisition_dependency_pins
    assert "-p:RestoreConfigFile=/workspace/.readme-agent/NuGet.Config" in calls[0].argv[-1]
    assert calls[0].policy.network_mode == "none"


def test_dotnet_consumer_rejects_unbound_selected_project_and_net8_for_net9_only(tmp_path):
    project = tmp_path / "Aspose.Words/Aspose.Words.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        "<Project><PropertyGroup><TargetFramework>net9.0</TargetFramework>"
        "</PropertyGroup></Project>",
        encoding="utf-8",
    )
    snapshot = _snapshot(tmp_path).model_copy(
        update={
            "package_roots": (
                PackageRoot(
                    path="Aspose.Words",
                    ecosystem="net",
                    manifest_path="Aspose.Words/Aspose.Words.csproj",
                    confidence=1.0,
                    evidence="fixture",
                ),
            )
        }
    )

    with pytest.raises(ValueError, match="not bound"):
        dotnet_example_verifier._project(snapshot, "Other/Other.csproj")
    with pytest.raises(ValueError, match="cannot reference a net9-only"):
        dotnet_example_verifier._target_framework(project, "net8.0")


def test_java_class_name_cannot_escape_control_directory(tmp_path, monkeypatch):
    (tmp_path / "src/main/java/org/acme").mkdir(parents=True)
    (tmp_path / "pom.xml").write_text("<project />\n", encoding="utf-8")
    (tmp_path / "src/main/java/org/acme/Widget.java").write_text(
        "package org.acme; public class Widget {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(java_example_verifier, "verify_repository_snapshot", lambda _: None)

    with pytest.raises(ValueError, match="valid identifier"):
        java_example_verifier.verify(
            _snapshot(tmp_path),
            _example(
                "java",
                "import org.acme.Widget;\npublic class ReadmeExample {}\n",
                class_name="../escape",
            ),
            executor=_successful_executor([]),
        )
