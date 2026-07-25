"""C++ and Rust exact-example verification through native build tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verifiers import cpp, rust
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(root: Path, ecosystem: str) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo=f"acme/{ecosystem}-widget",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        inventory_sha256="b" * 64,
        captured_at="2026-07-25T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url=f"https://example.test/acme/{ecosystem}-widget.git",
            git_tree_sha256="b" * 64,
        ),
    )


def _success(argv, **kwargs):
    return ExampleExecutionResultV1(
        argv=list(argv),
        return_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        environment_names=["CI"],
    )


def test_cpp_verifier_builds_with_cmake_and_syntax_checks_exact_example(tmp_path, monkeypatch):
    workspace = tmp_path / "repository"
    workspace.mkdir()
    (workspace / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.16)\nproject(widget)\n",
        encoding="utf-8",
    )
    commands = []

    def execute(argv, **kwargs):
        commands.append(list(argv))
        return _success(argv)

    monkeypatch.setattr(
        cpp.shutil,
        "which",
        lambda name: "C:/tools/cmake.exe" if name == "cmake" else "C:/tools/clang++.exe",
    )
    monkeypatch.setattr(cpp, "execute_example", execute)
    example = MinimalExamplePolicy(
        language="cpp",
        class_name="WidgetExample",
        code="int main() { return 0; }",
        evidence_paths=["CMakeLists.txt"],
    )

    result = cpp.verify(_snapshot(workspace, "cpp"), example, workspace)

    assert result.outcome == "SOURCE_BUILD_VERIFIED"
    assert commands[0][1] == "-S"
    assert "--build" in commands[1]
    assert "-fsyntax-only" in commands[2]
    assert (tmp_path / "readme-agent-example.cpp").read_text(encoding="utf-8") == example.code


def test_rust_verifier_checks_source_and_exact_cargo_example(tmp_path, monkeypatch):
    workspace = tmp_path / "repository"
    workspace.mkdir()
    (workspace / "Cargo.toml").write_text(
        '[package]\nname = "widget"\nversion = "0.1.0"\nedition = "2021"\n',
        encoding="utf-8",
    )
    (workspace / "Cargo.lock").write_text("", encoding="utf-8")
    commands = []

    def execute(argv, **kwargs):
        commands.append(list(argv))
        return _success(argv)

    monkeypatch.setattr(rust.shutil, "which", lambda name: "C:/tools/cargo.exe")
    monkeypatch.setattr(rust, "execute_example", execute)
    example = MinimalExamplePolicy(
        language="rust",
        class_name="WidgetExample",
        code="fn main() {}",
        evidence_paths=["Cargo.toml"],
    )

    result = rust.verify(_snapshot(workspace, "rust"), example, workspace)

    assert result.outcome == "SOURCE_BUILD_VERIFIED"
    assert commands[0][1:] == ["check", "--locked"]
    assert commands[1][1:] == ["check", "--locked", "--example", "readme_agent_example"]
    assert (workspace / "examples" / "readme_agent_example.rs").read_text(
        encoding="utf-8"
    ) == example.code


@pytest.mark.parametrize(
    ("module", "ecosystem", "tool"),
    [(cpp, "cpp", "cmake"), (rust, "rust", "cargo")],
)
def test_missing_native_toolchain_is_a_typed_visible_block(
    tmp_path, monkeypatch, module, ecosystem, tool
):
    workspace = tmp_path / "repository"
    workspace.mkdir()
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    example = MinimalExamplePolicy(
        language=ecosystem,
        class_name="WidgetExample",
        code="fn main() {}" if ecosystem == "rust" else "int main() { return 0; }",
        evidence_paths=["manifest"],
    )

    result = module.verify(_snapshot(workspace, ecosystem), example, workspace)

    assert result.outcome == "BLOCKED_TOOLCHAIN"
    assert result.build.return_code == 9009
    assert tool in result.detail
