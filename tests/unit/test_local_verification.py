"""RPOC-035: `_verify_dotnet`/`_verify_python`/`_verify_typescript`/`_verify_go`
-- each follows `_verify_java`'s exact two-phase shape and outcome vocabulary
(`SOURCE_BUILD_VERIFIED`/`BLOCKED_TOOLCHAIN`/`BUILD_FAILED`), and their
registration in `_VERIFIERS`.

Every test here is offline/mocked (`execute_example`/`shutil.which` are
monkeypatched) EXCEPT the `@pytest.mark.live` tests at the bottom, which run
the real `python`/`go`/`dotnet` toolchains against a small, hand-written,
genuinely-correct example -- proving the real subprocess wiring works, not
just that the mocks are self-consistent. `tsc` is not installed on the
machine this was authored on, so the equivalent live TypeScript test is
`skipif`-guarded rather than faked."""

from __future__ import annotations

import shutil

import pytest

from readme_agent.facts import local_verification as lv
from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.profile.schema import PackageRoot
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(tmp_path) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="abc1234",
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="a" * 64,
        captured_at="2026-07-25T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="a" * 64,
        ),
    )


def _example(language: str, class_name: str, code: str) -> MinimalExamplePolicy:
    return MinimalExamplePolicy(
        language=language,
        class_name=class_name,
        code=code,
        evidence_paths=["README.md"],
        required_symbols=[],
    )


def _result(*, argv, return_code, stdout="", stderr="") -> ExampleExecutionResultV1:
    return ExampleExecutionResultV1(
        argv=argv,
        return_code=return_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
        environment_names=[],
    )


def _workspace(tmp_path):
    workspace = tmp_path / "repository"
    workspace.mkdir()
    return workspace


def _which_only(monkeypatch, available: dict[str, str]) -> None:
    """`shutil.which` returns a fake path for names in `available`, `None` otherwise."""

    def fake_which(executable: str) -> str | None:
        return available.get(executable)

    monkeypatch.setattr(lv.shutil, "which", fake_which)


def _scripted_execute_example(monkeypatch, results: list[ExampleExecutionResultV1]) -> list:
    calls: list = []

    def fake_execute_example(argv, *, workspace, timeout_seconds, base_environment=None):
        calls.append({"argv": argv, "workspace": workspace, "base_environment": base_environment})
        return results[len(calls) - 1]

    monkeypatch.setattr(lv, "execute_example", fake_execute_example)
    return calls


class TestVerifiersRegistration:
    def test_all_supported_languages_registered(self):
        assert set(lv._VERIFIERS) == {
            "java",
            "dotnet",
            "python",
            "typescript",
            "cpp",
            "go",
            "rust",
        }
        assert lv._VERIFIERS["dotnet"] is lv._verify_dotnet
        assert lv._VERIFIERS["python"] is lv._verify_python
        assert lv._VERIFIERS["typescript"] is lv._verify_typescript
        assert lv._VERIFIERS["go"] is lv._verify_go
        assert lv._ISOLATED_VERIFIERS["java"] is lv.java_example_verifier.verify
        assert lv._ISOLATED_VERIFIERS["dotnet"] is lv.dotnet_example_verifier.verify
        assert lv._ISOLATED_VERIFIERS["cpp"] is lv.cpp_example_verifier.verify
        assert lv._ISOLATED_VERIFIERS["go"] is lv.go_example_verifier.verify
        assert lv._ISOLATED_VERIFIERS["typescript"] is lv.typescript_example_verifier.verify
        assert lv._ISOLATED_VERIFIERS["rust"] is lv.rust_example_verifier.verify

    def test_unregistered_language_fails_closed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lv, "verify_repository_snapshot", lambda snapshot: None)
        snapshot = _snapshot(tmp_path)
        # Bypass pydantic's Literal validation to prove the host diagnostic
        # itself still fails closed for anything `_VERIFIERS` doesn't recognize.
        example = _example("java", "Example", "public class Example {}")
        example.language = "ruby"  # type: ignore[assignment]
        with pytest.raises(ValueError, match="no local example verifier registered"):
            lv.run_host_product_example_diagnostic(snapshot, example)


class TestVerifyDotnetMocked:
    def test_missing_dotnet_is_blocked_toolchain(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {})
        result = lv._verify_dotnet(
            _snapshot(tmp_path), _example("dotnet", "Example", ""), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"
        assert "dotnet" in result.detail

    def test_repo_build_failure_is_build_failed(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"dotnet": "C:/dotnet.exe"})
        _scripted_execute_example(
            monkeypatch,
            [_result(argv=["dotnet"], return_code=1, stderr="CS0103: some real compile error")],
        )
        result = lv._verify_dotnet(
            _snapshot(tmp_path), _example("dotnet", "Example", "x"), _workspace(tmp_path)
        )
        assert result.outcome == "BUILD_FAILED"

    def test_repo_build_failure_with_toolchain_signal_is_blocked(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"dotnet": "C:/dotnet.exe"})
        _scripted_execute_example(
            monkeypatch,
            [_result(argv=["dotnet"], return_code=1, stderr="No .NET SDKs were found.")],
        )
        result = lv._verify_dotnet(
            _snapshot(tmp_path), _example("dotnet", "Example", "x"), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"

    def test_success_scaffolds_example_project_referencing_repo_csproj(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"dotnet": "C:/dotnet.exe"})
        workspace = _workspace(tmp_path)
        repo_csproj = workspace / "widget.csproj"
        repo_csproj.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            "<TargetFramework>net6.0</TargetFramework>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )
        calls = _scripted_execute_example(
            monkeypatch,
            [
                _result(argv=["dotnet", "build"], return_code=0),
                _result(argv=["dotnet", "build"], return_code=0),
            ],
        )
        example = _example("dotnet", "ReadmeExample", "Console.WriteLine(1);")
        result = lv._verify_dotnet(_snapshot(tmp_path), example, workspace)

        assert result.outcome == "SOURCE_BUILD_VERIFIED"
        assert len(calls) == 2
        example_dir = workspace.parent / "dotnet-example"
        csproj_text = (example_dir / "ReadmeAgentExample.csproj").read_text(encoding="utf-8")
        assert "<TargetFramework>net6.0</TargetFramework>" in csproj_text
        assert f'ProjectReference Include="{repo_csproj}"' in csproj_text
        assert (example_dir / "ReadmeExample.cs").read_text(
            encoding="utf-8"
        ) == "Console.WriteLine(1);"
        assert calls[0]["argv"] == ["C:/dotnet.exe", "build", str(repo_csproj), "--nologo"]
        assert calls[1]["workspace"] == example_dir

    def test_multi_root_build_selects_project_that_owns_example_evidence(
        self, tmp_path, monkeypatch
    ):
        _which_only(monkeypatch, {"dotnet": "C:/dotnet.exe"})
        workspace = _workspace(tmp_path)
        main_project = workspace / "src" / "main" / "Widget" / "Widget.csproj"
        converter_project = workspace / "src" / "converter" / "Converter.csproj"
        test_project = workspace / "src" / "test" / "Widget.Tests" / "Widget.Tests.csproj"
        for project in (main_project, converter_project, test_project):
            project.parent.mkdir(parents=True)
            project.write_text(
                '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
                "<TargetFramework>net8.0</TargetFramework>"
                "</PropertyGroup></Project>",
                encoding="utf-8",
            )
        snapshot = _snapshot(tmp_path).model_copy(
            update={
                "package_roots": (
                    PackageRoot(
                        path="src/converter",
                        ecosystem="net",
                        manifest_path="src/converter/Converter.csproj",
                        confidence=1.0,
                        evidence="fixture",
                    ),
                    PackageRoot(
                        path="src/main/Widget",
                        ecosystem="net",
                        manifest_path="src/main/Widget/Widget.csproj",
                        confidence=1.0,
                        evidence="fixture",
                    ),
                    PackageRoot(
                        path="src/test/Widget.Tests",
                        ecosystem="net",
                        manifest_path="src/test/Widget.Tests/Widget.Tests.csproj",
                        confidence=1.0,
                        evidence="fixture",
                    ),
                )
            }
        )
        example = MinimalExamplePolicy(
            language="dotnet",
            class_name="ReadmeExample",
            code="new Widget.Scene();",
            evidence_paths=["src/main/Widget/Scene.cs"],
        )
        calls = _scripted_execute_example(
            monkeypatch,
            [
                _result(argv=["dotnet", "build"], return_code=0),
                _result(argv=["dotnet", "build"], return_code=0),
            ],
        )

        result = lv._verify_dotnet(snapshot, example, workspace)

        assert result.outcome == "SOURCE_BUILD_VERIFIED"
        assert calls[0]["argv"] == ["C:/dotnet.exe", "build", str(main_project), "--nologo"]
        generated = workspace.parent / "dotnet-example" / "ReadmeAgentExample.csproj"
        assert f'ProjectReference Include="{main_project}"' in generated.read_text(encoding="utf-8")

    def test_example_compile_failure_is_build_failed(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"dotnet": "C:/dotnet.exe"})
        _scripted_execute_example(
            monkeypatch,
            [
                _result(argv=["dotnet", "build"], return_code=0),
                _result(argv=["dotnet", "build"], return_code=1, stderr="CS1002: ; expected"),
            ],
        )
        result = lv._verify_dotnet(
            _snapshot(tmp_path), _example("dotnet", "Example", "broken"), _workspace(tmp_path)
        )
        assert result.outcome == "BUILD_FAILED"
        assert result.example_compile is not None


class TestVerifyPythonMocked:
    def test_missing_python_is_blocked_toolchain(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {})
        result = lv._verify_python(
            _snapshot(tmp_path), _example("python", "example", ""), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"
        assert "python" in result.detail

    def test_repo_compileall_failure_is_build_failed(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"python": "C:/python.exe"})
        _scripted_execute_example(
            monkeypatch,
            [_result(argv=["python"], return_code=1, stderr="SyntaxError: invalid syntax")],
        )
        result = lv._verify_python(
            _snapshot(tmp_path), _example("python", "example", "x = 1"), _workspace(tmp_path)
        )
        assert result.outcome == "BUILD_FAILED"

    def test_success_writes_example_module(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"python": "C:/python.exe"})
        workspace = _workspace(tmp_path)
        calls = _scripted_execute_example(
            monkeypatch,
            [
                _result(argv=["python", "-m", "compileall"], return_code=0),
                _result(argv=["python", "-m", "py_compile"], return_code=0),
            ],
        )
        example = _example("python", "readme_example", "print('hi')\n")
        result = lv._verify_python(_snapshot(tmp_path), example, workspace)

        assert result.outcome == "SOURCE_BUILD_VERIFIED"
        example_dir = workspace.parent / "python-example"
        assert (example_dir / "readme_example.py").read_text(encoding="utf-8") == "print('hi')\n"
        assert calls[1]["workspace"] == example_dir


class TestVerifyTypeScriptMocked:
    def test_missing_tsc_is_blocked_toolchain(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"node": "C:/node.exe"})
        result = lv._verify_typescript(
            _snapshot(tmp_path), _example("typescript", "example", ""), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"
        assert "tsc" in result.detail

    def test_missing_node_is_blocked_toolchain(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"tsc": "C:/tsc.cmd"})
        result = lv._verify_typescript(
            _snapshot(tmp_path), _example("typescript", "example", ""), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"
        assert "node" in result.detail

    def test_repo_typecheck_failure_is_build_failed(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"node": "C:/node.exe", "tsc": "C:/tsc.cmd"})
        _scripted_execute_example(
            monkeypatch,
            [_result(argv=["tsc"], return_code=1, stderr="TS2304: Cannot find name 'x'.")],
        )
        result = lv._verify_typescript(
            _snapshot(tmp_path), _example("typescript", "example", "x"), _workspace(tmp_path)
        )
        assert result.outcome == "BUILD_FAILED"

    def test_success_scaffolds_tsconfig_and_example_file(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"node": "C:/node.exe", "tsc": "C:/tsc.cmd"})
        workspace = _workspace(tmp_path)
        calls = _scripted_execute_example(
            monkeypatch,
            [
                _result(argv=["tsc", "--noEmit"], return_code=0),
                _result(argv=["tsc", "--noEmit"], return_code=0),
            ],
        )
        example = _example("typescript", "readmeExample", "const x: number = 1;")
        result = lv._verify_typescript(_snapshot(tmp_path), example, workspace)

        assert result.outcome == "SOURCE_BUILD_VERIFIED"
        example_dir = workspace.parent / "typescript-example"
        assert (example_dir / "tsconfig.json").is_file()
        assert (example_dir / "readmeExample.ts").read_text(
            encoding="utf-8"
        ) == "const x: number = 1;"
        assert calls[1]["workspace"] == example_dir


class TestVerifyGoMocked:
    def test_missing_go_is_blocked_toolchain(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {})
        result = lv._verify_go(
            _snapshot(tmp_path), _example("go", "example", ""), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"
        assert "go" in result.detail

    def test_repo_build_failure_is_build_failed(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"go": "C:/go.exe"})
        _scripted_execute_example(
            monkeypatch, [_result(argv=["go", "build"], return_code=1, stderr="undefined: Foo")]
        )
        result = lv._verify_go(
            _snapshot(tmp_path), _example("go", "example", "x"), _workspace(tmp_path)
        )
        assert result.outcome == "BUILD_FAILED"

    def test_repo_build_failure_with_toolchain_signal_is_blocked(self, tmp_path, monkeypatch):
        _which_only(monkeypatch, {"go": "C:/go.exe"})
        _scripted_execute_example(
            monkeypatch,
            [_result(argv=["go", "build"], return_code=1, stderr="note: module requires Go 1.99")],
        )
        result = lv._verify_go(
            _snapshot(tmp_path), _example("go", "example", "x"), _workspace(tmp_path)
        )
        assert result.outcome == "BLOCKED_TOOLCHAIN"

    def test_success_scaffolds_disposable_module_with_detected_go_version(
        self, tmp_path, monkeypatch
    ):
        _which_only(monkeypatch, {"go": "C:/go.exe"})
        workspace = _workspace(tmp_path)
        (workspace / "go.mod").write_text(
            "module example.com/widget\n\ngo 1.20\n", encoding="utf-8"
        )
        calls = _scripted_execute_example(
            monkeypatch,
            [
                _result(argv=["go", "build"], return_code=0),
                _result(argv=["go", "build"], return_code=0),
            ],
        )
        example = _example("go", "readme_example", "package main\n\nfunc main() {}\n")
        result = lv._verify_go(_snapshot(tmp_path), example, workspace)

        assert result.outcome == "SOURCE_BUILD_VERIFIED"
        example_dir = workspace.parent / "go-example"
        assert (example_dir / "go.mod").read_text(encoding="utf-8") == (
            "module readme-agent-example\n\ngo 1.20\n"
        )
        assert (example_dir / "readme_example.go").is_file()
        assert calls[1]["workspace"] == example_dir


# --------------------------------------------------------------------------
# Live tests: real subprocess calls against a real installed toolchain.
# Excluded from the default run (`addopts = "-m 'not live'"`); run explicitly
# with `-m live`. Each proves the real dispatch/scaffold/execute_example
# wiring actually works end to end, not just that the mocks above are
# self-consistent.
# --------------------------------------------------------------------------


@pytest.mark.live
class TestVerifyPythonLive:
    def test_real_python_toolchain_verifies_a_correct_example(self, tmp_path):
        workspace = _workspace(tmp_path)
        (workspace / "widget.py").write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
        example = _example(
            "python", "readme_example", "print('hello from a real readme-agent example')\n"
        )
        result = lv._verify_python(_snapshot(tmp_path), example, workspace)
        assert result.outcome == "SOURCE_BUILD_VERIFIED", result
        assert result.build.return_code == 0
        assert result.example_compile is not None
        assert result.example_compile.return_code == 0


@pytest.mark.live
class TestVerifyGoLive:
    def test_real_go_toolchain_verifies_a_correct_example(self, tmp_path):
        workspace = _workspace(tmp_path)
        (workspace / "go.mod").write_text(
            "module example.com/widget\n\ngo 1.21\n", encoding="utf-8"
        )
        (workspace / "main.go").write_text(
            'package main\n\nfunc main() {\n\tprintln("widget")\n}\n', encoding="utf-8"
        )
        example = _example(
            "go",
            "readme_example",
            'package main\n\nfunc main() {\n\tprintln("hello from a real readme-agent")\n}\n',
        )
        result = lv._verify_go(_snapshot(tmp_path), example, workspace)
        assert result.outcome == "SOURCE_BUILD_VERIFIED", result
        assert result.build.return_code == 0
        assert result.example_compile is not None
        assert result.example_compile.return_code == 0


@pytest.mark.live
class TestVerifyDotnetLive:
    def test_real_dotnet_toolchain_verifies_a_correct_example(self, tmp_path):
        workspace = _workspace(tmp_path)
        (workspace / "widget.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            "<OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )
        (workspace / "Program.cs").write_text(
            'System.Console.WriteLine("widget");\n', encoding="utf-8"
        )
        example = _example(
            "dotnet",
            "ReadmeExample",
            'System.Console.WriteLine("hello from a real readme-agent example");\n',
        )
        result = lv._verify_dotnet(_snapshot(tmp_path), example, workspace)
        assert result.outcome == "SOURCE_BUILD_VERIFIED", result
        assert result.build.return_code == 0
        assert result.example_compile is not None
        assert result.example_compile.return_code == 0


@pytest.mark.live
@pytest.mark.skipif(shutil.which("tsc") is None, reason="tsc is not installed on this machine")
class TestVerifyTypeScriptLive:
    def test_real_typescript_toolchain_verifies_a_correct_example(self, tmp_path):
        workspace = _workspace(tmp_path)
        (workspace / "tsconfig.json").write_text(
            '{"compilerOptions": {"strict": false}}', encoding="utf-8"
        )
        (workspace / "widget.ts").write_text("export const widget = 1;\n", encoding="utf-8")
        example = _example("typescript", "readmeExample", "const x: number = 1;\nconsole.log(x);\n")
        result = lv._verify_typescript(_snapshot(tmp_path), example, workspace)
        assert result.outcome == "SOURCE_BUILD_VERIFIED", result
