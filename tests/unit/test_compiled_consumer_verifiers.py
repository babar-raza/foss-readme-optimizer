"""Offline contracts for Java, .NET, C++, and Go isolated consumers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from readme_agent.facts import (
    cpp_example_verifier,
    dotnet_example_verifier,
    go_example_verifier,
    java_example_verifier,
)
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
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
    monkeypatch.setattr(dotnet_example_verifier, "verify_repository_snapshot", lambda _: None)

    result = dotnet_example_verifier.verify(
        _snapshot(tmp_path),
        _example(
            "dotnet",
            "using Aspose.Cells_FOSS;\n"
            "using Aspose.Cells_FOSS.Utility;\n"
            "var book = new Workbook();\n"
            "var helper = new CellsHelper();\n",
        ),
        executor=_successful_executor(calls),
    )

    assert result.truth_eligible
    assert result.verified_public_symbols == [
        "Aspose.Cells_FOSS.Utility.CellsHelper",
        "Aspose.Cells_FOSS.Workbook",
    ]
    assert "-p:RestoreConfigFile=/workspace/.readme-agent/NuGet.Config" in calls[0].argv[-1]
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
